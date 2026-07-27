# """
# document_builder.py
# --------------------
# Turns each Excel row (from excel_loader.SheetData) into a human-readable
# text "document" plus metadata (source file, sheet name, row number).

# This text is what eventually gets chunked and embedded.
# """

# from dataclasses import dataclass, field
# from typing import Any, Dict, List

# from src.excel_loader import SheetData


# @dataclass
# class Document:
#     text: str
#     metadata: Dict[str, Any] = field(default_factory=dict)


# def _format_value(value: Any) -> str:
#     if value is None:
#         return "N/A"
#     if isinstance(value, bool):
#         return "Yes" if value else "No"
#     return str(value)


# def row_to_text(sheet_name: str, columns: List[str], row: Dict[str, Any]) -> str:
#     """
#     Render a single row as a natural, readable "field: value" sentence.
#     Works for any column names/values (Arabic, English, mixed, numeric, dates).
#     """
#     parts = [f"{col}: {_format_value(row.get(col))}" for col in columns]
#     return f"Sheet '{sheet_name}' record -> " + "; ".join(parts)


# def build_documents(file_name: str, sheets: List[SheetData]) -> List[Document]:
#     """
#     Convert all sheets/rows of a workbook into a flat list of Document
#     objects, each carrying metadata: source file, sheet name, row number.
#     """
#     documents: List[Document] = []

#     for sheet in sheets:
#         for row_idx, row in enumerate(sheet.rows, start=1):
#             text = row_to_text(sheet.sheet_name, sheet.columns, row)
#             metadata = {
#                 "source_file": file_name,
#                 "sheet_name": sheet.sheet_name,
#                 "row_number": row_idx,
#                 "columns": sheet.columns,
#             }
#             documents.append(Document(text=text, metadata=metadata))

#     return documents

"""
document_builder.py
-------------------
This file changes Excel data into simple text documents.

Each row from the Excel file becomes one document.
The document also keeps some extra information like:
- file name
- sheet name
- row number

These documents will later be split into smaller pieces and used for embeddings.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

from src.excel_loader import SheetData


@dataclass
class Document:
    # Stores the document text and its metadata
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


def _format_value(value: Any) -> str:
    """
    Convert different value types into readable text.
    """
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value)


def row_to_text(sheet_name: str, columns: List[str], row: Dict[str, Any]) -> str:
    """
    Turn one Excel row into a readable sentence.

    Each column is shown like:
    Column Name: Value

    This works for any type of data, such as:
    - English or Arabic text
    - Numbers
    - Dates
    """
    parts = [f"{col}: {_format_value(row.get(col))}" for col in columns]
    return f"Sheet '{sheet_name}' record -> " + "; ".join(parts)


def build_documents(file_name: str, sheets: List[SheetData]) -> List[Document]:
    """
    Go through every sheet in the workbook.

    For each row:
    - create a text document
    - save useful metadata
    - add it to the documents list

    At the end, return all documents.
    """
    documents: List[Document] = []

    for sheet in sheets:
        for row_idx, row in enumerate(sheet.rows, start=1):
            text = row_to_text(sheet.sheet_name, sheet.columns, row)

            metadata = {
                "source_file": file_name,
                "sheet_name": sheet.sheet_name,
                "row_number": row_idx,
                "columns": sheet.columns,
            }

            documents.append(Document(text=text, metadata=metadata))

    return documents