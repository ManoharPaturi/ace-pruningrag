"""Read-only CRAG finance snapshot slice with the original two endpoint wire formats."""

import csv
import io
import json
import math
import pickle
import sqlite3
import threading
import urllib.request
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .artifacts import sha256_file
from .assets import verify_asset


class ScalarUnpickler(pickle.Unpickler):
    def find_class(self, module: str, name: str):
        raise ValueError("snapshot market-cap values must not load global objects")


def decode_market_cap(blob: bytes) -> float | int:
    value = ScalarUnpickler(io.BytesIO(blob)).load()
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("market-cap snapshot value is not a finite number")
    return value


class FinanceSnapshot:
    def __init__(self, config: dict[str, Any], root: Path):
        for asset in config["assets"]:
            verify_asset(asset, root)
        self.config = config
        self.database = root / config["db_path"]
        with (root / config["company_path"]).open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            self.names = {row["Name"]: row["Symbol"] for row in reader}
        with self.connection() as db:
            self.market_cap_rows = db.execute('SELECT count(*) FROM "unnamed"').fetchone()[0]
            # Validate the entire narrow snapshot, not just successful probe tickers.
            for (blob,) in db.execute('SELECT value FROM "unnamed"'):
                decode_market_cap(blob)

    @contextmanager
    def connection(self):
        uri = f"file:{quote(str(self.database.resolve()))}?mode=ro"
        db = sqlite3.connect(uri, uri=True)
        try:
            yield db
        finally:
            db.close()

    def lookup(self, endpoint: str, query: str):
        if endpoint == "/finance/get_ticker_by_name":
            return self.names.get(query)
        if endpoint == "/finance/get_market_capitalization":
            with self.connection() as db:
                row = db.execute('SELECT value FROM "unnamed" WHERE key = ?', (query,)).fetchone()
            return decode_market_cap(row[0]) if row else None
        raise KeyError(endpoint)


def handler_for(snapshot: FinanceSnapshot) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def respond(self, status: int, value: Any):
            content = json.dumps(value, allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def do_POST(self):
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16384:
                    raise ValueError("invalid request size")
                value = json.loads(self.rfile.read(length))
                if not isinstance(value, dict) or not isinstance(value.get("query"), str):
                    raise ValueError("query must be a string")
                result = snapshot.lookup(self.path, value["query"])
            except KeyError:
                self.respond(404, {"error": "endpoint outside restored finance slice"})
            except (ValueError, json.JSONDecodeError) as exc:
                self.respond(400, {"error": str(exc)})
            else:
                self.respond(200, {"result": result})

    return Handler


def finance_smoke(config: dict[str, Any], root: Path) -> dict[str, Any]:
    snapshot = FinanceSnapshot(config, root)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(snapshot))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    probes = []
    try:
        for probe in config["probe_queries"]:
            payload = json.dumps({"query": probe["query"]}).encode()
            request = urllib.request.Request(
                f"http://127.0.0.1:{server.server_port}{probe['endpoint']}",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                value = json.load(response)
            if value != {"result": snapshot.lookup(probe["endpoint"], probe["query"])}:
                raise ValueError("HTTP response differs from verified snapshot lookup")
            if probe.get("expected") is not None and value["result"] != probe["expected"]:
                raise ValueError("known probe result does not match")
            if probe.get("expect_missing") and value["result"] is not None:
                raise ValueError("unknown-ticker probe should return null")
            probes.append(dict(probe, response=value))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    return {
        "status": "finance_slice_verified",
        "revision": config["revision"],
        "market_cap_rows": snapshot.market_cap_rows,
        "company_names": len(snapshot.names),
        "probes": probes,
        "assets": [
            dict(a, verified_sha256=sha256_file(root / a["local_path"])) for a in config["assets"]
        ],
        "limitations": [
            "Only exact company-to-ticker and market-cap endpoints are restored.",
            "Snapshot values are historical benchmark data, not live financial data.",
            "Fuzzy matching and the remaining domain endpoints are not served.",
            "This independent adapter is not the complete original CRAG API server.",
            "HTTP smoke probes are not generated answers or a benchmark accuracy evaluation.",
        ],
    }
