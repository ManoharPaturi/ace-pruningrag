"""Read-only original CRAG dated price rows; scalar/container-only pickle loading."""

import io
import math
import re
import sqlite3
from pathlib import Path
from urllib.parse import quote

from .artifacts import sha256_file
from .assets import verify_asset
from .finance_api import ScalarUnpickler


def decode_prices(blob: bytes) -> dict:
    result = ScalarUnpickler(io.BytesIO(blob)).load()
    if not isinstance(result, dict):
        raise ValueError("price history must be a dictionary")
    for date, values in result.items():
        if not isinstance(date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2} .+", date):
            raise ValueError("dated price key required")
        if not isinstance(values, dict) or not {"Open", "Close"} <= set(values):
            raise ValueError("OHLC price fields missing")
        if any(
            not isinstance(k, str) or type(v) not in (int, float) or not math.isfinite(v)
            for k, v in values.items()
        ):
            raise ValueError("price fields must contain finite numeric scalars")
    return result


class DailyPrices:
    def __init__(self, config: dict, root: Path):
        self.path = verify_asset(config["assets"][0], root)

    def lookup(self, ticker: str, date: str | None = None) -> dict | None:
        with sqlite3.connect(f"file:{quote(str(self.path.resolve()))}?mode=ro", uri=True) as db:
            row = db.execute('SELECT value FROM "unnamed" WHERE key = ?', (ticker,)).fetchone()
        if not row:
            return None
        data = decode_prices(row[0])
        if date is None:
            return data
        return {key: value for key, value in data.items() if key[:10] == date} or None

    def audit(self) -> dict:
        probes = {}
        for ticker in ("AAPL", "MSFT", "TSLA"):
            rows = self.lookup(ticker) or {}
            dates = sorted(rows)
            probes[ticker] = {
                "rows": len(rows),
                "first_date": dates[0][:10] if dates else None,
                "last_date": dates[-1][:10] if dates else None,
                "march_5_2024_available": self.lookup(ticker, "2024-03-05") is not None,
            }
        return {
            "status": "dated_price_probes_verified",
            "probes": probes,
            "scope": "Three ticker probes, not a proof of every ticker/date in the snapshot.",
            "asset_sha256": sha256_file(self.path),
        }
