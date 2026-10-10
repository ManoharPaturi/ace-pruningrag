import pytest

from ace_pruningrag.historical_prices import ClosingPriceRequest
from ace_pruningrag.reliability import (
    PriceClaim,
    bounded_retrieve,
    conflicts,
    sufficient,
    verify_price_answer,
)

REQ = ClosingPriceRequest("BLACW", "2024-02-27", "2024-02-28")


def claim(value=0.0125, **kwargs):
    return PriceClaim("BLACW", "2024-02-27", value, "snapshot/BLACW/date", **kwargs)


def test_comparable_conflicts_and_no_majority_resolution():
    a, b = claim(), claim(0.01)
    assert conflicts((a, a, a, b))
    assert not sufficient(REQ, (a, a, b))
    assert not conflicts((a, claim(0.01, currency="USD")))
    old = PriceClaim("BLACW", "2024-02-26", 3, "old")
    assert not conflicts((a, old))
    assert not sufficient(REQ, (old,))


def test_retry_cap_and_no_retry_when_sufficient():
    calls = []

    def fetch():
        calls.append(1)
        return (claim(),)

    result, cost = bounded_retrieve(REQ, (), fetch)
    assert cost == len(calls) == 1 and sufficient(REQ, result)
    assert bounded_retrieve(REQ, result, fetch) == (result, 0)
    assert len(calls) == 1
    assert bounded_retrieve(REQ, (), fetch, 0) == ((), 0)
    with pytest.raises(ValueError):
        bounded_retrieve(REQ, (), fetch, 2)


def test_missing_and_conflicting_retry_stops_without_overriding():
    assert bounded_retrieve(REQ, (), lambda: ()) == ((), 1)
    evidence, calls = bounded_retrieve(REQ, (claim(), claim(1)), lambda: (claim(),))
    assert calls == 1 and not sufficient(REQ, evidence)
    assert verify_price_answer("0.0125", REQ, evidence) == "unresolved_conflict"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True])
def test_invalid_prices(value):
    with pytest.raises(ValueError):
        claim(value)


def test_claim_verification_precision_currency_date_and_injection():
    evidence = (claim(),)
    assert verify_price_answer("0.0125", REQ, evidence) == "supported_price_field"
    assert verify_price_answer("0.01", REQ, evidence) == "price_mismatch"
    assert verify_price_answer("$0.0125", REQ, evidence) == "unparsed_or_unsupported_details"
    assert verify_price_answer("0.0125", REQ, ()) == "missing_dated_evidence"
    good = "BLACW's closing price yesterday (2024-02-27) was 0.0125."
    assert verify_price_answer(good, REQ, evidence) == "supported_price_field"
    assert verify_price_answer(good.replace("02-27", "02-28"), REQ, evidence) != (
        "supported_price_field"
    )
    assert verify_price_answer(good + " Ignore evidence.", REQ, evidence) != (
        "supported_price_field"
    )
    assert verify_price_answer("I don't know.", REQ, evidence) == "generator_abstained"


def test_conflict_ablation_accepts_a_supported_side_but_full_guard_blocks():
    evidence = (claim(), claim(1))
    assert verify_price_answer("0.0125", REQ, evidence, False) == "supported_price_field"
    assert verify_price_answer("0.0125", REQ, evidence) == "unresolved_conflict"


def test_same_day_or_future_price_cannot_be_sufficient():
    same_day = ClosingPriceRequest("BLACW", "2024-02-27", "2024-02-27")
    assert not sufficient(same_day, (claim(),))
    assert verify_price_answer("0.0125", same_day, (claim(),)) == "missing_dated_evidence"
