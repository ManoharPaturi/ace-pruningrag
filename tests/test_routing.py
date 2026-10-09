import pytest

from ace_pruningrag.dataset import QueryInput, validate_record
from ace_pruningrag.routing import Capability, route, source_hints


def query(text="market cap and ticker", time="03/05/2024, 23:18:31 PT"):
    return QueryInput("fixture", text, time, ())


def inventory(date=None):
    return (
        Capability("web", True, False, None),
        Capability("finance_market_cap", True, True, date),
        Capability("finance_ticker", True, True, date),
    )


def test_unverified_finance_cannot_be_promoted_to_available():
    plan = route(query(), inventory(), "adaptive", 1536, 256)
    assert plan.allocations == (("web", 1280),)
    assert all(reason == "snapshot_date_unknown" for _, reason in plan.blocked_hints)
    assert plan.execution_status == "not_executed"


def test_date_mismatch_blocks_and_matched_date_allocates_shared_budget():
    blocked = route(query(), inventory("2024-03-06"), "adaptive", 1536, 256)
    assert all(reason == "snapshot_date_mismatch" for _, reason in blocked.blocked_hints)
    matched = route(query(), inventory("2024-03-05"), "adaptive", 1536, 256)
    assert len(matched.allocations) == 3
    assert sum(tokens for _, tokens in matched.allocations) + matched.reserved_tokens == 1536
    assert matched.max_source_calls == 3


def test_adaptive_does_not_allocate_irrelevant_available_api():
    q = query("Which mountain is tallest?")
    adaptive = route(q, inventory("2024-03-05"), "adaptive", 1536, 256)
    all_sources = route(q, inventory("2024-03-05"), "all_available", 1536, 256)
    assert adaptive.allocations == (("web", 1280),)
    assert len(all_sources.allocations) == 3
    assert sum(t for _, t in all_sources.allocations) == 1280


def test_tiny_budget_determinism_and_no_zero_allocation():
    q = query()
    for caps in (inventory("2024-03-05"), tuple(reversed(inventory("2024-03-05")))):
        plan = route(q, caps, "adaptive", 2, 1)
        assert plan.allocations == (("finance_market_cap", 1),)
        assert plan.max_source_calls == 1


def test_source_hints_are_not_complete_source_necessity():
    assert "finance_prices" in source_hints("what company is the best performer today?")
    historical = source_hints("historical market capitalizations over the past decade")
    assert "finance_timeseries" in historical and "finance_market_cap" not in historical
    plan = route(query("3-point attempts per game"), inventory(), "adaptive", 1536, 256)
    assert ("sports_stats", "capability_not_provisioned") in plan.blocked_hints
    assert plan.allocations == (("web", 1280),)


def test_no_gold_fields_in_route_input(row):
    row["query_time"] = "03/05/2024, 23:18:31 PT"
    q = validate_record(row).inference_input()
    before = route(q, inventory(), "adaptive", 1536, 256)
    row.update(answer="different gold", domain="finance", split=999)
    after = route(validate_record(row).inference_input(), inventory(), "adaptive", 1536, 256)
    assert before == after


@pytest.mark.parametrize("budget,reserve", [(1, 1), (0, 0), (100, -1), (True, 0), (100, 1.5)])
def test_invalid_budgets_fail(budget, reserve):
    with pytest.raises(ValueError):
        route(query(), inventory(), "adaptive", budget, reserve)


def test_unavailable_web_does_not_get_budget_and_unknown_policy_fails():
    assert (
        route(query(), (Capability("web", False, False, None),), "adaptive", 10, 0).allocations
        == ()
    )
    with pytest.raises(ValueError):
        route(query(), inventory(), "unknown", 10, 0)


def test_adaptive_keyword_weights_change_allocation_under_same_total():
    q = query("market cap, market cap and ticker")
    plan = route(q, inventory("2024-03-05"), "adaptive", 100, 10)
    allocated = dict(plan.allocations)
    assert allocated["finance_market_cap"] == 45
    assert allocated["finance_ticker"] + allocated["web"] == 45
    assert sum(allocated.values()) == 90
