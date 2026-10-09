import pytest

from ace_pruningrag.metrics import score_outcomes


def test_published_score_counts():
    result = score_outcomes(["exact_correct", "judge_correct", "miss", "incorrect"])
    assert result["score"] == pytest.approx(0.25)
    assert result["accuracy"] == pytest.approx(0.5)
    assert result["exact_accuracy"] == pytest.approx(0.25)
    assert result["hallucination"] == pytest.approx(0.25)
    assert result["missing"] == pytest.approx(0.25)


@pytest.mark.parametrize("outcomes", [[], ["pending"], ["exact_correct", "unjudged"]])
def test_unjudged_results_cannot_be_scored(outcomes):
    with pytest.raises(ValueError):
        score_outcomes(outcomes)
