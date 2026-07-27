# """
# hybrid_pipeline.py
# -------------------
# Orchestrates the full hybrid RAG system for a single Excel file:

#   Build/refresh (only when the file's SHA-256 hash changes):
#     1. Read every worksheet (generic, schema-agnostic).
#     2. Build a FAISS vector index over row-level text chunks
#        (nomic-embed-text embeddings) -> semantic search path.
#     3. Build a SQLite database, one table per sheet -> structured
#        (Text-to-SQL) path.
#     Both stores live side by side under one directory per Excel file and
#     share a single SHA-256 hash file, so a single "did the file change?"
#     check controls whether BOTH stores are rebuilt together.

#   Query:
#     1. Route the question -> "sql", "semantic", or "hybrid".
#     2. "sql": generate + validate + run a SQL query; on any failure,
#        fall back to the semantic path so the user still gets an answer.
#        If the query executes but returns zero rows (no exact match),
#        automatically fall back to semantic search for the closest
#        related rows, with an explicit note telling the LLM (and thus
#        the user) that these are similar, not exact, matches.
#     3. "semantic": embed the question, retrieve top-k chunks from FAISS.
#     4. "hybrid": run both and combine their context.
#     5. Send only the resulting context (SQL result table and/or retrieved
#        rows) to qwen2.5:7b and return its answer.
# """

# import os
# import sqlite3
# from typing import List, Tuple

# from tqdm import tqdm

# from config import (
#     TOP_K,
#     EMBED_BATCH_SIZE,
#     VERBOSE,
#     SQLITE_ENABLED,
#     VECTOR_DB_ROOT,
#     ENABLE_SIMILAR_FALLBACK,
# )
# from src.excel_loader import load_excel
# from src.document_builder import build_documents
# from src.chunker import chunk_documents, Chunk
# from src.vector_store import VectorStore, safe_dir_name
# from src.sqlite_store import SQLiteStore
# from src.sql_agent import run_text_to_sql, format_sql_result_as_text, SQLSafetyError
# from src.router import route_question
# from src.hash_utils import compute_file_hash, file_has_changed, write_stored_hash
# from src.ollama_client import (
#     get_embeddings_batch,
#     generate_answer,
#     check_ollama_available,
# )


# def _log(msg: str) -> None:
#     if VERBOSE:
#         print(msg)


# class HybridPipeline:
#     def __init__(self, excel_path: str):
#         if not os.path.isfile(excel_path):
#             raise FileNotFoundError(f"Excel file not found: {excel_path}")
#         if not excel_path.lower().endswith((".xlsx", ".xlsm")):
#             raise ValueError("Only .xlsx / .xlsm Excel files are supported.")

#         self.excel_path = excel_path
#         self.file_name = os.path.basename(excel_path)

#         self.store_dir = os.path.join(VECTOR_DB_ROOT, safe_dir_name(excel_path))
#         self.hash_path = os.path.join(self.store_dir, "source_hash.json")

#         self.vector_store = VectorStore(excel_path)
#         self.sql_store = SQLiteStore(self.store_dir) if SQLITE_ENABLED else None

#     # ------------------------------------------------------------------
#     # Build / load
#     # ------------------------------------------------------------------
#     def prepare(self) -> None:
#         """Ensure both stores are ready to query (loaded from cache or rebuilt)."""
#         check_ollama_available()

#         stores_exist = self.vector_store.exists() and (
#             not SQLITE_ENABLED or self.sql_store.exists()
#         )

#         needs_rebuild = True
#         if stores_exist and not file_has_changed(self.excel_path, self.hash_path):
#             _log(f"[INFO] No changes detected in '{self.file_name}'. "
#                  f"Loading existing vector database and SQL database...")
#             vector_loaded = self.vector_store.load()
#             sql_loaded = (not SQLITE_ENABLED) or self.sql_store.load_schema_map()
#             if vector_loaded and sql_loaded:
#                 needs_rebuild = False
#                 _log(f"[INFO] Loaded {len(self.vector_store.chunks)} chunks "
#                      f"and {len(self.sql_store.schema_map) if SQLITE_ENABLED else 0} "
#                      f"SQL table(s) from cache.")

#         if needs_rebuild:
#             self._build_indexes()

