import ollama


class ExcelRAG:

    def __init__(

        self,

        vector_store,

        model="qwen2.5:7b",

        similarity_threshold=1.2

    ):

        self.vector_store = vector_store

        self.model = model

        self.threshold = similarity_threshold

    # -----------------------------------

    def ask(self, question):

        retrieved = self.vector_store.search(question)

        if len(retrieved) == 0:

            return {

                "answer":

                "I couldn't find this information in the uploaded Excel file(s).",

                "sources": []

            }

        if retrieved[0]["distance"] > self.threshold:

            return {

                "answer":

                "I couldn't find this information in the uploaded Excel file(s).",

                "sources": []

            }

        context = ""

        sources = []

        for item in retrieved:

            chunk = item["chunk"]

            context += chunk["text"]

            context += "\n\n"

            sources.append(chunk["metadata"])

        prompt = f"""

You are an AI assistant.

Answer ONLY from the provided context.

Never use outside knowledge.

If the answer does not exist in the context, reply exactly:

I couldn't find this information in the uploaded Excel file(s).

Context:

{context}

Question:

{question}

Answer:

"""

        response = ollama.chat(

            model=self.model,

            messages=[

                {

                    "role": "user",

                    "content": prompt

                }

            ]

        )

        return {

            "answer":

            response["message"]["content"],

            "sources":

            sources

        }