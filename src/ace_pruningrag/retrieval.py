"""Independent, offline BM25 sanity baseline; not the published PruningRAG retriever."""

import math
import re
from collections import Counter

from .evidence import Evidence


def terms(text: str) -> list[str]:
    return re.findall(r"\w+", text.casefold())


def bm25_rank(
    query: str,
    evidence: list[Evidence],
    k1: float = 1.5,
    b: float = 0.75,
) -> list[tuple[Evidence, float]]:
    if k1 <= 0 or not 0 <= b <= 1:
        raise ValueError("BM25 requires k1 > 0 and b in [0, 1]")
    if not evidence:
        return []
    counts = [Counter(terms(item.content)) for item in evidence]
    lengths = [sum(count.values()) for count in counts]
    average = sum(lengths) / len(lengths)
    if average == 0:
        return sorted(((item, 0.0) for item in evidence), key=lambda pair: pair[0].evidence_id)
    frequency = Counter(term for count in counts for term in count)
    query_terms = set(terms(query))
    ranked = []
    for item, count, length in zip(evidence, counts, lengths, strict=True):
        score = 0.0
        for term in query_terms:
            tf = count[term]
            if not tf:
                continue
            df = frequency[term]
            idf = math.log(1 + (len(evidence) - df + 0.5) / (df + 0.5))
            score += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * length / average))
        ranked.append((item, score))
    return sorted(ranked, key=lambda pair: (-pair[1], pair[0].evidence_id))


def select_context(
    ranked: list[tuple[Evidence, float]],
    top_k: int,
    max_words: int,
) -> list[tuple[Evidence, float]]:
    if top_k < 1 or max_words < 1:
        raise ValueError("top_k and max_words must be positive")
    selected = []
    used = 0
    for item, score in ranked:
        if used + item.word_count <= max_words:
            selected.append((item, score))
            used += item.word_count
        if len(selected) == top_k:
            break
    return selected
