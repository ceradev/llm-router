from __future__ import annotations

import re
from collections import Counter

# Compact English stopword list for keyword extraction (fast lookup).
_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "as",
        "is",
        "was",
        "are",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "can",
        "this",
        "that",
        "these",
        "those",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "me",
        "him",
        "her",
        "us",
        "them",
        "my",
        "your",
        "his",
        "its",
        "our",
        "their",
        "what",
        "which",
        "who",
        "whom",
        "when",
        "where",
        "why",
        "how",
        "all",
        "each",
        "every",
        "both",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "nor",
        "not",
        "only",
        "own",
        "same",
        "so",
        "than",
        "too",
        "very",
        "just",
        "also",
        "now",
        "here",
        "there",
        "then",
        "if",
        "because",
        "about",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "from",
        "up",
        "down",
        "out",
        "off",
        "over",
        "under",
        "again",
        "once",
    }
)

_WORD_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?", re.IGNORECASE)

# Technical terms aligned with routing-relevant vocabulary (subset of intent hints).
_TECH_TERMS: frozenset[str] = frozenset(
    {
        "api",
        "sql",
        "python",
        "javascript",
        "typescript",
        "json",
        "schema",
        "function",
        "class",
        "debug",
        "refactor",
        "deploy",
        "docker",
        "kubernetes",
        "database",
        "query",
        "async",
        "http",
        "rest",
        "graphql",
        "oauth",
        "lambda",
        "regex",
        "algorithm",
        "architecture",
        "microservice",
    }
)


def normalize_prompt(text: str) -> str:
    return " ".join(text.split())


def tokenize_words(text: str) -> list[str]:
    return [m.group(0).lower() for m in _WORD_RE.finditer(text)]


def sentence_count(text: str) -> int:
    if not text.strip():
        return 0
    parts = re.split(r"[.!?]+", text)
    return max(1, sum(1 for p in parts if p.strip()))


def extract_keywords(text: str, *, top_n: int = 10) -> list[str]:
    words = tokenize_words(text)
    filtered = [w for w in words if w not in _STOPWORDS and len(w) > 1]
    if not filtered:
        return []
    counts = Counter(filtered)
    # Stable tie-break: alphabetical
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [word for word, _ in ranked[:top_n]]


def technical_term_hits(words: list[str]) -> int:
    return sum(1 for w in words if w in _TECH_TERMS)


def complexity_from_heuristics(
    *,
    raw_len: int,
    sentences: int,
    tech_hits: int,
    word_count: int,
) -> float:
    length_component = min(1.0, raw_len / 500.0)
    sentence_component = min(1.0, sentences / 8.0)
    tech_component = min(1.0, tech_hits / 5.0) if word_count else 0.0
    # Weighted blend; stays in [0, 1]
    blended = 0.45 * length_component + 0.35 * sentence_component + 0.2 * tech_component
    return min(1.0, blended)
