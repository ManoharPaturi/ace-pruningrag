"""Experimental inference-only selectors; features are predictions, never gold labels."""

import math
from collections.abc import Callable
from dataclasses import dataclass
from itertools import combinations


@dataclass(frozen=True)
class Candidate:
    evidence_id: str
    content: str
    source_kind: str
    source_ref: str
    relevance: float
    support: tuple[float, ...]


@dataclass(frozen=True)
class Weights:
    relevance: float = 0.2
    coverage: float = 0.6
    complementarity: float = 0.2
    redundancy: float = 0.1
    conflict: float = 0.5


class SelectionProblem:
    """Shared candidate pool, predicted requirements, pair features, and exact cost function.

    Coverage is mean maximum predicted support per requirement. Complementarity
    counts fully covered requirement groups whose coverage needs multiple items.
    These scores are experimental features, not calibrated probabilities.
    """

    def __init__(
        self,
        candidates: list[Candidate],
        requirements: tuple[str, ...],
        groups: tuple[tuple[int, ...], ...],
        similarities: dict[tuple[str, str], float],
        conflicts: dict[tuple[str, str], float],
        cost: Callable[[tuple[Candidate, ...]], int],
        budget: int,
        max_items: int,
        weights: Weights | None = None,
    ):
        weights = weights or Weights()
        if any(isinstance(v, bool) or not isinstance(v, int) for v in (budget, max_items)):
            raise ValueError("budget and max_items must be integers")
        if budget < 1 or max_items < 1 or not requirements:
            raise ValueError("positive budget/max_items and nonempty requirements are required")
        self.candidates = tuple(sorted(candidates, key=lambda item: item.evidence_id))
        ids = [item.evidence_id for item in self.candidates]
        if len(set(ids)) != len(ids) or any(not identity for identity in ids):
            raise ValueError("candidate IDs must be nonempty and unique")
        if len(set(requirements)) != len(requirements) or any(not r for r in requirements):
            raise ValueError("requirements must be unique and nonempty")
        for item in self.candidates:
            if item.source_kind not in ("web", "api") or not item.source_ref or not item.content:
                raise ValueError("evidence needs content and web/API provenance")
            if len(item.support) != len(requirements):
                raise ValueError("support vector must match requirements")
            for value in (item.relevance, *item.support):
                self._unit(value)
        for group in groups:
            if len(group) < 2 or len(set(group)) != len(group):
                raise ValueError("complementarity groups need distinct requirements")
            if any(index < 0 or index >= len(requirements) for index in group):
                raise ValueError("requirement index out of range")
        if len(set(groups)) != len(groups):
            raise ValueError("duplicate requirement groups")
        for features in (similarities, conflicts):
            for pair, value in features.items():
                if len(pair) != 2 or pair[0] >= pair[1] or any(i not in ids for i in pair):
                    raise ValueError("pair features need sorted distinct known candidate IDs")
                self._unit(value)
        for value in vars(weights).values():
            if not math.isfinite(value) or value < 0:
                raise ValueError("weights must be finite and nonnegative")
        self.requirements, self.groups = requirements, groups
        self.similarities, self.conflicts = dict(similarities), dict(conflicts)
        self.cost, self.budget, self.max_items, self.weights = cost, budget, max_items, weights
        self._cost_cache: dict[tuple[str, ...], int] = {}

    @staticmethod
    def _unit(value: float) -> None:
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("feature values must be finite in [0, 1]")

    def context_cost(self, selected: tuple[Candidate, ...]) -> int:
        ordered = tuple(sorted(selected, key=lambda item: item.evidence_id))
        key = tuple(item.evidence_id for item in ordered)
        if key not in self._cost_cache:
            value = self.cost(ordered)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError("context cost must be a nonnegative integer")
            self._cost_cache[key] = value
        return self._cost_cache[key]

    def feasible(self, selected: tuple[Candidate, ...]) -> bool:
        return len(selected) <= self.max_items and self.context_cost(selected) <= self.budget

    def components(self, selected: tuple[Candidate, ...]) -> dict[str, float]:
        maxima = [
            max((item.support[i] for item in selected), default=0.0)
            for i in range(len(self.requirements))
        ]
        joint = 0
        for group in self.groups:
            complete = all(maxima[i] == 1.0 for i in group)
            one_item = any(all(item.support[i] == 1.0 for i in group) for item in selected)
            joint += int(complete and not one_item)
        pairs = [
            tuple(sorted((a.evidence_id, b.evidence_id))) for a, b in combinations(selected, 2)
        ]
        # Constant denominators make component magnitudes comparable across set sizes.
        pair_capacity = max(1, self.max_items * (self.max_items - 1) / 2)
        return {
            "relevance": sum(item.relevance for item in selected) / self.max_items,
            "coverage": sum(maxima) / len(maxima),
            "complementarity": joint / max(1, len(self.groups)),
            "redundancy": sum(self.similarities.get(pair, 0.0) for pair in pairs) / pair_capacity,
            "conflict": sum(self.conflicts.get(pair, 0.0) for pair in pairs) / pair_capacity,
        }

    def objective(self, selected: tuple[Candidate, ...]) -> float:
        c = self.components(selected)
        w = self.weights
        return (
            w.relevance * c["relevance"]
            + w.coverage * c["coverage"]
            + w.complementarity * c["complementarity"]
            - w.redundancy * c["redundancy"]
            - w.conflict * c["conflict"]
        )

    def select(self, method: str, mmr_lambda: float = 0.7) -> tuple[Candidate, ...]:
        if method not in ("top_k", "mmr", "coverage", "joint", "exact"):
            raise ValueError("unknown selector")
        self._unit(mmr_lambda)
        if method == "exact":
            if len(self.candidates) > 14:
                raise ValueError("exact diagnostic limited to 14 candidates")
            feasible = [
                subset
                for size in range(min(self.max_items, len(self.candidates)) + 1)
                for subset in combinations(self.candidates, size)
                if self.feasible(subset)
            ]
            return min(
                feasible,
                key=lambda subset: (
                    -self.objective(subset),
                    self.context_cost(subset),
                    tuple(i.evidence_id for i in subset),
                ),
            )
        selected: tuple[Candidate, ...] = ()
        while len(selected) < self.max_items:
            remaining = [item for item in self.candidates if item not in selected]
            options = []
            sizes = (1, 2) if method == "joint" else (1,)
            for size in sizes:
                for bundle in combinations(remaining, size):
                    proposed = tuple(sorted((*selected, *bundle), key=lambda i: i.evidence_id))
                    if not self.feasible(proposed):
                        continue
                    if method == "top_k":
                        gain = bundle[0].relevance
                    elif method == "mmr":
                        item = bundle[0]
                        similarity = max(
                            (
                                self.similarities.get(
                                    tuple(sorted((item.evidence_id, old.evidence_id))), 0.0
                                )
                                for old in selected
                            ),
                            default=0,
                        )
                        gain = mmr_lambda * item.relevance - (1 - mmr_lambda) * similarity
                    elif method == "coverage":
                        gain = (
                            self.components(proposed)["coverage"]
                            - self.components(selected)["coverage"]
                        )
                    else:
                        gain = self.objective(proposed) - self.objective(selected)
                    options.append(
                        (
                            -gain,
                            self.context_cost(proposed),
                            tuple(item.evidence_id for item in proposed),
                            proposed,
                        )
                    )
            if not options:
                break
            best = min(options)
            # Top-K and MMR fill available slots; marginal coverage/joint stop at no gain.
            if method in ("coverage", "joint") and -best[0] <= 0:
                break
            selected = best[3]
        return selected


def render_context(selected: tuple[Candidate, ...]) -> str:
    """Identical deterministic context representation for every selector."""
    return "\n\n".join(
        f"[{item.evidence_id}] {item.source_kind} {item.source_ref}\n{item.content}"
        for item in sorted(selected, key=lambda item: item.evidence_id)
    )
