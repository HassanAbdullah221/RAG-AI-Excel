import json
import faiss
import numpy as np
import pandas as pd
import ollama

# ==========================
# CONFIGURATION
# ==========================

EXCEL_FILES = [
    "employees.xlsx"
]

LLM_MODEL = "qwen2.5:7b"
EMBED_MODEL = "nomic-embed-text"

TOP_K = 10


# ==========================
# READ EXCEL FILES
# ==========================

documents = []

for file in EXCEL_FILES:

    sheets = pd.read_excel(file, sheet_name=None)

    for sheet_name, df in sheets.items():

        df = df.fillna("")

        text = df.to_markdown(index=False)

        documents.append({
            "text": text,
            "file": file,
            "sheet": sheet_name
        })

print(f"Loaded {len(documents)} document(s).")


# ==========================
# CREATE EMBEDDINGS
# ==========================

vectors = []

for doc in documents:

    response = ollama.embeddings(
        model=EMBED_MODEL,
        prompt=doc["text"]
    )

    vectors.append(response["embedding"])

vectors = np.array(vectors).astype("float32")


# ==========================
# CREATE FAISS INDEX
# ==========================

dimension = len(vectors[0])

index = faiss.IndexFlatL2(dimension)

index.add(vectors)

print("Vector database created.")


# ==========================
# ASK FUNCTION
# ==========================

def ask(question):

    q = ollama.embeddings(
        model=EMBED_MODEL,
        prompt=question
    )["embedding"]

    q = np.array([q]).astype("float32")

    distances, ids = index.search(q, TOP_K)

    context = ""

    for i in ids[0]:

        if i == -1:
            continue

        context += documents[i]["text"]
        context += "\n\n"

    prompt = f"""
You are an assistant answering questions ONLY using the provided Excel data.

Rules:

1. Use ONLY the provided context.
2. Do NOT use outside knowledge.
3. Read ALL retrieved rows before answering.
4. The answer may require combining multiple fields from the SAME row.
5. If the question contains multiple conditions (for example: department + position, city + salary, joining date + department), find the row that satisfies ALL conditions.
6. Do not answer using partial matches.
7. If multiple rows satisfy the conditions, list all of them.
8. If no row satisfies all conditions, reply EXACTLY:

Context:

{context}

Question:

{question}

Answer:
"""

    response = ollama.chat(
        model=LLM_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    print("\nAnswer:\n")
    print(response["message"]["content"])


# ==========================
# CHAT LOOP
# ==========================

print("\nExcel RAG")
print("Type 'exit' to quit.\n")

while True:

    question = input("Question: ")

    if question.lower() == "exit":
        break

    ask(question)