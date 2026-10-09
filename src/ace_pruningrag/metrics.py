"""Published outcome-count metrics; correctness labels must come from evaluation."""

from collections import Counter
from collections.abc import Sequence


def score_outcomes(outcomes: Sequence[str]) -> dict[str, float | int]:
    """Match the upstream aggregate formula without substituting a local judge.

    The caller must supply validated exact_correct, judge_correct, miss, or incorrect
    decisions. This function cannot turn unjudged predictions into correctness labels.
    """
    allowed = {"exact_correct", "judge_correct", "miss", "incorrect"}
    if not outcomes or any(item not in allowed for item in outcomes):
        raise ValueError("non-empty, fully evaluated outcomes are required")
    counts = Counter(outcomes)
    n = len(outcomes)
    correct = counts["exact_correct"] + counts["judge_correct"]
    missed = counts["miss"]
    return {
        "total": n,
        "n_correct": correct,
        "n_correct_exact": counts["exact_correct"],
        "n_miss": missed,
        "score": (2 * correct + missed) / n - 1,
        "exact_accuracy": counts["exact_correct"] / n,
        "accuracy": correct / n,
        "hallucination": counts["incorrect"] / n,
        "missing": missed / n,
    }
