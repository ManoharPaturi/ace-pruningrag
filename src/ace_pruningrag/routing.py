"""Deterministic capability routing and shared budgets; no gold labels or calibration."""

import re
from dataclasses import asdict, dataclass
from datetime import datetime

from .dataset import QueryInput


@dataclass(frozen=True)
class Capability:
    name: str
    available: bool
    requires_as_of: bool
    as_of_date: str | None

    def __post_init__(self):
        if (
            not self.name
            or type(self.available) is not bool
            or type(self.requires_as_of) is not bool
        ):
            raise ValueError("capability needs a name and explicit availability/time flags")
        if self.as_of_date is not None:
            datetime.strptime(self.as_of_date, "%Y-%m-%d")


@dataclass(frozen=True)
class RoutingPlan:
    policy: str
    query_id: str
    requested_hints: tuple[str, ...]
    blocked_hints: tuple[tuple[str, str], ...]
    allocations: tuple[tuple[str, int], ...]
    evidence_budget: int
    reserved_tokens: int
    total_budget: int
    max_source_calls: int
    execution_status: str = "not_executed"

    def as_dict(self) -> dict:
        return asdict(self)


def source_hints(query: str) -> dict[str, int]:
    """Scores indicate keyword matches, not confidence or source necessity."""
    text = query.casefold()
    result = {"web": 1}
    patterns = {
        "finance_market_cap": r"\bmarket cap(?:italization)?s?\b",
        "finance_ticker": r"\bticker\b",
        "finance_prices": (
            r"\b(?:stock price|share price|best performer|daily moves|price change)\b"
        ),
        "sports_stats": r"\b(?:per game|3-point|three-point|batting|touchdowns)\b",
        "movie_knowledge": r"\b(?:movie|film|oscar)\b",
        "company_history": r"\b(?:ceo|previously work|prior employer)\b",
    }
    for name, pattern in patterns.items():
        count = len(re.findall(pattern, text))
        if count:
            result[name] = count
    if "finance_market_cap" in result and re.search(
        r"\b(?:historical|decade|over time|when|past years)\b", text
    ):
        result.pop("finance_market_cap")
        result["finance_timeseries"] = 1
    return result


def route(
    query: QueryInput,
    capabilities: tuple[Capability, ...],
    policy: str,
    total_budget: int,
    reserved_tokens: int,
) -> RoutingPlan:
    if policy not in ("fixed_web", "all_available", "adaptive"):
        raise ValueError("unknown routing policy")
    if any(type(value) is not int for value in (total_budget, reserved_tokens)):
        raise ValueError("budgets must be integers")
    if not 0 <= reserved_tokens < total_budget:
        raise ValueError("reserve must leave a positive evidence budget")
    inventory = {cap.name: cap for cap in capabilities}
    if len(inventory) != len(capabilities) or "web" not in inventory:
        raise ValueError("unique capabilities including web are required")
    query_date = datetime.strptime(query.query_time, "%m/%d/%Y, %H:%M:%S PT").date().isoformat()
    hints = source_hints(query.query)
    eligible = {}
    failures = {}
    for name, cap in sorted(inventory.items()):
        reason = None
        if not cap.available:
            reason = "unavailable"
        elif cap.requires_as_of and cap.as_of_date is None:
            reason = "snapshot_date_unknown"
        elif cap.requires_as_of and cap.as_of_date != query_date:
            reason = "snapshot_date_mismatch"
        if reason:
            failures[name] = reason
        else:
            eligible[name] = cap
    blocked = tuple(
        (name, failures.get(name, "capability_not_provisioned"))
        for name in sorted(hints)
        if name not in eligible
    )
    if policy == "fixed_web":
        names = ["web"] if "web" in eligible else []
    elif policy == "all_available":
        names = sorted(eligible)
    else:
        names = sorted(set(hints) & set(eligible))
    # Allocate once across all sources: a single total budget, never one per source.
    budget = total_budget - reserved_tokens
    weights = {name: hints.get(name, 1) if policy == "adaptive" else 1 for name in names}
    total_weight = sum(weights.values())
    allocations = {name: budget * weight // total_weight for name, weight in weights.items()}
    remainder = budget - sum(allocations.values()) if names else 0
    order = sorted(names, key=lambda name: (-(budget * weights[name] % total_weight), name))
    for name in order[:remainder]:
        allocations[name] += 1
    allocations = {name: tokens for name, tokens in allocations.items() if tokens > 0}
    return RoutingPlan(
        policy,
        query.interaction_id,
        tuple(sorted(hints)),
        blocked,
        tuple(sorted(allocations.items())),
        budget,
        reserved_tokens,
        total_budget,
        len(allocations),
    )
