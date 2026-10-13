import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "metrics", Path(__file__).parents[1] / "scripts/cohort_metrics.py"
)
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)


def test_paired_constant_effects_and_deterministic_resampling():
    zero = metrics.paired_interval([0] * 50)
    assert zero["mean_difference"] == 0
    assert zero["bootstrap_95_percentile_interval"] == [0, 0]
    one = metrics.paired_interval([1] * 50)
    assert one["bootstrap_95_percentile_interval"] == [1, 1]
    assert metrics.paired_interval([-1, 0, 1], samples=100) == metrics.paired_interval(
        [-1, 0, 1], samples=100
    )


def test_no_empty_or_unresampled_estimates():
    with pytest.raises(ValueError):
        metrics.paired_interval([])
    with pytest.raises(ValueError):
        metrics.paired_interval([0], samples=0)