#     def _build_indexes(self) -> None:
#         _log(f"[INFO] Reading workbook '{self.file_name}' ...")
#         sheets = load_excel(self.excel_path)
#         if not sheets:
#             raise ValueError(
#                 f"No usable data found in '{self.file_name}'. "
#                 f"The workbook may be empty or all sheets/rows are blank."
#             )
#         _log(f"[INFO] Found {len(sheets)} non-empty sheet(s): "
#              f"{', '.join(s.sheet_name for s in sheets)}")

#         # ---- Semantic path: documents -> chunks -> embeddings -> FAISS ----
#         documents = build_documents(self.file_name, sheets)
#         _log(f"[INFO] Built {len(documents)} row-level document(s).")

#         chunks: List[Chunk] = chunk_documents(documents)
#         _log(f"[INFO] Split into {len(chunks)} chunk(s) for embedding.")

#         texts = [c.text for c in chunks]
#         embeddings = []
#         _log("[INFO] Generating embeddings via Ollama (nomic-embed-text)...")
#         for i in tqdm(range(0, len(texts), EMBED_BATCH_SIZE), disable=not VERBOSE):
#             batch = texts[i:i + EMBED_BATCH_SIZE]
#             embeddings.extend(get_embeddings_batch(batch))

#         self.vector_store.build(chunks, embeddings)
#         self.vector_store.save()

#         # ---- Structured path: sheets -> SQLite tables ----
#         if SQLITE_ENABLED:
#             _log("[INFO] Building SQLite database (one table per sheet)...")
#             self.sql_store.build(sheets)
#             _log(f"[INFO] Created {len(self.sql_store.schema_map)} SQL table(s).")

#         # ---- Shared hash (controls rebuild for BOTH stores together) ----
#         file_hash = compute_file_hash(self.excel_path)
#         write_stored_hash(self.hash_path, file_hash, self.excel_path)

#         _log(f"[INFO] Indexes built and saved to '{self.store_dir}'.")

#     # ------------------------------------------------------------------
#     # Query
#     # ------------------------------------------------------------------
#     def _semantic_context(self, question: str, top_k: int) -> str:
#         query_embedding = get_embeddings_batch([question])[0]
#         results = self.vector_store.search(query_embedding, top_k)
#         if not results:
#             return ""

#         blocks = []
#         for chunk, _score in results:
#             meta = chunk.metadata
#             source_info = (
#                 f"[File: {meta.get('source_file')} | "
#                 f"Sheet: {meta.get('sheet_name')} | "
#                 f"Row: {meta.get('row_number')}]"
#             )
#             blocks.append(f"{source_info}\n{chunk.text}")
#         return "Retrieved rows (semantic search):\n" + "\n\n".join(blocks)

#     def _sql_context(self, question: str) -> Tuple[str, bool]:
#         """Returns (context_text, found_exact_match)."""
#         sql, columns, rows = run_text_to_sql(question, self.sql_store)
#         _log(f"[INFO] Generated SQL: {sql}")
#         return format_sql_result_as_text(sql, columns, rows), bool(rows)

#     def answer(self, question: str, top_k: int = TOP_K) -> str:
#         """Route the question, gather context from the appropriate store(s),
#         and generate the final answer using only that context."""
#         if self.vector_store.index is None:
#             raise RuntimeError("Pipeline not prepared. Call prepare() first.")

#         route = "semantic"
#         if SQLITE_ENABLED:
#             route = route_question(question)
#         _log(f"[INFO] Routing question to: '{route}'")

#         context_parts: List[str] = []
#         sql_ran_but_empty = False

#         if route in ("sql", "hybrid") and SQLITE_ENABLED:
#             try:
#                 sql_ctx, found_rows = self._sql_context(question)
#                 context_parts.append(sql_ctx)
#                 sql_ran_but_empty = not found_rows
#             except (SQLSafetyError, sqlite3.Error) as exc:
#                 _log(f"[WARN] SQL path failed ({exc}); falling back to semantic search.")
#                 if route == "sql":
#                     route = "semantic"

#         need_semantic = route in ("semantic", "hybrid") or not context_parts

#         # No exact SQL match -> automatically pull the closest semantically
#         # similar rows instead of just reporting "not found".
#         similar_fallback_used = False
#         if ENABLE_SIMILAR_FALLBACK and sql_ran_but_empty and not need_semantic:
#             _log("[INFO] SQL found no exact match; falling back to semantic "
#                  "search for similar results.")
#             need_semantic = True
#             similar_fallback_used = True

