# """
# router.py
# ---------
# Decides which retrieval path(s) should answer a given question:

#   - "sql"      -> structured query: counts, sums, averages, filters,
#                   sorting, comparisons, "top N", date ranges, etc.
#   - "semantic" -> fuzzy / descriptive free-text search (FAISS retrieval).
#   - "hybrid"   -> ambiguous, or likely needs both structured and
#                   free-text reasoning together.

# A fast keyword heuristic (English + Arabic) handles the common, obvious
# cases without any extra round trip. Anything it can't confidently classify
# falls back to a lightweight LLM classification call.
# """

# import re
# from typing import Optional

# from config import ENABLE_SQL_ROUTE, ENABLE_SEMANTIC_ROUTE
# from src.ollama_client import chat_completion

# _SQL_HINT_PATTERNS = [
#     r"\bhow many\b", r"\bcount\b", r"\btotal\b", r"\bsum\b", r"\baverage\b",
#     r"\bavg\b", r"\bmax(imum)?\b", r"\bmin(imum)?\b", r"\bgreater than\b",
#     r"\bless than\b", r"\bat least\b", r"\bat most\b", r"\bbetween\b",
#     r"\btop \d+\b", r"\blist all\b", r"\bnumber of\b", r"\bhighest\b",
#     r"\blowest\b", r"\bmore than\b", r"\bfewer than\b", r"\bsorted by\b",
#     r"\bgroup(ed)? by\b",
#     # Arabic equivalents
#     r"كم عدد", r"مجموع", r"متوسط", r"أكبر من", r"أصغر من", r"أقل من",
#     r"أعلى", r"أدنى", r"عدد", r"إجمالي",
# ]

# _SQL_HINT_RE = re.compile("|".join(_SQL_HINT_PATTERNS), re.IGNORECASE)


# def heuristic_route(question: str) -> Optional[str]:
#     """Fast, deterministic classification. Returns None if not confident."""
#     if _SQL_HINT_RE.search(question):
#         return "sql"
#     return None


# def llm_route(question: str) -> str:
#     """LLM-based fallback classification for anything the heuristic misses."""
#     system_prompt = (
#         "Classify the user's question about a spreadsheet database into "
#         "exactly one category:\n"
#         "- 'sql': requires counting, summing, averaging, filtering, sorting, "
#         "or aggregating structured data (e.g. totals, comparisons, rankings, "
#         "date ranges).\n"
#         "- 'semantic': requires fuzzy or descriptive search over free text "
#         "(e.g. finding rows that match a description or topic).\n"
#         "- 'hybrid': the question is ambiguous or likely needs both.\n"
#         "Respond with exactly one word: sql, semantic, or hybrid. "
#         "No explanation."
#     )
#     raw = chat_completion(system_prompt, question, temperature=0.0).strip().lower()
#     if "hybrid" in raw:
#         return "hybrid"
#     if "sql" in raw:
#         return "sql"
#     if "semantic" in raw:
#         return "semantic"
#     return "hybrid"


# def route_question(question: str) -> str:
#     """
#     Return one of "sql", "semantic", "hybrid", honoring whichever routes
#     are enabled in config. Falls back gracefully if a route is disabled.
#     """
#     if not ENABLE_SQL_ROUTE:
#         return "semantic"
#     if not ENABLE_SEMANTIC_ROUTE:
#         return "sql"

#     route = heuristic_route(question)
#     if route is None:
#         route = llm_route(question)
#     return route

"""
router.py
---------
This file decides which search method should be used to answer
a user's question.

It can choose:
- "sql"      -> for questions about numbers, totals, filters, or calculations.
- "semantic" -> for questions that need meaning-based text search.
- "hybrid"   -> when both SQL and semantic search may be useful.

It first uses simple keywords to make a quick decision.
If it is not sure, it asks the language model to decide.
"""

import re
from typing import Optional

from config import ENABLE_SQL_ROUTE, ENABLE_SEMANTIC_ROUTE
from src.ollama_client import chat_completion

_SQL_HINT_PATTERNS = [
    r"\bhow many\b", r"\bcount\b", r"\btotal\b", r"\bsum\b", r"\baverage\b",
    r"\bavg\b", r"\bmax(imum)?\b", r"\bmin(imum)?\b", r"\bgreater than\b",
    r"\bless than\b", r"\bat least\b", r"\bat most\b", r"\bbetween\b",
    r"\btop \d+\b", r"\blist all\b", r"\bnumber of\b", r"\bhighest\b",
    r"\blowest\b", r"\bmore than\b", r"\bfewer than\b", r"\bsorted by\b",
    r"\bgroup(ed)? by\b",

    # Arabic keywords
    r"كم عدد", r"مجموع", r"متوسط", r"أكبر من", r"أصغر من", r"أقل من",
    r"أعلى", r"أدنى", r"عدد", r"إجمالي",
]

_SQL_HINT_RE = re.compile("|".join(_SQL_HINT_PATTERNS), re.IGNORECASE)


def heuristic_route(question: str) -> Optional[str]:
    """
    Quickly check if the question looks like a SQL question.

    Return:
    - "sql" if a SQL keyword is found.
    - None if no clear match is found.
    """
    if _SQL_HINT_RE.search(question):
        return "sql"

    return None


def llm_route(question: str) -> str:
    """
    Ask the language model to decide which route to use
    when the keyword check is not enough.
    """
    system_prompt = (
        "Classify the user's question about a spreadsheet database into "
        "exactly one category:\n"
        "- 'sql': requires counting, summing, averaging, filtering, sorting, "
        "or aggregating structured data.\n"
        "- 'semantic': requires meaning-based search over text.\n"
        "- 'hybrid': needs both SQL and semantic search.\n"
        "Respond with exactly one word: sql, semantic, or hybrid."
    )

    raw = chat_completion(
        system_prompt,
        question,
        temperature=0.0,
    ).strip().lower()

    if "hybrid" in raw:
        return "hybrid"

    if "sql" in raw:
        return "sql"

    if "semantic" in raw:
        return "semantic"

    # Default choice if the response is unclear.
    return "hybrid"


def route_question(question: str) -> str:
    """
    Decide which search method should answer the question.

    The result will be one of:
    - "sql"
    - "semantic"
    - "hybrid"

    The function also checks which routes are enabled
    in the project settings.
    """
    if not ENABLE_SQL_ROUTE:
        return "semantic"

    if not ENABLE_SEMANTIC_ROUTE:
        return "sql"

    # Try the keyword-based method first.
    route = heuristic_route(question)

    # If no decision was made, ask the language model.
    if route is None:
        route = llm_route(question)

    return route