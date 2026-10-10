import pytest

from ace_pruningrag.dataset import QueryInput
from ace_pruningrag.historical_prices import prior_close_evidence, prior_close_request


def query(text):
    return QueryInput("q", text, "02/28/2024, 07:53:08 PT", ())


def test_prior_close_resolves_requested_day_not_current_day():
    request = prior_close_request(
        query("What was UBSI's stock price at the close yesterday?"), {"UBSI"}
    )
    assert request.ticker == "UBSI"
    assert request.requested_date == "2024-02-27"
    assert request.available_as_of == "2024-02-28"


@pytest.mark.parametrize(
    "text",
    [
        "What is UBSI's current stock price today?",
        "What was UBSI's highest price yesterday?",
        "Was UBSI's closing price higher than MSFT yesterday?",
        "What was UBSI's closing price last week?",
        "What were UBSI's and MSFT's closing prices yesterday?",
        "What was the closing price yesterday?",
    ],
)
def test_rejects_unsupported_or_ambiguous_requests(text):
    assert prior_close_request(query(text), {"UBSI", "MSFT"}) is None


def test_missing_date_does_not_fall_back_and_evidence_retains_timestamp():
    request = prior_close_request(
        query("What was UBSI's closing price the previous day?"), {"UBSI"}
    )

    class Prices:
        def lookup(self, ticker, date):
            assert ticker == "UBSI" and date == "2024-02-27"
            return self.response

    prices = Prices()
    prices.response = None
    assert prior_close_evidence(request, prices, "hash") is None
    prices.response = {"2024-02-27 00:00:00-05:00": {"Close": 34.25}}
    evidence = prior_close_evidence(request, prices, "hash")
    assert evidence["close"] == 34.25
    assert "2024-02-27 00:00:00-05:00" in evidence["source_ref"]
    prices.response = {"2024-02-28 00:00:00-05:00": {"Close": 35}}
    with pytest.raises(ValueError):
        prior_close_evidence(request, prices, "hash")
