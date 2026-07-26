# class Chunker:

#     def __init__(self,
#                  rows_per_chunk=20):

#         self.rows_per_chunk = rows_per_chunk

#     def chunk(self, documents):

#         chunks = []

#         current = []

#         metadata = None

#         for doc in documents:

#             if metadata is None:
#                 metadata = doc["metadata"]

#             current.append(doc["text"])

#             if len(current) == self.rows_per_chunk:

#                 chunks.append({

#                     "text": "\n\n".join(current),

#                     "metadata": metadata

#                 })

#                 current = []
#                 metadata = None

#         if current:

#             chunks.append({

#                 "text": "\n\n".join(current),

#                 "metadata": metadata

#             })

#         return chunks