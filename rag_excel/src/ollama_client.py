# """
# ollama_client.py
# -----------------
# Minimal HTTP client for the local Ollama server. Handles:
#   - Generating embeddings via the "nomic-embed-text" model.
#   - Generating chat completions via the "qwen2.5:7b" model.

# No external SDK is required, only `requests`, keeping the project
# lightweight and fully offline-capable once models are pulled.
# """

# from typing import List
# import requests

# from config import (
#     OLLAMA_BASE_URL,
#     LLM_MODEL,
#     EMBED_MODEL,
#     OLLAMA_REQUEST_TIMEOUT,
#     OLLAMA_EMBED_TIMEOUT,
# )


# class OllamaError(RuntimeError):
#     """Raised when the local Ollama server cannot be reached or returns an error."""


# def check_ollama_available() -> None:
#     """Raise a clear, actionable error if Ollama isn't running / reachable."""
#     try:
#         resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
#         resp.raise_for_status()
#     except requests.exceptions.RequestException as exc:
#         raise OllamaError(
#             f"Could not reach Ollama at {OLLAMA_BASE_URL}. "
#             f"Make sure Ollama is installed and running (`ollama serve`), "
#             f"and that models '{LLM_MODEL}' and '{EMBED_MODEL}' have been pulled "
#             f"(`ollama pull {LLM_MODEL}` / `ollama pull {EMBED_MODEL}`)."
#         ) from exc


# def get_embedding(text: str) -> List[float]:
#     """Get a single embedding vector for a piece of text."""
#     url = f"{OLLAMA_BASE_URL}/api/embeddings"
#     payload = {"model": EMBED_MODEL, "prompt": text}
#     try:
#         resp = requests.post(url, json=payload, timeout=OLLAMA_EMBED_TIMEOUT)
#         resp.raise_for_status()
#     except requests.exceptions.RequestException as exc:
#         raise OllamaError(f"Embedding request to Ollama failed: {exc}") from exc

#     data = resp.json()
#     embedding = data.get("embedding")
#     if not embedding:
#         raise OllamaError(f"Ollama returned no embedding for text: {text[:80]!r}")
#     return embedding


# def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
#     """
#     Get embeddings for a list of texts.
#     The Ollama /api/embeddings endpoint handles one prompt per request,
#     so we loop here; batching is done at a higher level (progress bar,
#     chunked persistence) to keep memory usage predictable.
#     """
#     return [get_embedding(t) for t in texts]


# def chat_completion(system_prompt: str, user_prompt: str, temperature: float = 0.0) -> str:
#     """
#     Generic single-turn chat call to qwen2.5:7b. Used by answer synthesis,
#     SQL generation, and question routing alike, so all three share the
#     same request/error handling logic.
#     """
#     url = f"{OLLAMA_BASE_URL}/api/chat"
#     payload = {
#         "model": LLM_MODEL,
#         "messages": [
#             {"role": "system", "content": system_prompt},
#             {"role": "user", "content": user_prompt},
#         ],
#         "stream": False,
#         "options": {"temperature": temperature},
#     }

#     try:
#         resp = requests.post(url, json=payload, timeout=OLLAMA_REQUEST_TIMEOUT)
#         resp.raise_for_status()
#     except requests.exceptions.RequestException as exc:
#         raise OllamaError(f"Chat generation request to Ollama failed: {exc}") from exc

#     data = resp.json()
#     message = data.get("message", {})
#     content = message.get("content")
#     if not content:
#         raise OllamaError(f"Ollama returned an empty response: {data}")
#     return content.strip()


# def generate_answer(question: str, context: str) -> str:
#     """
#     Send only the retrieved context + the user's question to qwen2.5:7b
#     and return the generated answer text. `context` may come from
#     semantic retrieval (FAISS), a SQL query result, or both combined.
#     """
#     system_prompt = (
#         "You are a helpful assistant answering questions about the contents "
#         "of an Excel workbook. Use ONLY the information provided in the "
#         "context below to answer the user's question. The context may "
#         "contain retrieved rows and/or the result of a SQL query run "
#         "against the data, in English and/or Arabic. "
#         "If the answer cannot be found in the context, clearly say that the "
#         "information is not available in the provided data - do not invent "
#         "facts. Answer in the same language as the user's question when "
#         "possible, and be concise and precise.\n\n"
#         "CRITICAL - numeric accuracy:\n"
#         "- Copy every number (salaries, prices, dates, counts, thresholds, "
#         "IDs, etc.) EXACTLY as it appears in the context or the user's "
#         "question. Do not round, rescale, add/remove digits, or change "
#         "thousands separators.\n"
#         "- Before answering, re-read every number you are about to write and "
#         "verify it matches the source character-for-character (e.g. if the "
#         "question says 10000, your answer must say 10000 / 10,000 - never "
#         "100000 or 100,000).\n"
#         "- When referencing a filter/threshold from the question (e.g. "
#         "'salary greater than 10000'), quote that exact value back rather "
#         "than paraphrasing it from memory.\n\n"
#         "Similar-match fallback:\n"
#         "- If the context includes a 'NOTE TO ASSISTANT' saying no exact "
#         "match was found and the rows shown are similar/related instead, "
#         "you MUST explicitly tell the user that no exact match was found, "
#         "then present those rows as the closest related results - never "
#         "present them as if they satisfy the original exact criteria."
#     )

