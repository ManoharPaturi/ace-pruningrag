"""Gold-free audit of the existing executor and explicit-ticker expansion candidates."""

import re
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from .artifacts import sha256_file
from .daily_prices import DailyPrices
from .dataset import QueryInput, iter_records, verify_dataset
from .routing import source_hints


def current_symbols(query: QueryInput) -> set[str]:
    aliases = {"apple": "AAPL", "microsoft": "MSFT", "tesla": "TSLA"}
    return {
        ticker
        for name, ticker in (*aliases.items(), *((t, t) for t in aliases.values()))
        if re.search(r"\b" + name + r"\b", query.query, re.I)
    }


def expansion_symbols(query: QueryInput, inventory: set[str]) -> set[str]:
    """Candidates only: exact ticker words of >=3 characters on price-hinted queries."""
    if "finance_prices" not in source_hints(query.query):
        return set()
    words = set(re.findall(r"\b[A-Za-z][A-Za-z0-9]{2,}\b", query.query.upper()))
    return words & inventory


def audit_price_eligibility(dataset_config: dict, price_config: dict, root: Path) -> dict:
    data = verify_dataset(dataset_config, root)
    prices = DailyPrices(price_config, root)
    with sqlite3.connect(f"file:{quote(str(prices.path.resolve()))}?mode=ro", uri=True) as db:
        inventory = {row[0] for row in db.execute('SELECT key FROM "unnamed"')}
    histories = {}

    def available(symbol, date):
        if symbol not in histories:
            histories[symbol] = prices.lookup(symbol) or {}
        return any(key[:10] == date for key in histories[symbol])

    counts = Counter()
    existing_eligible = []
    expansion = []
    for record in iter_records(data):
        query = record.inference_input()
        counts["questions"] += 1
        date = datetime.strptime(query.query_time, "%m/%d/%Y, %H:%M:%S PT").date().isoformat()
        hinted = "finance_prices" in source_hints(query.query)
        counts["price_hinted_questions"] += hinted
        symbols = current_symbols(query)
        if len(symbols) == 1:
            counts["current_single_entity_questions"] += 1
            symbol = next(iter(symbols))
            if available(symbol, date):
                counts["current_date_eligible"] += 1
                counts["current_date_eligible_and_price_hinted"] += hinted
                existing_eligible.append(
                    {
                        "interaction_id": query.interaction_id,
                        "ticker": symbol,
                        "date": date,
                        "price_hinted": hinted,
                    }
                )
        candidates = expansion_symbols(query, inventory)
        if len(candidates) == 1:
            symbol = next(iter(candidates))
            if available(symbol, date):
                expansion.append(
                    {
                        "interaction_id": query.interaction_id,
                        "ticker_candidate": symbol,
                        "date": date,
                        "query": query.query,
                    }
                )
    return {
        "status": "full_dataset_price_eligibility_audited",
        "dataset_sha256": sha256_file(data),
        "prices_sha256": sha256_file(prices.path),
        "counts": dict(counts),
        "current_date_eligible_queries": existing_eligible,
        "explicit_ticker_expansion_candidates": expansion,
        "expansion_candidate_count": len(expansion),
        "cached_history_reads": len(histories),
        "current_executor_relevant_comparison_ready": counts[
            "current_date_eligible_and_price_hinted"
        ]
        > 0,
        "expansion_ready_for_generation": False,
        "limitations": [
            "Keyword relevance and ticker candidates are not human evidence-necessity labels.",
            "Same-date availability does not prove the requested historical range is covered.",
            "A completed daily OHLC row can leak later prices into an intraday question.",
            "Expansion candidates require entity and requested-time validation before generation.",
        ],
    }
