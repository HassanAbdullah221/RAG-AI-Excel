# """
# sql_agent.py
# ------------
# Text-to-SQL agent: asks qwen2.5:7b to translate a natural-language question
# into a single, safe, read-only SQL query against the auto-generated SQLite
# schema, validates it strictly, executes it, and returns the results.

# Safety model:
#   - Only a single SELECT statement is allowed (no semicolons / stacked
#     statements).
#   - Any DDL/DML keyword (INSERT, UPDATE, DELETE, DROP, ALTER, ATTACH,
#     PRAGMA, ...) causes the query to be rejected before it ever reaches
#     the database.
#   - The connection itself is opened read-only (see SQLiteStore.run_query),
#     so even a validation gap can't mutate the database.
#   - A LIMIT is enforced to bound how much data ever comes back into the
#     LLM context.
# """

# import re
# from typing import List, Optional, Tuple

# from config import SQL_MAX_ROWS
# from src.ollama_client import chat_completion
# from src.sqlite_store import SQLiteStore

# FORBIDDEN_KEYWORDS = {
#     "insert", "update", "delete", "drop", "alter", "create", "attach",
#     "detach", "pragma", "vacuum", "replace", "reindex", "trigger", "grant",
# }


# class SQLSafetyError(ValueError):
#     """Raised when the LLM-generated SQL fails the safety validation."""


# def _extract_sql(text: str) -> str:
#     """Pull the SQL statement out of the LLM's raw response (handles code fences)."""
#     text = text.strip()
#     fence_match = re.search(r"```(?:sql)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
#     if fence_match:
#         text = fence_match.group(1).strip()
#     return text.strip().rstrip(";").strip()


# def validate_sql(sql: str) -> str:
#     """Ensure the query is exactly one safe, read-only SELECT statement."""
#     if not sql:
#         raise SQLSafetyError("The model did not generate a SQL query.")

#     if ";" in sql:
#         raise SQLSafetyError("Multiple SQL statements are not allowed.")

#     lowered = sql.lower().strip()
#     if not (lowered.startswith("select") or lowered.startswith("with")):
#         raise SQLSafetyError("Only SELECT (or SELECT-based WITH/CTE) queries are allowed.")

#     for kw in FORBIDDEN_KEYWORDS:
#         if re.search(rf"\b{kw}\b", lowered):
#             raise SQLSafetyError(f"Forbidden keyword detected in generated SQL: '{kw}'.")

#     if "limit" not in lowered:
#         sql = f"{sql}\nLIMIT {SQL_MAX_ROWS}"

#     return sql


# def generate_sql(question: str, schema_description: str) -> str:
#     """Ask the LLM for exactly one safe SQL query answering `question`."""
#     system_prompt = (
#         "You are a SQL expert generating SQLite queries for a database that "
#         "was auto-generated from an Excel workbook (one table per sheet). "
#         "Given the schema below and a user's question - which may be in "
#         "English, Arabic, or mixed - write EXACTLY ONE read-only SQLite "
#         "SELECT query that answers the question.\n"
#         "Rules:\n"
#         "- Only reference tables/columns that literally exist in the schema below.\n"
#         "- Always use the sanitized (quoted) table/column names shown, not the "
#         "'original name' shown in parentheses.\n"
#         "- Never use INSERT, UPDATE, DELETE, DROP, ALTER, PRAGMA, or ATTACH.\n"
#         "- Return ONLY the raw SQL query - no explanation, no markdown fences, "
#         "no trailing semicolon.\n\n"
#         f"Database schema:\n{schema_description}\n"
#     )
#     raw = chat_completion(system_prompt, f"Question: {question}\nSQL:")
#     sql = _extract_sql(raw)
#     return validate_sql(sql)


# def run_text_to_sql(
#     question: str, store: SQLiteStore
# ) -> Tuple[str, List[str], List[Tuple]]:
#     """
#     Full text-to-SQL round trip: generate, validate, execute.
#     Returns (sql_query, column_names, result_rows).
#     Raises SQLSafetyError (validation) or sqlite3.Error (execution) on failure -
#     callers should catch these and fall back to the semantic path.
#     """
#     schema_description = store.get_schema_description()
#     sql = generate_sql(question, schema_description)
#     columns, rows = store.run_query(sql)
#     return sql, columns, rows


# def format_sql_result_as_text(sql: str, columns: List[str], rows: List[Tuple]) -> str:
#     """Render a SQL result set as readable text to feed into the final answer prompt."""
#     if not rows:
#         return f"SQL query executed:\n{sql}\n\nResult: no matching rows."

#     header = " | ".join(columns)
#     body_lines = [" | ".join("" if v is None else str(v) for v in row) for row in rows]
#     table_text = "\n".join([header] + body_lines)

#     truncation_note = ""
#     if len(rows) >= SQL_MAX_ROWS:
#         truncation_note = f"\n(Result truncated to the first {SQL_MAX_ROWS} rows.)"

