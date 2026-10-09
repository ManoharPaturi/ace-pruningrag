"""Evidence with exact text provenance for the initial web retrieval smoke test."""

import hashlib
import re
from dataclasses import asdict, dataclass

from .dataset import QueryInput


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    interaction_id: str
    source_kind: str
    page_index: int
    source_url: str
    source_title: str
    source_time: str
    field: str
    char_start: int
    char_end: int
    content: str
    word_count: int

    def as_dict(self) -> dict:
        return asdict(self)


def web_chunks(query: QueryInput, chunk_words: int) -> list[Evidence]:
    if chunk_words < 1:
        raise ValueError("chunk_words must be positive")
    chunks = []
    for page_index, page in enumerate(query.search_results):
        for field in ("page_result", "page_snippet"):
            text = page[field]
            words = list(re.finditer(r"\S+", text))
            for offset in range(0, len(words), chunk_words):
                span = words[offset : offset + chunk_words]
                start, end = span[0].start(), span[-1].end()
                content = text[start:end]
                identity = (
                    f"{query.interaction_id}\0{page_index}\0{field}\0{start}\0{end}\0{content}"
                )
                chunks.append(
                    Evidence(
                        hashlib.sha256(identity.encode()).hexdigest(),
                        query.interaction_id,
                        "web",
                        page_index,
                        page["page_url"],
                        page["page_name"],
                        page["page_last_modified"],
                        field,
                        start,
                        end,
                        content,
                        len(span),
                    )
                )
    return chunks
