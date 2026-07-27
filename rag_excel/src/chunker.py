# """
# chunker.py
# ----------
# Splits Document objects (one per Excel row) into overlapping text chunks.

# Most rows are short, so they typically become a single chunk. Rows with
# long text fields (long descriptions/comments, etc.) are split into
# multiple overlapping chunks so no information is lost and context stays
# coherent, while metadata (source file, sheet, row number) is preserved
# on every chunk.
# """

# from dataclasses import dataclass, field
# from typing import Any, Dict, List

# from config import CHUNK_SIZE, CHUNK_OVERLAP
# from src.document_builder import Document


# @dataclass
# class Chunk:
#     text: str
#     metadata: Dict[str, Any] = field(default_factory=dict)


# def _split_text(text: str, chunk_size: int, overlap: int) -> List[str]:
#     """Simple, robust character-based sliding-window splitter.
#     Works uniformly for Arabic, English, mixed text, digits, punctuation."""
#     if len(text) <= chunk_size:
#         return [text]

#     chunks = []
#     start = 0
#     text_len = len(text)
#     step = max(chunk_size - overlap, 1)

#     while start < text_len:
#         end = min(start + chunk_size, text_len)
#         chunks.append(text[start:end])
#         if end == text_len:
#             break
#         start += step

#     return chunks


# def chunk_documents(documents: List[Document]) -> List[Chunk]:
#     """Turn a list of Documents into a list of Chunks ready for embedding."""
#     chunks: List[Chunk] = []

#     for doc in documents:
#         pieces = _split_text(doc.text, CHUNK_SIZE, CHUNK_OVERLAP)
#         for idx, piece in enumerate(pieces):
#             metadata = dict(doc.metadata)
#             metadata["chunk_index"] = idx
#             metadata["total_chunks_for_row"] = len(pieces)
#             chunks.append(Chunk(text=piece, metadata=metadata))

#     return chunks


"""
chunker.py
----------
This file splits documents into smaller text chunks.

Most Excel rows are already short, so they usually stay as one chunk.
If a row has a lot of text, it is split into smaller overlapping chunks.

Each chunk keeps the same metadata as the original document, such as:
- source file
- sheet name
- row number

This makes it easier to find where the chunk came from later.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List

from config import CHUNK_SIZE, CHUNK_OVERLAP
from src.document_builder import Document


@dataclass
class Chunk:
    # Stores one text chunk and its metadata
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


def _split_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """
    Split text into smaller overlapping chunks.

    If the text is already short enough, return it as one chunk.

    This method works with:
    - English
    - Arabic
    - Mixed text
    - Numbers and symbols
    """
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    text_len = len(text)
    step = max(chunk_size - overlap, 1)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunks.append(text[start:end])

        if end == text_len:
            break

        start += step

    return chunks


def chunk_documents(documents: List[Document]) -> List[Chunk]:
    """
    Convert a list of documents into a list of chunks.

    For each document:
    - split the text into chunks
    - copy the document metadata
    - add the chunk number
    - save the chunk

    Return all chunks at the end.
    """
    chunks: List[Chunk] = []

    for doc in documents:
        pieces = _split_text(doc.text, CHUNK_SIZE, CHUNK_OVERLAP)

        for idx, piece in enumerate(pieces):
            metadata = dict(doc.metadata)
            metadata["chunk_index"] = idx
            metadata["total_chunks_for_row"] = len(pieces)

            chunks.append(Chunk(text=piece, metadata=metadata))

    return chunks