#     return f"SQL query executed:\n{sql}\n\nResult ({len(rows)} row(s)):\n{table_text}{truncation_note}"

"""
sql_agent.py
------------
This file converts a user's question into a SQL query.

The language model generates a SQL query, then the query is:
- Checked to make sure it is safe.
- Run on the SQLite database.
- Returned as readable text.

Only read-only SELECT queries are allowed.
This prevents the database from being changed.
"""

import re
from typing import List, Optional, Tuple

from config import SQL_MAX_ROWS
from src.ollama_client import chat_completion
from src.sqlite_store import SQLiteStore

FORBIDDEN_KEYWORDS = {
    "insert", "update", "delete", "drop", "alter", "create", "attach",
    "detach", "pragma", "vacuum", "replace", "reindex", "trigger", "grant",
}


class SQLSafetyError(ValueError):
    """Raised when a generated SQL query is not safe."""


def _extract_sql(text: str) -> str:
    """
    Extract the SQL query from the model's response.

    This also removes markdown code blocks if they exist.
    """
    text = text.strip()

    fence_match = re.search(
        r"```(?:sql)?\s*(.*?)```",
        text,
        re.DOTALL | re.IGNORECASE,
    )

    if fence_match:
        text = fence_match.group(1).strip()

    return text.strip().rstrip(";").strip()


def validate_sql(sql: str) -> str:
    """
    Check that the SQL query is safe before running it.

    Rules:
    - The query cannot be empty.
    - Only one SQL statement is allowed.
    - It must start with SELECT or WITH.
    - Dangerous SQL commands are not allowed.
    - Add a LIMIT if one is missing.
    """
    if not sql:
        raise SQLSafetyError("The model did not generate a SQL query.")

    if ";" in sql:
        raise SQLSafetyError("Multiple SQL statements are not allowed.")

    lowered = sql.lower().strip()

    if not (lowered.startswith("select") or lowered.startswith("with")):
        raise SQLSafetyError(
            "Only SELECT (or SELECT-based WITH/CTE) queries are allowed."
        )

    for kw in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{kw}\b", lowered):
            raise SQLSafetyError(
                f"Forbidden keyword detected in generated SQL: '{kw}'."
            )

    # Add a row limit if the query does not have one.
    if "limit" not in lowered:
        sql = f"{sql}\nLIMIT {SQL_MAX_ROWS}"

    return sql


def generate_sql(question: str, schema_description: str) -> str:
    """
    Ask the language model to generate one SQL query
    that answers the user's question.
    """
    system_prompt = (
        "You are a SQL expert generating SQLite queries for a database that "
        "was auto-generated from an Excel workbook (one table per sheet). "
        "Given the schema below and a user's question - which may be in "
        "English, Arabic, or mixed - write EXACTLY ONE read-only SQLite "
        "SELECT query that answers the question.\n"
        "Rules:\n"
        "- Only reference tables/columns that literally exist in the schema below.\n"
        "- Always use the sanitized (quoted) table/column names shown, not the "
        "'original name' shown in parentheses.\n"
        "- Never use INSERT, UPDATE, DELETE, DROP, ALTER, PRAGMA, or ATTACH.\n"
        "- Return ONLY the raw SQL query - no explanation, no markdown fences, "
        "no trailing semicolon.\n\n"
        f"Database schema:\n{schema_description}\n"
    )

    raw = chat_completion(
        system_prompt,
        f"Question: {question}\nSQL:",
    )

    sql = _extract_sql(raw)

    return validate_sql(sql)


def run_text_to_sql(
    question: str,
    store: SQLiteStore,
) -> Tuple[str, List[str], List[Tuple]]:
    """
    Complete the text-to-SQL process.

    Steps:
    1. Generate a SQL query.
    2. Validate the query.
    3. Run the query.
    4. Return the SQL query, column names, and rows.
    """
    schema_description = store.get_schema_description()

    sql = generate_sql(question, schema_description)

    columns, rows = store.run_query(sql)

    return sql, columns, rows


def format_sql_result_as_text(
    sql: str,
    columns: List[str],
    rows: List[Tuple],
) -> str:
    """
    Convert SQL results into readable text
    that can be used by the language model.
    """
    if not rows:
        return (
            f"SQL query executed:\n{sql}\n\n"
            f"Result: no matching rows."
        )

    header = " | ".join(columns)

    body_lines = [
        " | ".join("" if v is None else str(v) for v in row)
        for row in rows
    ]

    table_text = "\n".join([header] + body_lines)

    truncation_note = ""

    if len(rows) >= SQL_MAX_ROWS:
        truncation_note = (
            f"\n(Result truncated to the first {SQL_MAX_ROWS} rows.)"
        )

    return (
        f"SQL query executed:\n{sql}\n\n"
        f"Result ({len(rows)} row(s)):\n"
        f"{table_text}{truncation_note}"
    )