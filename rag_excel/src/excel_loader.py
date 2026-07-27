# """
# excel_loader.py
# ----------------
# Generic, schema-agnostic Excel loader.

# Given ANY .xlsx file, this module:
#   - Reads every worksheet.
#   - Auto-detects column names (whatever they are).
#   - Drops rows/columns that are completely empty.
#   - Normalises values (dates, booleans, numbers, text, Arabic/English/mixed)
#     into safe Python-native representations that are easy to render as text.

# No sheet name, column name, or schema is ever hard-coded.
# """

# from dataclasses import dataclass, field
# from typing import Dict, List, Any
# import datetime

# import pandas as pd

# from config import DROP_FULLY_EMPTY_ROWS, DROP_FULLY_EMPTY_COLUMNS


# @dataclass
# class SheetData:
#     sheet_name: str
#     columns: List[str]
#     rows: List[Dict[str, Any]] = field(default_factory=list)


# def _normalize_cell(value: Any) -> Any:
#     """Convert a pandas/numpy cell value into a clean, human-readable value."""
#     if value is None:
#         return None
#     try:
#         if not isinstance(value, (list, dict)) and pd.isna(value):
#             return None
#     except (TypeError, ValueError):
#         pass
#     if isinstance(value, (pd.Timestamp, datetime.datetime, datetime.date)):
#         # Keep a readable, locale-agnostic date format.
#         try:
#             if isinstance(value, pd.Timestamp):
#                 value = value.to_pydatetime()
#             if isinstance(value, datetime.datetime) and value.time() == datetime.time(0, 0):
#                 return value.strftime("%Y-%m-%d")
#             return value.strftime("%Y-%m-%d %H:%M:%S")
#         except Exception:
#             return str(value)
#     if isinstance(value, bool):
#         return value
#     if isinstance(value, (int,)):
#         return value
#     if isinstance(value, float):
#         # Represent whole-number floats (common from Excel) as ints.
#         if value.is_integer():
#             return int(value)
#         return round(value, 6)
#     # Strings (Arabic, English, mixed, symbols, etc.) pass through untouched,
#     # just stripped of leading/trailing whitespace.
#     if isinstance(value, str):
#         stripped = value.strip()
#         return stripped if stripped != "" else None
#     return value


# def _is_row_empty(row_values: List[Any]) -> bool:
#     return all(v is None for v in row_values)


# def load_excel(file_path: str) -> List[SheetData]:
#     """
#     Load every worksheet of the given Excel file.

#     Returns a list of SheetData objects (one per non-empty sheet), each
#     holding a list of row dictionaries: {column_name: normalized_value}.
#     Fully empty rows and fully empty columns are dropped.
#     """
#     # sheet_name=None -> dict of {sheet_name: DataFrame} for ALL sheets.
#     # dtype=object keeps original values so we can normalize them ourselves.
#     all_sheets = pd.read_excel(file_path, sheet_name=None, dtype=object, engine="openpyxl")

#     result: List[SheetData] = []

#     for sheet_name, df in all_sheets.items():
#         if df is None or df.empty:
#             continue

#         # Ensure column names are strings (Excel sometimes yields ints/NaN
#         # for unnamed columns).
#         df.columns = [
#             str(col).strip() if col is not None and str(col).strip() != "" else f"Column_{i+1}"
#             for i, col in enumerate(df.columns)
#         ]

#         # Drop fully-empty columns (all values NaN/blank across the sheet).
#         if DROP_FULLY_EMPTY_COLUMNS:
#             non_empty_cols = []
#             for col in df.columns:
#                 series = df[col]
#                 if series.apply(lambda v: _normalize_cell(v) is not None).any():
#                     non_empty_cols.append(col)
#             df = df[non_empty_cols]

#         if df.shape[1] == 0:
#             continue

#         columns = list(df.columns)
#         rows: List[Dict[str, Any]] = []

