import csv
import json
import pickle
import sqlite3
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from ace_pruningrag.artifacts import sha256_file
from ace_pruningrag.assets import fetch_assets
from ace_pruningrag.finance_api import FinanceSnapshot, decode_market_cap, handler_for


@pytest.fixture
def finance_config(tmp_path):
    database = tmp_path / "marketcap.sqlite"
    with sqlite3.connect(database) as db:
        db.execute('CREATE TABLE "unnamed" (key TEXT PRIMARY KEY, value BLOB)')
        db.execute('INSERT INTO "unnamed" VALUES (?, ?)', ("TEST", pickle.dumps(42.0)))
    names = tmp_path / "companies.csv"
    with names.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Name", "Symbol"])
        writer.writerow(["Fixture Company", "TEST"])
    return {
        "revision": "unit-fixture",
        "scope": "unit-fixture",
        "max_total_bytes": 100000,
        "db_path": "marketcap.sqlite",
        "company_path": "companies.csv",
        "assets": [
            {"local_path": p.name, "bytes": p.stat().st_size, "sha256": sha256_file(p)}
            for p in (database, names)
        ],
    }


def test_snapshot_integrity_readonly_and_missing_ticker(finance_config, tmp_path):
    snapshot = FinanceSnapshot(finance_config, tmp_path)
    assert snapshot.lookup("/finance/get_ticker_by_name", "Fixture Company") == "TEST"
    assert snapshot.lookup("/finance/get_market_capitalization", "TEST") == 42
    assert snapshot.lookup("/finance/get_market_capitalization", "missing") is None
    with snapshot.connection() as db, pytest.raises(sqlite3.OperationalError, match="readonly"):
        db.execute('DELETE FROM "unnamed"')
    (tmp_path / "companies.csv").write_text("modified")
    with pytest.raises(ValueError, match="integrity"):
        FinanceSnapshot(finance_config, tmp_path)


def test_snapshot_decoder_rejects_global_objects_and_nonfinite():
    with pytest.raises(ValueError, match="global"):
        decode_market_cap(pickle.dumps(Exception("never instantiated")))
    with pytest.raises(ValueError, match="finite"):
        decode_market_cap(pickle.dumps(float("nan")))


def test_asset_budget_and_destination_guards(finance_config, tmp_path):
    assert fetch_assets(finance_config, tmp_path)["assets"] == 2
    finance_config["max_total_bytes"] = 1
    with pytest.raises(ValueError, match="budget"):
        fetch_assets(finance_config, tmp_path)
    finance_config["max_total_bytes"] = 100000
    finance_config["assets"][0]["local_path"] = "../outside.sqlite"
    with pytest.raises(ValueError, match="escapes"):
        fetch_assets(finance_config, tmp_path)


def test_http_wire_format_and_invalid_requests(finance_config, tmp_path):
    snapshot = FinanceSnapshot(finance_config, tmp_path)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_for(snapshot))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def request(path, payload):
        return urllib.request.Request(
            f"http://127.0.0.1:{server.server_port}{path}",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )

    try:
        with urllib.request.urlopen(
            request("/finance/get_market_capitalization", {"query": "TEST"})
        ) as r:
            assert json.load(r) == {"result": 42.0}
        for path, payload, status in [
            ("/finance/get_market_capitalization", {"query": 123}, 400),
            ("/movie/get_movie_info", {"query": "test"}, 404),
        ]:
            with pytest.raises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(request(path, payload))
            assert error.value.code == status
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
