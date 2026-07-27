# """
# config.py
# ---------
# Central configuration for the Local Excel RAG system.
# All tunable parameters live here so behaviour can be adjusted
# without touching application logic.
# """

# import os

# # --------------------------------------------------------------------------
# # Ollama connection
# # --------------------------------------------------------------------------
# OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

# # Models (as required by the project spec)
# LLM_MODEL = os.environ.get("RAG_LLM_MODEL", "qwen2.5:7b")
# EMBED_MODEL = os.environ.get("RAG_EMBED_MODEL", "nomic-embed-text")

# # Timeouts (seconds)
# OLLAMA_REQUEST_TIMEOUT = 120
# OLLAMA_EMBED_TIMEOUT = 60

# # --------------------------------------------------------------------------
# # Chunking
# # --------------------------------------------------------------------------
# # Character-based chunking (works uniformly for Arabic/English/mixed text).
# CHUNK_SIZE = 800
# CHUNK_OVERLAP = 120

# # --------------------------------------------------------------------------
# # Retrieval
# # --------------------------------------------------------------------------
# TOP_K = 5

# # --------------------------------------------------------------------------
# # Storage
# # --------------------------------------------------------------------------
# # Root directory where one sub-folder per Excel file is created, containing:
# #   - index.faiss      -> FAISS vector index
# #   - metadata.pkl      -> list of chunk texts + metadata
# #   - source_hash.json  -> SHA-256 hash + info about the source file
# VECTOR_DB_ROOT = os.environ.get("RAG_VECTOR_DB_ROOT", "vector_dbs")

# # --------------------------------------------------------------------------
# # Excel processing
# # --------------------------------------------------------------------------
# # Rows/columns that are entirely empty (NaN/blank) are dropped automatically.
# # A column is considered "empty" if all values in it are NaN/blank across
# # the whole sheet.
# DROP_FULLY_EMPTY_ROWS = True
# DROP_FULLY_EMPTY_COLUMNS = True

# # Batch size for embedding requests sent to Ollama.
# EMBED_BATCH_SIZE = 16

# # --------------------------------------------------------------------------
# # SQLite / Text-to-SQL (structured query path)
# # --------------------------------------------------------------------------
# # Every Excel sheet is also loaded into a local SQLite database (one table
# # per sheet) so aggregation/filtering/counting questions can be answered
# # precisely via a generated SQL query instead of semantic retrieval.
# SQLITE_ENABLED = True

# # Max rows returned by any generated SQL query (auto-appended as LIMIT if
# # the LLM's query doesn't already have one).
# SQL_MAX_ROWS = 200

# # Read-only SQLite connection timeout (seconds).
# SQL_QUERY_TIMEOUT = 15

# # --------------------------------------------------------------------------
# # Routing (SQL vs semantic vs hybrid)
# # --------------------------------------------------------------------------
# # "sql"      -> counts, sums, averages, filters, sorting, comparisons
# # "semantic" -> fuzzy / descriptive free-text search (uses FAISS)
# # "hybrid"   -> both paths are used and combined into one answer
# # If a fast keyword heuristic can't confidently decide, an LLM classification
# # call is used as a fallback.
# ENABLE_SQL_ROUTE = True
# ENABLE_SEMANTIC_ROUTE = True

# # If a SQL query executes successfully but returns zero rows (no exact
# # match), automatically fall back to semantic search and surface the
# # closest/related rows instead of just saying "not found".
# ENABLE_SIMILAR_FALLBACK = True

# # --------------------------------------------------------------------------
# # Misc
# # --------------------------------------------------------------------------
# VERBOSE = True
"""
config.py
---------
This file stores the main settings for the Local Excel RAG system.

If you want to change how the system works, you can change the values
here instead of editing the main program.
"""

import os

# --------------------------------------------------------------------------
# Ollama settings
# --------------------------------------------------------------------------

# Address of the local Ollama server.
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

# Models used by the project.
LLM_MODEL = os.environ.get("RAG_LLM_MODEL", "qwen2.5:7b")
EMBED_MODEL = os.environ.get("RAG_EMBED_MODEL", "nomic-embed-text")

# Time limits for requests (in seconds).
OLLAMA_REQUEST_TIMEOUT = 120
OLLAMA_EMBED_TIMEOUT = 60

# --------------------------------------------------------------------------
# Chunk settings
# --------------------------------------------------------------------------

# Maximum number of characters in each chunk.
CHUNK_SIZE = 800

# Number of overlapping characters between chunks.
CHUNK_OVERLAP = 120

# --------------------------------------------------------------------------
# Retrieval settings
# --------------------------------------------------------------------------

# Number of results to return during semantic search.
TOP_K = 15

# --------------------------------------------------------------------------
# Storage settings
# --------------------------------------------------------------------------

# Folder where the vector databases are saved.
# Each Excel file gets its own folder containing:
# - index.faiss
# - chunks.pkl
# - source_hash.json
VECTOR_DB_ROOT = os.environ.get("RAG_VECTOR_DB_ROOT", "vector_dbs")

# --------------------------------------------------------------------------
# Excel processing settings
# --------------------------------------------------------------------------

# Remove rows that are completely empty.
DROP_FULLY_EMPTY_ROWS = True

# Remove columns that are completely empty.
DROP_FULLY_EMPTY_COLUMNS = True

# Number of texts sent to Ollama at one time for embeddings.
EMBED_BATCH_SIZE = 16

# --------------------------------------------------------------------------
# SQLite settings
# --------------------------------------------------------------------------

# Build a SQLite database from the Excel file.
SQLITE_ENABLED = True

# Maximum number of rows returned from a SQL query.
SQL_MAX_ROWS = 200

# SQLite timeout (in seconds).
SQL_QUERY_TIMEOUT = 15

# --------------------------------------------------------------------------
# Routing settings
# --------------------------------------------------------------------------

# Enable SQL-based search.
ENABLE_SQL_ROUTE = True

# Enable semantic (vector) search.
ENABLE_SEMANTIC_ROUTE = True

# If SQL finds no matching rows, automatically try semantic search.
ENABLE_SIMILAR_FALLBACK = True

# --------------------------------------------------------------------------
# Other settings
# --------------------------------------------------------------------------

# Show progress messages while the program is running.
VERBOSE = True