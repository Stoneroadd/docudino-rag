"""Text normalization, chunking, and explainable local BM25 retrieval."""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

STOP = {"the", "and", "for", "with", "from", "that", "this", "what", "when", "where", "which",
        "para", "con", "por", "una", "uno", "las", "los", "del", "que", "como", "donde", "cuando",
        "sobre", "entre", "este", "esta", "estos", "estas", "sus", "son", "fue", "ser", "hay"}


def tokenize(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return [word for word in re.findall(r"[a-z0-9+#.]{2,}", normalized) if word not in STOP]


def split_chunks(text: str, size: int = 180, overlap: int = 35) -> list[str]:
    words = text.split()
    if not words:
        return []
    result = []
    start = 0
    while start < len(words):
        end = min(len(words), start + size)
        result.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = max(start + 1, end - overlap)
    return result


def retrieve(query: str, chunks: list[dict], top_k: int = 5) -> list[tuple[dict, float]]:
    terms = tokenize(query)
    if not terms or not chunks:
        return []
    docs = [(chunk, Counter(tokenize(chunk.get("text", "")))) for chunk in chunks]
    n = len(docs)
    avg_len = sum(sum(counts.values()) for _, counts in docs) / max(1, n)
    document_frequency = Counter(term for term in set(terms)
                                 for _, counts in docs if counts.get(term, 0))
    scored = []
    for chunk, counts in docs:
        length = sum(counts.values())
        score = 0.0
        for term in terms:
            frequency = counts.get(term, 0)
            if not frequency:
                continue
            idf = math.log(1 + (n - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5))
            denominator = frequency + 1.5 * (1 - 0.75 + 0.75 * length / max(avg_len, 1))
            score += idf * frequency * 2.5 / denominator
        if score > 0:
            scored.append((chunk, score))
    return sorted(scored, key=lambda item: item[1], reverse=True)[:max(1, min(top_k, 20))]
