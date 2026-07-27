# """
# vector_store.py
# ----------------
# FAISS-backed vector store, with one persisted store per Excel file.

# Layout for each source file (under VECTOR_DB_ROOT/<safe_name>/):
#   - index.faiss        FAISS index (inner-product over L2-normalized vectors,
#                         i.e. cosine similarity).
#   - chunks.pkl          Pickled list of chunk texts + metadata (parallel to
#                         the vectors stored in the FAISS index).
#   - source_hash.json    SHA-256 hash of the source Excel file (see hash_utils).
# """

# import os
# import pickle
# import re
# from typing import List, Tuple

# import faiss
# import numpy as np

# from config import VECTOR_DB_ROOT
# from src.chunker import Chunk


# def safe_dir_name(file_path: str) -> str:
#     """Turn an arbitrary Excel file path into a filesystem-safe folder name."""
#     base = os.path.basename(file_path)
#     name, _ext = os.path.splitext(base)
#     safe = re.sub(r"[^A-Za-z0-9_\-\.]+", "_", name)
#     return safe or "excel_file"


# class VectorStore:
#     def __init__(self, source_file_path: str):
#         self.source_file_path = source_file_path
#         self.store_dir = os.path.join(VECTOR_DB_ROOT, safe_dir_name(source_file_path))
#         self.index_path = os.path.join(self.store_dir, "index.faiss")
#         self.chunks_path = os.path.join(self.store_dir, "chunks.pkl")
#         self.hash_path = os.path.join(self.store_dir, "source_hash.json")

#         self.index: faiss.Index = None
#         self.chunks: List[Chunk] = []

#     # ------------------------------------------------------------------
#     # Build
#     # ------------------------------------------------------------------
#     def build(self, chunks: List[Chunk], embeddings: List[List[float]]) -> None:
#         if not chunks or not embeddings:
#             raise ValueError("Cannot build a vector store with no chunks/embeddings.")

#         vectors = np.array(embeddings, dtype="float32")
#         faiss.normalize_L2(vectors)

#         dim = vectors.shape[1]
#         index = faiss.IndexFlatIP(dim)  # cosine similarity via normalized inner product
#         index.add(vectors)

#         self.index = index
#         self.chunks = chunks

#     # ------------------------------------------------------------------
#     # Persistence
#     # ------------------------------------------------------------------
#     def save(self) -> None:
#         os.makedirs(self.store_dir, exist_ok=True)
#         faiss.write_index(self.index, self.index_path)
#         with open(self.chunks_path, "wb") as f:
#             pickle.dump(self.chunks, f)

#     def load(self) -> bool:
#         """Load a previously persisted index. Returns True on success."""
#         if not (os.path.exists(self.index_path) and os.path.exists(self.chunks_path)):
#             return False
#         self.index = faiss.read_index(self.index_path)
#         with open(self.chunks_path, "rb") as f:
#             self.chunks = pickle.load(f)
#         return True

#     def exists(self) -> bool:
#         return os.path.exists(self.index_path) and os.path.exists(self.chunks_path)

#     # ------------------------------------------------------------------
#     # Search
#     # ------------------------------------------------------------------
#     def search(self, query_embedding: List[float], top_k: int) -> List[Tuple[Chunk, float]]:
#         if self.index is None:
#             raise RuntimeError("Vector store is not loaded/built yet.")

#         vec = np.array([query_embedding], dtype="float32")
#         faiss.normalize_L2(vec)

#         top_k = min(top_k, self.index.ntotal)
#         if top_k == 0:
#             return []

#         scores, indices = self.index.search(vec, top_k)

#         results: List[Tuple[Chunk, float]] = []
#         for score, idx in zip(scores[0], indices[0]):
#             if idx == -1:
#                 continue
#             results.append((self.chunks[idx], float(score)))
#         return results

"""
vector_store.py
---------------
This file creates and manages the FAISS vector database.

Each Excel file has its own saved vector database.

The folder for each Excel file contains:
- index.faiss      : the FAISS vector index
- chunks.pkl       : the saved text chunks and their metadata
- source_hash.json : the hash of the original Excel file

The vector database is used for semantic (meaning-based) search.
"""

import os
import pickle
import re
from typing import List, Tuple

import faiss
import numpy as np

from config import VECTOR_DB_ROOT
from src.chunker import Chunk


def safe_dir_name(file_path: str) -> str:
    """
    Convert an Excel file name into a safe folder name.
    """
    base = os.path.basename(file_path)
    name, _ext = os.path.splitext(base)

    safe = re.sub(r"[^A-Za-z0-9_\-\.]+", "_", name)

    return safe or "excel_file"


class VectorStore:
    def __init__(self, source_file_path: str):
        self.source_file_path = source_file_path

        # Folder where the vector database is stored.
        self.store_dir = os.path.join(
            VECTOR_DB_ROOT,
            safe_dir_name(source_file_path),
        )

        self.index_path = os.path.join(self.store_dir, "index.faiss")
        self.chunks_path = os.path.join(self.store_dir, "chunks.pkl")
        self.hash_path = os.path.join(self.store_dir, "source_hash.json")

        self.index: faiss.Index = None
        self.chunks: List[Chunk] = []

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------
    def build(self, chunks: List[Chunk], embeddings: List[List[float]]) -> None:
        """
        Build the FAISS vector index from the text embeddings.
        """
        if not chunks or not embeddings:
            raise ValueError(
                "Cannot build a vector store with no chunks/embeddings."
            )

        vectors = np.array(embeddings, dtype="float32")

        # Normalize vectors for cosine similarity.
        faiss.normalize_L2(vectors)

        dim = vectors.shape[1]

        # Create the FAISS index.
        index = faiss.IndexFlatIP(dim)

        # Add all vectors to the index.
        index.add(vectors)

        self.index = index
        self.chunks = chunks

    # ------------------------------------------------------------------
    # Save / Load
    # ------------------------------------------------------------------
    def save(self) -> None:
        """
        Save the FAISS index and chunks to disk.
        """
        os.makedirs(self.store_dir, exist_ok=True)

        faiss.write_index(self.index, self.index_path)

        with open(self.chunks_path, "wb") as f:
            pickle.dump(self.chunks, f)

    def load(self) -> bool:
        """
        Load a previously saved vector database.

        Return True if successful.
        """
        if not (
            os.path.exists(self.index_path)
            and os.path.exists(self.chunks_path)
        ):
            return False

        self.index = faiss.read_index(self.index_path)

        with open(self.chunks_path, "rb") as f:
            self.chunks = pickle.load(f)

        return True

    def exists(self) -> bool:
        """
        Check if the saved vector database exists.
        """
        return (
            os.path.exists(self.index_path)
            and os.path.exists(self.chunks_path)
        )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------
    def search(
        self,
        query_embedding: List[float],
        top_k: int,
    ) -> List[Tuple[Chunk, float]]:
        """
        Search for the most similar text chunks.

        Return the matching chunks and their similarity scores.
        """
        if self.index is None:
            raise RuntimeError(
                "Vector store is not loaded/built yet."
            )

        vec = np.array([query_embedding], dtype="float32")

        # Normalize the query vector.
        faiss.normalize_L2(vec)

        top_k = min(top_k, self.index.ntotal)

        if top_k == 0:
            return []

        scores, indices = self.index.search(vec, top_k)

        results: List[Tuple[Chunk, float]] = []

        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue

            results.append(
                (self.chunks[idx], float(score))
            )

        return results