"""Bounded prior-calendar-day closing-price requests with no same-day look-ahead."""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from .daily_prices import DailyPrices
from .dataset import QueryInput


@dataclass(frozen=True)
class ClosingPriceRequest:
    ticker: str
    requested_date: str
    available_as_of: str


def prior_close_request(query: QueryInput, inventory: set[str]) -> ClosingPriceRequest | None:
    """Accept explicit possessive tickers and an unambiguous previous-day close intent."""
    text = query.query.casefold()
    if not re.search(r"\bprice\b", text):
        return None
    if not re.search(r"\b(?:yesterday|previous day)\b", text):
        return None
    if not re.search(r"\b(?:close|closing)\b", text):
        return None
    # Multi-company/range questions need a separate adapter, not silent simplification.
    if re.search(
        r"\b(?:and|or|than|versus|compared|compare|higher|lower|week|month|ratio)\b", text
    ):
        return None
    possessives = set(re.findall(r"\b([A-Za-z][A-Za-z0-9]{2,5})['’]s\b", text))
    symbols = {ticker.upper() for ticker in possessives} & inventory
    if len(symbols) != 1:
        return None
    moment = datetime.strptime(query.query_time, "%m/%d/%Y, %H:%M:%S PT")
    return ClosingPriceRequest(
        next(iter(symbols)),
        (moment.date() - timedelta(days=1)).isoformat(),
        moment.date().isoformat(),
    )


def prior_close_evidence(
    request: ClosingPriceRequest, prices: DailyPrices, snapshot_sha256: str
) -> dict | None:
    response = prices.lookup(request.ticker, request.requested_date)
    if not response:
        return None
    if len(response) != 1:
        raise ValueError("ambiguous daily rows for requested date")
    timestamp, row = next(iter(response.items()))
    if (
        timestamp[:10] != request.requested_date
        or request.requested_date >= request.available_as_of
    ):
        raise ValueError("requested close must precede the availability date")
    return {
        "content": f"{request.ticker} closing price on {request.requested_date}: {row['Close']}",
        "source_ref": f"crag:{snapshot_sha256}/finance_price/{request.ticker}/{timestamp}",
        "ticker": request.ticker,
        "requested_date": request.requested_date,
        "row_timestamp": timestamp,
        "available_as_of": request.available_as_of,
        "close": row["Close"],
        "snapshot_sha256": snapshot_sha256,
        "limitations": "Currency and adjustment basis are not established by this row.",
    }
