# """
# sqlite_store.py
# ----------------
# Loads ANY Excel workbook into a local, on-disk SQLite database - one table
# per worksheet - with automatically sanitized table/column names, regardless
# of the original sheet/column names (any language, spaces, symbols).

# This powers the "structured" half of the hybrid pipeline: precise counting,
# summing, averaging, filtering, and sorting via generated SQL, instead of
# semantic retrieval.
# """

# import json
# import os
# import re
# import sqlite3
# from typing import Any, Dict, List, Tuple

# import pandas as pd

# from config import SQL_MAX_ROWS, SQL_QUERY_TIMEOUT
# from src.excel_loader import SheetData


# def _sanitize_identifier(name: str, used: set) -> str:
#     """
#     Turn an arbitrary sheet/column name into a safe, unique SQL identifier.
#     Keeps Arabic letters (valid inside quoted SQLite identifiers) and
#     replaces everything else unsafe with underscores. Guarantees uniqueness
#     within the given `used` set (case-insensitive).
#     """
#     safe = re.sub(r"[^0-9A-Za-z_\u0600-\u06FF]+", "_", str(name)).strip("_")
#     if not safe:
#         safe = "col"
#     if safe[0].isdigit():
#         safe = f"_{safe}"

#     base = safe
#     counter = 1
#     while safe.lower() in used:
#         safe = f"{base}_{counter}"
#         counter += 1
#     used.add(safe.lower())
#     return safe


# class SQLiteStore:
#     """One SQLite database per Excel file, stored inside the shared
#     per-file vector-db directory (alongside the FAISS index)."""

#     def __init__(self, store_dir: str):
#         self.store_dir = store_dir
#         self.db_path = os.path.join(store_dir, "data.sqlite3")
#         self.schema_map_path = os.path.join(store_dir, "schema_map.json")
#         # table_name -> {"original_sheet_name": str, "columns": [[safe, original], ...]}
#         self.schema_map: Dict[str, Dict[str, Any]] = {}

#     # ------------------------------------------------------------------
#     # Build
#     # ------------------------------------------------------------------
#     def build(self, sheets: List[SheetData]) -> None:
#         os.makedirs(self.store_dir, exist_ok=True)
#         if os.path.exists(self.db_path):
#             os.remove(self.db_path)

#         conn = sqlite3.connect(self.db_path)
#         used_table_names: set = set()
#         schema_map: Dict[str, Dict[str, Any]] = {}

#         try:
#             for sheet in sheets:
#                 table_name = _sanitize_identifier(sheet.sheet_name, used_table_names)

#                 used_col_names: set = set()
#                 col_map: List[Tuple[str, str]] = []
#                 for col in sheet.columns:
#                     safe_col = _sanitize_identifier(col, used_col_names)
#                     col_map.append((safe_col, col))

#                 data = {
#                     safe_col: [row.get(orig_col) for row in sheet.rows]
#                     for safe_col, orig_col in col_map
#                 }
#                 df = pd.DataFrame(data)
#                 df.to_sql(table_name, conn, index=False, if_exists="replace")

#                 schema_map[table_name] = {
#                     "original_sheet_name": sheet.sheet_name,
#                     "columns": [[s, o] for s, o in col_map],
#                 }
#             conn.commit()
#         finally:
#             conn.close()

#         self.schema_map = schema_map
#         with open(self.schema_map_path, "w", encoding="utf-8") as f:
#             json.dump(schema_map, f, ensure_ascii=False, indent=2)

#     # ------------------------------------------------------------------
#     # Load
#     # ------------------------------------------------------------------
#     def load_schema_map(self) -> bool:
#         if not os.path.exists(self.schema_map_path):
#             return False
#         with open(self.schema_map_path, "r", encoding="utf-8") as f:
#             self.schema_map = json.load(f)
#         return True

#     def exists(self) -> bool:
#         return os.path.exists(self.db_path) and os.path.exists(self.schema_map_path)

