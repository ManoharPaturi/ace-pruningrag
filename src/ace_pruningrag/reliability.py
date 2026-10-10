"""Conservative, bounded verification of explicit historical closing-price claims.

Inputs must be authenticated by the caller. This is not a general web claim parser.
"""

import math
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date

from .historical_prices import ClosingPriceRequest


@dataclass(frozen=True)
class PriceClaim:
    ticker: str
    date: str
    value: float
    source_ref: str
    currency: str | None = None
    basis: str | None = None

    def __post_init__(self):
        if type(self.value) not in (int, float) or not math.isfinite(self.value):
            raise ValueError("finite scalar price required")
        date.fromisoformat(self.date)
        if not self.source_ref or not self.ticker:
            raise ValueError("identity and provenance required")


def matching_claims(request: ClosingPriceRequest, claims: tuple[PriceClaim, ...]):
    if date.fromisoformat(request.requested_date) >= date.fromisoformat(request.available_as_of):
        return ()
    return tuple(
        c for c in claims if c.ticker == request.ticker and c.date == request.requested_date
    )


def conflicts(claims: tuple[PriceClaim, ...]) -> bool:
    """Only compare equal entity/date/unit/basis; duplicate sources cannot vote."""
    for i, left in enumerate(claims):
        for right in claims[i + 1 :]:
            if (left.ticker, left.date, left.currency, left.basis) != (
                right.ticker,
                right.date,
                right.currency,
                right.basis,
            ):
                continue
            if not math.isclose(left.value, right.value, rel_tol=0, abs_tol=1e-6):
                return True
    return False


def sufficient(request: ClosingPriceRequest, claims: tuple[PriceClaim, ...]) -> bool:
    eligible = matching_claims(request, claims)
    return bool(eligible) and not conflicts(eligible)


def bounded_retrieve(
    request: ClosingPriceRequest,
    claims: tuple[PriceClaim, ...],
    fetch: Callable[[], tuple[PriceClaim, ...]],
    max_extra_calls: int = 1,
) -> tuple[tuple[PriceClaim, ...], int]:
    """One initial evidence round and at most one additional structured lookup."""
    if type(max_extra_calls) is not int or max_extra_calls not in (0, 1):
        raise ValueError("extra-call cap must be zero or one")
    if sufficient(request, claims) or max_extra_calls == 0:
        return claims, 0
    # Conflicts remain visible; fetching another copy is never a majority resolution.
    extra = fetch()
    return claims + extra, 1


def verify_price_answer(
    prediction: str,
    request: ClosingPriceRequest,
    claims: tuple[PriceClaim, ...],
    check_conflicts: bool = True,
) -> str:
    """Verify only bare numbers or a strict entity/date closing-price sentence.

    Unsupported currency, prose, rounding, and missing evidence fail closed. This
    deliberately trades coverage for support; rejected prose is not labeled wrong.
    """
    text = prediction.strip()
    if text.casefold() == "i don't know.":
        return "generator_abstained"
    eligible = matching_claims(request, claims)
    if not eligible:
        return "missing_dated_evidence"
    if check_conflicts and conflicts(eligible):
        return "unresolved_conflict"
    number = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
    if re.fullmatch(number, text):
        value = float(text)
    else:
        sentence = re.fullmatch(
            rf"{re.escape(request.ticker)}['’]s closing price yesterday "
            rf"\({re.escape(request.requested_date)}\) was ({number})\.",
            text,
            flags=re.IGNORECASE,
        )
        if not sentence:
            return "unparsed_or_unsupported_details"
        value = float(sentence.group(1))
    if not math.isfinite(value):
        return "price_mismatch"
    return (
        "supported_price_field"
        if any(math.isclose(value, c.value, rel_tol=0, abs_tol=1e-6) for c in eligible)
        else "price_mismatch"
    )
