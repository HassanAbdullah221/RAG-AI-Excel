import os

from extractor import ExcelExtractor
from vector_store import VectorStore
from rag import ExcelRAG

# ============================================
# CONFIGURATION
# ============================================

EXCEL_FILES = [
    "employees.xlsx"   # ضع المسار الكامل إذا لم يكن الملف في نفس المجلد
]

EMBEDDING_MODEL = "nomic-embed-text"
LLM_MODEL = "qwen2.5:7b"

# ============================================
# BUILD / LOAD VECTOR DATABASE
# ============================================

vector_store = VectorStore(
    embedding_model=EMBEDDING_MODEL
)

if not vector_store.load():

    print("=" * 60)
    print("Building Vector Database...")
    print("=" * 60)

    extractor = ExcelExtractor()

    # استخراج كل صف كـ Document مستقل
    documents = extractor.extract(EXCEL_FILES)

    print(f"Extracted {len(documents)} rows.")

    # إنشاء Embeddings لكل صف
    vector_store.create_embeddings(documents)

    # حفظ الـ FAISS
    vector_store.save()

else:

    print("=" * 60)
    print("Existing Vector Database Loaded")
    print("=" * 60)

# ============================================
# CREATE RAG
# ============================================

rag = ExcelRAG(
    vector_store=vector_store,
    model=LLM_MODEL
)

# ============================================
# CHAT LOOP
# ============================================

print("\n" + "=" * 60)
print("Excel RAG")
print("Type 'exit' to quit.")
print("=" * 60)

while True:

    question = input("\nQuestion: ").strip()

    if question.lower() == "exit":
        break

    result = rag.ask(question)

    print("\nAnswer")
    print("-" * 40)
    print(result["answer"])

    if result["sources"]:

        print("\nRetrieved Rows")
        print("-" * 40)

        shown = set()

        for src in result["sources"]:

            key = (
                src["file"],
                src["sheet"],
                src["row"]
            )

            if key in shown:
                continue

            shown.add(key)

            print(
                f"File : {src['file']}\n"
                f"Sheet: {src['sheet']}\n"
                f"Row  : {src['row']}\n"
            )

print("\nGoodbye.")