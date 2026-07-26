import os
import pickle
import faiss
import numpy as np
import ollama


class VectorStore:

    def __init__(
        self,
        embedding_model="nomic-embed-text",
        index_path="vector.index",
        metadata_path="metadata.pkl"
    ):

        self.embedding_model = embedding_model
        self.index_path = index_path
        self.metadata_path = metadata_path

        self.index = None
        self.metadata = []

    # ----------------------------

    def create_embeddings(self, chunks):

        vectors = []

        self.metadata = []

        print("Creating embeddings...")

        for chunk in chunks:

            response = ollama.embed(
                model=self.embedding_model,
                input=chunk["text"]
            )

            vectors.append(response["embeddings"][0])

            self.metadata.append(chunk)

        vectors = np.array(vectors).astype("float32")

        dimension = vectors.shape[1]

        self.index = faiss.IndexFlatL2(dimension)

        self.index.add(vectors)

        print("Embeddings created.")

    # ----------------------------

    def save(self):

        faiss.write_index(self.index, self.index_path)

        with open(self.metadata_path, "wb") as f:
            pickle.dump(self.metadata, f)

        print("Vector database saved.")

    # ----------------------------

    def load(self):

        if not os.path.exists(self.index_path):
            return False

        self.index = faiss.read_index(self.index_path)

        with open(self.metadata_path, "rb") as f:
            self.metadata = pickle.load(f)

        print("Vector database loaded.")

        return True

    # ----------------------------

    def search(
        self,
        question,
        top_k=4
    ):

        response = ollama.embed(

            model=self.embedding_model,

            input=question

        )

        query = np.array(
            [response["embeddings"][0]]
        ).astype("float32")

        distances, ids = self.index.search(
            query,
            top_k
        )

        results = []

        for distance, idx in zip(distances[0], ids[0]):

            if idx == -1:
                continue

            results.append({

                "distance": float(distance),

                "chunk": self.metadata[idx]

            })

        return results