from dataclasses import replace

import pytest

from ace_pruningrag.dataset import validate_record
from ace_pruningrag.evidence import web_chunks
from ace_pruningrag.retrieval import bm25_rank, select_context


def test_chunk_spans_recover_original_text(row):
    query = validate_record(row).inference_input()
    chunks = web_chunks(query, 2)
    assert len({item.evidence_id for item in chunks}) == len(chunks)
    for item in chunks:
        original = query.search_results[item.page_index][item.field]
        assert original[item.char_start : item.char_end] == item.content
        assert 0 < item.word_count <= 2
        assert item.source_url == "https://example.test/device"
    assert chunks == web_chunks(query, 2)


def test_ranking_and_budget_skip_oversized_evidence(row):
    evidence = web_chunks(validate_record(row).inference_input(), 100)[0]
    relevant = replace(evidence, evidence_id="relevant", content="built 2020", word_count=2)
    irrelevant = replace(evidence, evidence_id="other", content="unrelated unrelated", word_count=2)
    ranked = bm25_rank("2020", [irrelevant, relevant])
    assert ranked[0][0] == relevant
    selected = select_context([(evidence, 100), *ranked], top_k=3, max_words=4)
    assert [item.evidence_id for item, _ in selected] == ["relevant", "other"]
    assert sum(item.word_count for item, _ in selected) <= 4


def test_deterministic_ties_and_empty_text(row):
    evidence = web_chunks(validate_record(row).inference_input(), 100)[0]
    a = replace(evidence, evidence_id="a", content="!!!")
    b = replace(evidence, evidence_id="b", content="???")
    assert [item.evidence_id for item, _ in bm25_rank("query", [b, a])] == ["a", "b"]
    assert bm25_rank("query", []) == []


@pytest.mark.parametrize("k1,b", [(0, 0.75), (1.5, 1.1), (1.5, -0.1)])
def test_invalid_bm25_parameters(k1, b):
    with pytest.raises(ValueError):
        bm25_rank("query", [], k1=k1, b=b)