#         if need_semantic:
#             semantic_ctx = self._semantic_context(question, top_k)
#             if semantic_ctx:
#                 if similar_fallback_used:
#                     semantic_ctx = (
#                         "NOTE TO ASSISTANT: The exact filter/criteria in the "
#                         "question did not match any rows. The rows below are "
#                         "the closest semantically similar matches, NOT exact "
#                         "matches. You must clearly tell the user that no "
#                         "exact match was found, then present these as "
#                         "related/similar results.\n\n" + semantic_ctx
#                     )
#                 context_parts.append(semantic_ctx)

#         if not context_parts:
#             return ("I could not find any relevant information in the Excel "
#                      "file to answer this question.")

#         context = "\n\n".join(context_parts)
#         return generate_answer(question, context)

"""
hybrid_pipeline.py
------------------
This file controls the whole hybrid RAG pipeline for one Excel file.

When the Excel file changes, it:
1. Loads all worksheets.
2. Builds a vector database for semantic search.
3. Builds a SQLite database for SQL queries.
4. Saves both databases so they can be reused later.

When a user asks a question, it:
1. Decides whether to use SQL, semantic search, or both.
2. Gets the relevant information.
3. Sends only that information to the LLM.
4. Returns the final answer.
"""

import os
import sqlite3
from typing import List, Tuple

from tqdm import tqdm

from config import (
    TOP_K,
    EMBED_BATCH_SIZE,
    VERBOSE,
    SQLITE_ENABLED,
    VECTOR_DB_ROOT,
    ENABLE_SIMILAR_FALLBACK,
)
from src.excel_loader import load_excel
from src.document_builder import build_documents
from src.chunker import chunk_documents, Chunk
from src.vector_store import VectorStore, safe_dir_name
from src.sqlite_store import SQLiteStore
from src.sql_agent import run_text_to_sql, format_sql_result_as_text, SQLSafetyError
from src.router import route_question
from src.hash_utils import compute_file_hash, file_has_changed, write_stored_hash
from src.ollama_client import (
    get_embeddings_batch,
    generate_answer,
    check_ollama_available,
)


def _log(msg: str) -> None:
    """Print messages only if verbose mode is enabled."""
    if VERBOSE:
        print(msg)