#         for _, raw_row in df.iterrows():
#             normalized = {col: _normalize_cell(raw_row[col]) for col in columns}
#             values = list(normalized.values())

#             if DROP_FULLY_EMPTY_ROWS and _is_row_empty(values):
#                 continue

#             rows.append(normalized)

#         if rows:
#             result.append(SheetData(sheet_name=sheet_name, columns=columns, rows=rows))

#     return result

"""
excel_loader.py
---------------
This file loads data from an Excel (.xlsx) file.

It:
- Reads every sheet in the workbook.
- Gets the column names automatically.
- Removes completely empty rows and columns.
- Cleans the cell values so they are easier to use.

It works with any Excel file, so no sheet names or column names
need to be hard-coded.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any
import datetime

import pandas as pd

from config import DROP_FULLY_EMPTY_ROWS, DROP_FULLY_EMPTY_COLUMNS


@dataclass
class SheetData:
    # Stores the data for one worksheet
    sheet_name: str
    columns: List[str]
    rows: List[Dict[str, Any]] = field(default_factory=list)


def _normalize_cell(value: Any) -> Any:
    """
    Clean a cell value and convert it into a simple Python value.
    """
    if value is None:
        return None

    try:
        if not isinstance(value, (list, dict)) and pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    # Format dates into a readable form.
    if isinstance(value, (pd.Timestamp, datetime.datetime, datetime.date)):
        try:
            if isinstance(value, pd.Timestamp):
                value = value.to_pydatetime()

            if isinstance(value, datetime.datetime) and value.time() == datetime.time(0, 0):
                return value.strftime("%Y-%m-%d")

            return value.strftime("%Y-%m-%d %H:%M:%S")

        except Exception:
            return str(value)

    # Keep boolean values.
    if isinstance(value, bool):
        return value

    # Keep integer values.
    if isinstance(value, (int,)):
        return value

    # Convert whole-number floats to integers.
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        return round(value, 6)

    # Remove extra spaces from text.
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped != "" else None

    return value


def _is_row_empty(row_values: List[Any]) -> bool:
    """
    Check if every value in a row is empty.
    """
    return all(v is None for v in row_values)


def load_excel(file_path: str) -> List[SheetData]:
    """
    Load all worksheets from an Excel file.

    For each sheet:
    - clean the column names
    - remove empty columns
    - clean the cell values
    - remove empty rows

    Return a list of SheetData objects.
    """

    # Read every sheet in the workbook.
    # dtype=object keeps the original values so we can clean them ourselves.
    all_sheets = pd.read_excel(
        file_path,
        sheet_name=None,
        dtype=object,
        engine="openpyxl",
    )

    result: List[SheetData] = []

    for sheet_name, df in all_sheets.items():
        if df is None or df.empty:
            continue

        # Make sure every column has a valid name.
        df.columns = [
            str(col).strip() if col is not None and str(col).strip() != "" else f"Column_{i+1}"
            for i, col in enumerate(df.columns)
        ]

        # Remove columns that are completely empty.
        if DROP_FULLY_EMPTY_COLUMNS:
            non_empty_cols = []

            for col in df.columns:
                series = df[col]

                if series.apply(lambda v: _normalize_cell(v) is not None).any():
                    non_empty_cols.append(col)

            df = df[non_empty_cols]

        if df.shape[1] == 0:
            continue

        columns = list(df.columns)
        rows: List[Dict[str, Any]] = []

        # Go through every row in the sheet.
        for _, raw_row in df.iterrows():
            normalized = {
                col: _normalize_cell(raw_row[col])
                for col in columns
            }

            values = list(normalized.values())

            # Skip rows that are completely empty.
            if DROP_FULLY_EMPTY_ROWS and _is_row_empty(values):
                continue

            rows.append(normalized)

        # Save the sheet only if it has data.
        if rows:
            result.append(
                SheetData(
                    sheet_name=sheet_name,
                    columns=columns,
                    rows=rows,
                )
            )

    return result