#     user_prompt = (
#         f"Context:\n"
#         f"---------------------------------------------\n"
#         f"{context}\n"
#         f"---------------------------------------------\n\n"
#         f"Question: {question}\n"
#         f"Answer:"
#     )

#     return chat_completion(system_prompt, user_prompt)

"""
ollama_client.py
----------------
This file connects to the local Ollama server.

It is used to:
- Create embeddings with the "nomic-embed-text" model.
- Generate answers with the "qwen2.5:7b" model.

The project only uses the `requests` library, so no extra Ollama SDK
is needed.
"""

from typing import List
import requests

from config import (
    OLLAMA_BASE_URL,
    LLM_MODEL,
    EMBED_MODEL,
    OLLAMA_REQUEST_TIMEOUT,
    OLLAMA_EMBED_TIMEOUT,
)


class OllamaError(RuntimeError):
    """Raised when Ollama is not running or returns an error."""


def check_ollama_available() -> None:
    """
    Check if the Ollama server is running.

    If it is not available, raise a clear error message.
    """
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        raise OllamaError(
            f"Could not reach Ollama at {OLLAMA_BASE_URL}. "
            f"Make sure Ollama is installed and running (`ollama serve`), "
            f"and that models '{LLM_MODEL}' and '{EMBED_MODEL}' have been pulled "
            f"(`ollama pull {LLM_MODEL}` / `ollama pull {EMBED_MODEL}`)."
        ) from exc


def get_embedding(text: str) -> List[float]:
    """
    Generate one embedding vector for a piece of text.
    """
    url = f"{OLLAMA_BASE_URL}/api/embeddings"
    payload = {
        "model": EMBED_MODEL,
        "prompt": text,
    }

    try:
        resp = requests.post(url, json=payload, timeout=OLLAMA_EMBED_TIMEOUT)
        resp.raise_for_status()

    except requests.exceptions.RequestException as exc:
        raise OllamaError(f"Embedding request to Ollama failed: {exc}") from exc

    data = resp.json()
    embedding = data.get("embedding")

    if not embedding:
        raise OllamaError(
            f"Ollama returned no embedding for text: {text[:80]!r}"
        )

    return embedding


def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts.

    Ollama creates one embedding per request,
    so this function loops through all texts.
    """
    return [get_embedding(t) for t in texts]


def chat_completion(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.0,
) -> str:
    """
    Send a chat request to the language model
    and return the generated response.
    """
    url = f"{OLLAMA_BASE_URL}/api/chat"

    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }

    try:
        resp = requests.post(
            url,
            json=payload,
            timeout=OLLAMA_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()

    except requests.exceptions.RequestException as exc:
        raise OllamaError(
            f"Chat generation request to Ollama failed: {exc}"
        ) from exc

    data = resp.json()
    message = data.get("message", {})
    content = message.get("content")

    if not content:
        raise OllamaError(f"Ollama returned an empty response: {data}")

    return content.strip()


def generate_answer(question: str, context: str) -> str:
    """
    Generate the final answer using only the retrieved context.

    The context may come from:
    - semantic search
    - SQL queries
    - both together
    """
    system_prompt = (
    "You are an intelligent assistant answering questions about an Excel workbook. "
    "You must use ONLY the information provided in the context below. "
    "Do not use outside knowledge or information that is not present in the Excel data.\n\n"
    "The context may contain retrieved rows from semantic search and/or results "
    "from SQL queries. Analyze the provided data carefully and answer the user's "
    "question using reasoning based on the workbook contents.\n\n"
    "You are allowed to:\n"
    "- summarize information from the data\n"
    "- compare values between rows\n"
    "- identify patterns and trends\n"
    "- calculate or explain relationships between values\n"
    "- make conclusions that are directly supported by the Excel data\n\n"
    "If the answer is not available or cannot be reasonably concluded from the "
    "provided data, clearly say that the information is not available in the "
    "Excel file. Do not guess using general knowledge.\n\n"
    "Answer in the same language as the user's question whenever possible. "
    "Be clear, helpful, and concise.\n\n"
    "CRITICAL - numeric accuracy:\n"
    "- Copy numbers exactly as they appear in the context.\n"
    "- Do not change, round, or modify numbers, dates, IDs, salaries, prices, "
    "or counts.\n"
    "- Verify every number before including it in your answer.\n\n"
    "Similar-match fallback:\n"
    "- If the context indicates that no exact match exists and similar rows are "
    "provided, clearly explain that these are related results and not exact matches."
    )

    user_prompt = (
        f"Context:\n"
        f"---------------------------------------------\n"
        f"{context}\n"
        f"---------------------------------------------\n\n"
        f"Question: {question}\n"
        f"Answer:"
    )

    return chat_completion(system_prompt, user_prompt)