class HybridPipeline:
    def __init__(self, excel_path: str):
        # Check that the file exists.
        if not os.path.isfile(excel_path):
            raise FileNotFoundError(f"Excel file not found: {excel_path}")

        # Only Excel files are supported.
        if not excel_path.lower().endswith((".xlsx", ".xlsm")):
            raise ValueError("Only .xlsx / .xlsm Excel files are supported.")

        self.excel_path = excel_path
        self.file_name = os.path.basename(excel_path)

        # Folder where the vector database and SQL database are stored.
        self.store_dir = os.path.join(VECTOR_DB_ROOT, safe_dir_name(excel_path))
        self.hash_path = os.path.join(self.store_dir, "source_hash.json")

        self.vector_store = VectorStore(excel_path)
        self.sql_store = SQLiteStore(self.store_dir) if SQLITE_ENABLED else None

    # ------------------------------------------------------------------
    # Build / Load
    # ------------------------------------------------------------------
    def prepare(self) -> None:
        """
        Make sure the vector database and SQL database are ready.

        If the Excel file has not changed, load the existing databases.
        Otherwise, rebuild everything.
        """
        check_ollama_available()

        stores_exist = self.vector_store.exists() and (
            not SQLITE_ENABLED or self.sql_store.exists()
        )

        needs_rebuild = True

        if stores_exist and not file_has_changed(self.excel_path, self.hash_path):
            _log(
                f"[INFO] No changes detected in '{self.file_name}'. "
                f"Loading existing vector database and SQL database..."
            )

            vector_loaded = self.vector_store.load()
            sql_loaded = (not SQLITE_ENABLED) or self.sql_store.load_schema_map()

            if vector_loaded and sql_loaded:
                needs_rebuild = False

                _log(
                    f"[INFO] Loaded {len(self.vector_store.chunks)} chunks "
                    f"and {len(self.sql_store.schema_map) if SQLITE_ENABLED else 0} "
                    f"SQL table(s) from cache."
                )

        if needs_rebuild:
            self._build_indexes()

    def _build_indexes(self) -> None:
        """Build both the vector database and SQLite database."""
        _log(f"[INFO] Reading workbook '{self.file_name}' ...")

        sheets = load_excel(self.excel_path)

        if not sheets:
            raise ValueError(
                f"No usable data found in '{self.file_name}'. "
                f"The workbook may be empty or all sheets/rows are blank."
            )

        _log(
            f"[INFO] Found {len(sheets)} non-empty sheet(s): "
            f"{', '.join(s.sheet_name for s in sheets)}"
        )

        # Create documents from Excel rows.
        documents = build_documents(self.file_name, sheets)
        _log(f"[INFO] Built {len(documents)} row-level document(s).")

        # Split documents into chunks.
        chunks: List[Chunk] = chunk_documents(documents)
        _log(f"[INFO] Split into {len(chunks)} chunk(s) for embedding.")

        texts = [c.text for c in chunks]
        embeddings = []

        _log("[INFO] Generating embeddings via Ollama...")

        for i in tqdm(range(0, len(texts), EMBED_BATCH_SIZE), disable=not VERBOSE):
            batch = texts[i:i + EMBED_BATCH_SIZE]
            embeddings.extend(get_embeddings_batch(batch))

        # Build and save the vector database.
        self.vector_store.build(chunks, embeddings)
        self.vector_store.save()

        # Build the SQLite database.
        if SQLITE_ENABLED:
            _log("[INFO] Building SQLite database...")

            self.sql_store.build(sheets)

            _log(f"[INFO] Created {len(self.sql_store.schema_map)} SQL table(s).")

        # Save the file hash so we know if the Excel file changes later.
        file_hash = compute_file_hash(self.excel_path)
        write_stored_hash(self.hash_path, file_hash, self.excel_path)

        _log(f"[INFO] Indexes built and saved to '{self.store_dir}'.")

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------
    def _semantic_context(self, question: str, top_k: int) -> str:
        """
        Search the vector database and return the most similar chunks.
        """
        query_embedding = get_embeddings_batch([question])[0]
        results = self.vector_store.search(query_embedding, top_k)

        if not results:
            return ""

        blocks = []

        for chunk, _score in results:
            meta = chunk.metadata

            source_info = (
                f"[File: {meta.get('source_file')} | "
                f"Sheet: {meta.get('sheet_name')} | "
                f"Row: {meta.get('row_number')}]"
            )

            blocks.append(f"{source_info}\n{chunk.text}")

        return "Retrieved rows (semantic search):\n" + "\n\n".join(blocks)

    def _sql_context(self, question: str) -> Tuple[str, bool]:
        """
        Run a SQL query and return:
        - the formatted results
        - whether any rows were found
        """
        sql, columns, rows = run_text_to_sql(question, self.sql_store)

        _log(f"[INFO] Generated SQL: {sql}")

        return format_sql_result_as_text(sql, columns, rows), bool(rows)

    def answer(self, question: str, top_k: int = TOP_K) -> str:
        """
        Answer a user's question using SQL, semantic search,
        or both depending on the router.
        """
        if self.vector_store.index is None:
            raise RuntimeError("Pipeline not prepared. Call prepare() first.")

        route = "semantic"

        if SQLITE_ENABLED:
            route = route_question(question)

        _log(f"[INFO] Routing question to: '{route}'")

        context_parts: List[str] = []
        sql_ran_but_empty = False

        # Try the SQL path if needed.
        if route in ("sql", "hybrid") and SQLITE_ENABLED:
            try:
                sql_ctx, found_rows = self._sql_context(question)

                context_parts.append(sql_ctx)
                sql_ran_but_empty = not found_rows

            except (SQLSafetyError, sqlite3.Error) as exc:
                _log(f"[WARN] SQL path failed ({exc}); falling back to semantic search.")

                if route == "sql":
                    route = "semantic"

        need_semantic = route in ("semantic", "hybrid") or not context_parts

        # If SQL found nothing, try semantic search instead.
        similar_fallback_used = False

        if ENABLE_SIMILAR_FALLBACK and sql_ran_but_empty and not need_semantic:
            _log("[INFO] SQL found no exact match. Trying semantic search.")

            need_semantic = True
            similar_fallback_used = True

        if need_semantic:
            semantic_ctx = self._semantic_context(question, top_k)

            if semantic_ctx:
                if similar_fallback_used:
                    semantic_ctx = (
                        "NOTE TO ASSISTANT: No exact match was found. "
                        "The rows below are only similar matches.\n\n"
                        + semantic_ctx
                    )

                context_parts.append(semantic_ctx)

        # Nothing was found.
        if not context_parts:
            return (
                "I could not find any relevant information in the Excel "
                "file to answer this question."
            )

        # Combine all retrieved information and generate the answer.
        context = "\n\n".join(context_parts)

        return generate_answer(question, context)