# Local Excel Hybrid RAG (Ollama + FAISS + SQLite)

A fully local, offline **hybrid** Retrieval-Augmented Generation system that lets
you ask natural-language questions (English, Arabic, or mixed) about the
contents of **any** Excel (`.xlsx` / `.xlsm`) file — no code changes needed per
file.

- **LLM:** `qwen2.5:7b` (via [Ollama](https://ollama.com))
- **Embeddings:** `nomic-embed-text` (via Ollama)
- **Semantic vector store:** [FAISS](https://github.com/facebookresearch/faiss) (local, on-disk)
- **Structured query store:** SQLite (local, on-disk, one table per sheet)

Everything runs on your machine. After the two models are pulled once, no
internet connection is required.

---

## Why hybrid?

Excel data is tabular. Pure semantic (RAG) search is great for fuzzy,
descriptive questions but bad at math over the whole table — it only sees the
top-k most similar rows, so counts/sums/filters over hundreds of rows will be
wrong or incomplete. Pure Text-to-SQL is precise for structured questions but
can't handle vague, descriptive, or free-text search well.

This project routes every question to whichever approach fits it best:

| Question type | Example | Path used |
|---|---|---|
| Aggregation / counting | "How many employees are in Sales?" | **SQL** |
| Filtering / comparison | "List products priced over 500" | **SQL** |
| Sorting / ranking | "Top 5 highest paid employees" | **SQL** |
| Fuzzy / descriptive | "Tell me about the manager named Ahmed" | **Semantic (FAISS)** |
| Ambiguous / mixed | Unclear which is needed | **Hybrid (both)**, combined into one answer |

If the generated SQL fails validation or execution for any reason, the system
automatically falls back to the semantic path so you still get an answer.

---

## How it works

### Build / refresh (only when the file changes)

1. **Read** every worksheet in the workbook (any number of sheets).
2. **Auto-detect** columns — any names, any count, any data types.
3. **Drop** fully empty rows and fully empty columns.
4. **Semantic path**:
   - Convert each row into a readable text document (`"Sheet 'X' record -> Col1: val1; Col2: val2; ..."`), preserving metadata (source file, sheet name, row number).
   - Chunk documents (character-based, with overlap) so long rows aren't lost.
   - Embed each chunk with `nomic-embed-text` via the local Ollama server.
   - Store vectors in a FAISS index.
5. **Structured path**:
   - Load every sheet into its own auto-generated SQLite table (column/table names sanitized for SQL, original names preserved alongside for the LLM's benefit).
6. **Hash-check**: a single SHA-256 hash of the Excel file is stored once and
   controls **both** stores. On every run:
   - **Unchanged** -> both the FAISS index and SQLite database are loaded from cache (fast).
   - **Changed / new file** -> both are rebuilt automatically.

### Query

1. **Route** the question -> `sql`, `semantic`, or `hybrid` (fast keyword
   heuristic first, LLM classification as a fallback for ambiguous cases).
2. **`sql`**: the LLM generates a SQL query against the auto-detected schema.
   The query is strictly validated (single `SELECT` statement only, no
   DDL/DML keywords, executed on a read-only connection, row-limited) before
   running.
3. **`semantic`**: the question is embedded and the most relevant chunks are
   retrieved from FAISS (cosine similarity, top-k).
4. **`hybrid`**: both paths run and their results are combined into one
   context.
5. **Generate**: only the resulting context (SQL result table and/or
   retrieved rows — never the whole spreadsheet) is sent to `qwen2.5:7b`,
   which produces the final answer.

Nothing in the code assumes a specific file name, sheet name, column name,
schema, or number of columns/sheets — everything is detected at runtime.

### SQL safety

The Text-to-SQL path is defense-in-depth:
- Only a single `SELECT` (or `WITH ... SELECT`) statement is accepted — no
  semicolons, no stacked statements.
- Any DDL/DML keyword (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`,
  `ATTACH`, `PRAGMA`, ...) causes the query to be rejected before it ever
  touches the database.
- The SQLite connection used to run the query is opened **read-only**
  (`mode=ro`), so even a validation gap can't mutate data.
- A `LIMIT` is enforced on every query to bound how much data is ever
  returned into the LLM's context.

---

## Prerequisites

1. **Install Ollama**: https://ollama.com/download
2. **Pull the required models**:
   ```bash
   ollama pull qwen2.5:7b
   ollama pull nomic-embed-text
   ```
3. **Start the Ollama server** (if it isn't already running as a service):
   ```bash
   ollama serve
   ```

---

## Installation

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Usage

```bash
python main.py <path_to_excel_file>
```

Examples:

```bash
python main.py employees.xlsx
python main.py sales_report.xlsx
python main.py "/path/to/مبيعات.xlsx"
```

If no path is given, you'll be prompted for one interactively:

```bash
python main.py
No Excel file path was provided as an argument.
Please enter the path to your Excel (.xlsx) file: employees.xlsx
```

Once the vector database is ready, you'll get an interactive prompt:

```
Question: How many employees are in the Sales department?
Answer: ...

Question: exit
Goodbye.
```

Run the same command again later:
- If the Excel file **hasn't changed**, the existing vector database is
  reused instantly.
- If the Excel file **has changed** (even a single cell), the vector
  database is automatically rebuilt on the next run.

---

## Project structure

```
.
├── main.py                  # CLI entry point
├── config.py                 # All tunable settings (models, chunk size, top-k, paths)
├── requirements.txt
├── src/
│   ├── excel_loader.py       # Generic, schema-agnostic Excel reader
│   ├── document_builder.py   # Row -> readable text document + metadata
│   ├── chunker.py             # Text chunking with overlap
│   ├── ollama_client.py      # Ollama HTTP client (embeddings + chat)
│   ├── vector_store.py        # FAISS index build/save/load/search
│   ├── sqlite_store.py        # SQLite table build/load/query (one table per sheet)
│   ├── sql_agent.py           # Text-to-SQL generation + strict safety validation
│   ├── router.py              # Decides sql / semantic / hybrid per question
│   ├── hash_utils.py          # SHA-256 change detection (shared by both stores)
│   └── hybrid_pipeline.py     # Orchestrates build + query across both stores
└── vector_dbs/                # Auto-created; one folder per Excel file
    └── <file_name>/
        ├── index.faiss        # FAISS vector index (semantic path)
        ├── chunks.pkl          # Chunk text + metadata (semantic path)
        ├── data.sqlite3        # SQLite database (structured path)
        ├── schema_map.json     # Sanitized <-> original table/column name mapping
        └── source_hash.json    # Shared SHA-256 hash controlling rebuilds
```

---

## Notes on data handling

- **Arabic / English / mixed text**: handled natively as UTF-8 strings; no
  transliteration or language-specific logic is required.
- **Numbers**: floats that represent whole numbers are stored as integers;
  other floats are rounded to 6 decimal places for readability.
- **Dates**: rendered as `YYYY-MM-DD` (or `YYYY-MM-DD HH:MM:SS` when a time
  component is present).
- **Booleans**: rendered as `Yes` / `No`.
- **Empty cells**: rendered as `N/A` within a row's text, and fully empty
  rows/columns are dropped before indexing.
- **Large files / many sheets**: embeddings are generated in batches with a
  progress bar; FAISS scales to millions of vectors on a single machine.

---

## Configuration

Adjust `config.py` (or set the corresponding environment variables) to tune:

| Setting | Purpose | Default |
|---|---|---|
| `LLM_MODEL` | Ollama chat model | `qwen2.5:7b` |
| `EMBED_MODEL` | Ollama embedding model | `nomic-embed-text` |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | Text chunking | `800` / `120` |
| `TOP_K` | Number of chunks retrieved per question | `5` |
| `VECTOR_DB_ROOT` | Where vector/SQL databases are stored | `vector_dbs` |
| `OLLAMA_BASE_URL` | Ollama server address | `http://localhost:11434` |
| `SQLITE_ENABLED` | Enable the structured (Text-to-SQL) path | `True` |
| `SQL_MAX_ROWS` | Max rows returned by any SQL query | `200` |
| `ENABLE_SQL_ROUTE` / `ENABLE_SEMANTIC_ROUTE` | Toggle each path independently | `True` / `True` |

---

## Troubleshooting

- **"Could not reach Ollama..."** — Make sure `ollama serve` is running and
  that `qwen2.5:7b` / `nomic-embed-text` have been pulled.
- **Slow first run** — The first run on a new/changed file embeds every row;
  subsequent runs reuse the cached FAISS index instantly.
- **Empty answer / "not available in the provided data"** — The question's
  topic may genuinely not be present in the spreadsheet, or may need to be
  phrased using terms closer to the actual column values.
