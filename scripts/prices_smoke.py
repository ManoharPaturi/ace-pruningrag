"""Verify original daily-price assets and actual dated row lookups."""

import argparse
import json
from pathlib import Path

from ace_pruningrag.artifacts import read_json, write_json
from ace_pruningrag.assets import fetch_assets
from ace_pruningrag.daily_prices import DailyPrices

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path.cwd()
    config = read_json(root / "configs/crag_prices.json")
    fetch_assets(config, root)
    prices = DailyPrices(config, root)
    result = prices.audit()
    for ticker, probe in result["probes"].items():
        assert probe["rows"] == 252 and probe["last_date"] == "2024-02-28"
        assert prices.lookup(ticker, "2024-02-28")
        assert prices.lookup(ticker, "2024-03-05") is None
    assert prices.lookup("NONEXISTENT_FIXTURE_TICKER") is None
    write_json(args.output, result)
    print(json.dumps(result, indent=2))