#     # ------------------------------------------------------------------
#     # Schema description for the LLM
#     # ------------------------------------------------------------------
#     def get_schema_description(self, sample_rows: int = 2) -> str:
#         """
#         Human/LLM-readable description of every table: sanitized name (the
#         name to use in SQL), original sheet/column names (for context), and
#         a couple of sample rows so the LLM understands the data shape.
#         Dates are stored as ISO 8601 text (YYYY-MM-DD[ HH:MM:SS]), which is
#         noted explicitly since it's directly comparable/sortable as text.
#         """
#         lines = [
#             "Note: all dates are stored as ISO 8601 text (YYYY-MM-DD or "
#             "YYYY-MM-DD HH:MM:SS), which sorts/compares correctly as text. "
#             "Booleans are stored as integers (1 = true, 0 = false)."
#         ]
#         conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
#         try:
#             for table_name, info in self.schema_map.items():
#                 col_descs = [
#                     f'"{safe}" (original column: "{orig}")' for safe, orig in info["columns"]
#                 ]
#                 lines.append(
#                     f'\nTable "{table_name}" (from sheet "{info["original_sheet_name"]}"), '
#                     f"columns: " + ", ".join(col_descs)
#                 )
#                 try:
#                     cur = conn.execute(f'SELECT * FROM "{table_name}" LIMIT {sample_rows}')
#                     rows = cur.fetchall()
#                     if rows:
#                         lines.append(f"  Sample rows: {rows}")
#                 except sqlite3.Error:
#                     pass
#         finally:
#             conn.close()

#         return "\n".join(lines)

#     # ------------------------------------------------------------------
#     # Query execution
#     # ------------------------------------------------------------------
#     def run_query(self, sql: str) -> Tuple[List[str], List[Tuple]]:
#         """Execute an already-validated, read-only SELECT query."""
#         conn = sqlite3.connect(
#             f"file:{self.db_path}?mode=ro", uri=True, timeout=SQL_QUERY_TIMEOUT
#         )
#         try:
#             cur = conn.execute(sql)
#             columns = [d[0] for d in cur.description] if cur.description else []
#             rows = cur.fetchmany(SQL_MAX_ROWS)
#             return columns, rows
#         finally:
#             conn.close()

"""
sqlite_store.py
---------------
This file creates a SQLite database from an Excel workbook.

Each worksheet becomes one table in the database.

Table names and column names are cleaned so they are safe to use in SQL,
even if the original names contain spaces, symbols, Arabic, or other
characters.

The SQLite database is used for structured queries such as:
- counting
- filtering
- sorting
- averages
- totals
"""

import json
import os
import re
import sqlite3
from typing import Any, Dict, List, Tuple

import pandas as pd

from config import SQL_MAX_ROWS, SQL_QUERY_TIMEOUT
from src.excel_loader import SheetData


def _sanitize_identifier(name: str, used: set) -> str:
    """
    Convert a sheet name or column name into a safe SQL name.

    It also makes sure every name is unique.
    """
    safe = re.sub(r"[^0-9A-Za-z_\u0600-\u06FF]+", "_", str(name)).strip("_")

    if not safe:
        safe = "col"

    if safe[0].isdigit():
        safe = f"_{safe}"

    base = safe
    counter = 1

    while safe.lower() in used:
        safe = f"{base}_{counter}"
        counter += 1

    used.add(safe.lower())

    return safe


