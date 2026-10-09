import itertools

import pytest

from ace_pruningrag.selection import Candidate, SelectionProblem, Weights


def candidate(identity, support, relevance=0.5, kind="web"):
    return Candidate(
        identity, "evidence " + identity, kind, "snapshot:" + identity, relevance, tuple(support)
    )


def problem(items, budget=2, weights=None, similarities=None, conflicts=None):
    return SelectionProblem(
        items,
        ("entity", "value"),
        ((0, 1),),
        similarities or {},
        conflicts or {},
        len,
        budget,
        2,
        weights,
    )


def test_joint_pair_can_overcome_zero_single_item_gains():
    items = [candidate("a", (1, 0)), candidate("b", (0, 1), kind="api"), candidate("z", (0, 0), 1)]
    p = problem(items, weights=Weights(0, 0, 1, 0, 0))
    assert [i.evidence_id for i in p.select("joint")] == ["a", "b"]
    assert p.objective(p.select("exact")) == 1
    assert p.components((items[0],))["complementarity"] == 0


def test_one_item_coverage_is_not_cross_item_complementarity():
    p = problem([candidate("a", (1, 1))])
    assert p.components(p.select("joint"))["coverage"] == 1
    assert p.components(p.select("joint"))["complementarity"] == 0


def test_permutation_repeatability_and_budget_all_methods():
    items = [candidate("a", (1, 0)), candidate("b", (0, 1)), candidate("c", (1, 0))]
    for method in ("top_k", "mmr", "coverage", "joint", "exact"):
        outcomes = set()
        for order in itertools.permutations(items):
            p = problem(list(order), budget=1)
            selected = p.select(method)
            assert p.context_cost(selected) <= 1
            outcomes.add(tuple(i.evidence_id for i in selected))
        assert len(outcomes) == 1


def test_budget_counts_full_context_not_additive_approximation():
    p = problem([candidate("a", (1, 0)), candidate("b", (0, 1))])
    p.cost = lambda selected: 0 if not selected else 1 if len(selected) == 1 else 100
    for method in ("top_k", "mmr", "coverage", "joint", "exact"):
        assert len(p.select(method)) <= 1


def test_mmr_penalizes_duplicate_and_conflict_reduces_joint_objective():
    items = [candidate("a", (1, 0), 1), candidate("b", (1, 0), 0.9), candidate("c", (0, 1), 0.8)]
    p = problem(items, similarities={("a", "b"): 1}, conflicts={("a", "c"): 1})
    assert [i.evidence_id for i in p.select("mmr", 0.5)] == ["a", "c"]
    assert p.components((items[0], items[2]))["conflict"] == 1
    clean = problem(items)
    assert p.objective((items[0], items[2])) < clean.objective((items[0], items[2]))


def test_exact_is_upper_bound_for_experimental_objective():
    p = problem([candidate("a", (1, 0)), candidate("b", (0, 1)), candidate("c", (1, 1), 1)])
    optimum = p.objective(p.select("exact"))
    for method in ("top_k", "mmr", "coverage", "joint"):
        assert p.objective(p.select(method)) <= optimum + 1e-12


@pytest.mark.parametrize(
    "items",
    [
        [candidate("a", (1, 0)), candidate("a", (0, 1))],
        [candidate("a", (float("nan"), 0))],
        [candidate("a", (1,))],
        [candidate("a", (1, 0), 2)],
        [candidate("a", (1, 0), kind="gold")],
    ],
)
def test_invalid_features_fail(items):
    with pytest.raises(ValueError):
        problem(items)


def test_unaffordable_and_empty_pools():
    p = problem([candidate("a", (1, 1))])
    p.cost = lambda selected: 100 if selected else 0
    assert p.select("joint") == ()
    assert problem([]).select("exact") == ()
