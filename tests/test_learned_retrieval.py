from dataclasses import replace

import pytest

from ace_pruningrag.dataset import validate_record
from ace_pruningrag.evidence import web_chunks
from ace_pruningrag.learned_retrieval import score_ranking


def test_model_score_alignment_and_deterministic_ties(row):
    evidence = web_chunks(validate_record(row).inference_input(), 200)[0]
    a = replace(evidence, evidence_id="a")
    b = replace(evidence, evidence_id="b")
    assert score_ranking([b, a], [0.5, 0.5]) == [(a, 0.5), (b, 0.5)]
    assert score_ranking([a, b], [0.1, 0.9])[0] == (b, 0.9)


@pytest.mark.parametrize("scores", [[0.5], [float("nan"), 0.5], [float("inf"), 0.5]])
def test_unusable_model_outputs_are_rejected(row, scores):
    evidence = web_chunks(validate_record(row).inference_input(), 200)
    with pytest.raises(ValueError, match="finite score"):
        score_ranking(evidence, scores)