class SQLiteStore:
    """
    Stores one SQLite database for each Excel file.
    """

    def __init__(self, store_dir: str):
        self.store_dir = store_dir
        self.db_path = os.path.join(store_dir, "data.sqlite3")
        self.schema_map_path = os.path.join(store_dir, "schema_map.json")

        # Stores information about table names and column names.
        self.schema_map: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------
    def build(self, sheets: List[SheetData]) -> None:
        """
        Create a SQLite database from the Excel sheets.
        """
        os.makedirs(self.store_dir, exist_ok=True)

        if os.path.exists(self.db_path):
            os.remove(self.db_path)

        conn = sqlite3.connect(self.db_path)

        used_table_names: set = set()
        schema_map: Dict[str, Dict[str, Any]] = {}

        try:
            for sheet in sheets:
                # Create a safe table name.
                table_name = _sanitize_identifier(
                    sheet.sheet_name,
                    used_table_names,
                )

                used_col_names: set = set()
                col_map: List[Tuple[str, str]] = []

                # Create safe column names.
                for col in sheet.columns:
                    safe_col = _sanitize_identifier(col, used_col_names)
                    col_map.append((safe_col, col))

                # Copy the sheet data into a DataFrame.
                data = {
                    safe_col: [row.get(orig_col) for row in sheet.rows]
                    for safe_col, orig_col in col_map
                }

                df = pd.DataFrame(data)

                # Save the DataFrame as a SQLite table.
                df.to_sql(
                    table_name,
                    conn,
                    index=False,
                    if_exists="replace",
                )

                schema_map[table_name] = {
                    "original_sheet_name": sheet.sheet_name,
                    "columns": [[s, o] for s, o in col_map],
                }

            conn.commit()

        finally:
            conn.close()

        self.schema_map = schema_map

        # Save the table and column mappings.
        with open(self.schema_map_path, "w", encoding="utf-8") as f:
            json.dump(schema_map, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------
    def load_schema_map(self) -> bool:
        """
        Load the saved schema information.
        """
        if not os.path.exists(self.schema_map_path):
            return False

        with open(self.schema_map_path, "r", encoding="utf-8") as f:
            self.schema_map = json.load(f)

        return True

    def exists(self) -> bool:
        """
        Check if the database and schema files already exist.
        """
        return (
            os.path.exists(self.db_path)
            and os.path.exists(self.schema_map_path)
        )

    # ------------------------------------------------------------------
    # Schema description
    # ------------------------------------------------------------------
    def get_schema_description(self, sample_rows: int = 2) -> str:
        """
        Create a readable description of the database.

        The description includes:
        - table names
        - original sheet names
        - column names
        - a few sample rows

        This helps the language model generate better SQL queries.
        """
        lines = [
            "Note: all dates are stored as ISO 8601 text (YYYY-MM-DD or "
            "YYYY-MM-DD HH:MM:SS). "
            "Booleans are stored as integers (1 = true, 0 = false)."
        ]

        conn = sqlite3.connect(
            f"file:{self.db_path}?mode=ro",
            uri=True,
        )

        try:
            for table_name, info in self.schema_map.items():

                col_descs = [
                    f'"{safe}" (original column: "{orig}")'
                    for safe, orig in info["columns"]
                ]

                lines.append(
                    f'\nTable "{table_name}" '
                    f'(from sheet "{info["original_sheet_name"]}"), '
                    f"columns: " + ", ".join(col_descs)
                )

                try:
                    cur = conn.execute(
                        f'SELECT * FROM "{table_name}" LIMIT {sample_rows}'
                    )

                    rows = cur.fetchall()

                    if rows:
                        lines.append(f"  Sample rows: {rows}")

                except sqlite3.Error:
                    pass

        finally:
            conn.close()

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Query execution
    # ------------------------------------------------------------------
    def run_query(self, sql: str) -> Tuple[List[str], List[Tuple]]:
        """
        Run a validated read-only SQL query.
        """
        conn = sqlite3.connect(
            f"file:{self.db_path}?mode=ro",
            uri=True,
            timeout=SQL_QUERY_TIMEOUT,
        )

        try:
            cur = conn.execute(sql)

            columns = [
                d[0] for d in cur.description
            ] if cur.description else []

            rows = cur.fetchmany(SQL_MAX_ROWS)

            return columns, rows

        finally:
            conn.close()