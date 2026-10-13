from email.message import Message
from urllib.error import HTTPError

import pytest

from ace_pruningrag import asset_retry


def test_rate_limit_retry_preserves_config_and_bounds_server_delay(monkeypatch, tmp_path):
    calls, sleeps = [], []
    config = {"assets": [{"sha256": "pinned", "bytes": 4}]}
    headers = Message()
    headers["Retry-After"] = "20"

    def fetch(received, root):
        assert received is config and root == tmp_path
        calls.append(1)
        if len(calls) < 3:
            raise HTTPError("https://example.invalid/asset", 429, "rate limit", headers, None)
        return {"status": "assets_verified"}

    monkeypatch.setattr(asset_retry, "fetch_assets", fetch)
    monkeypatch.setattr(asset_retry.time, "sleep", sleeps.append)
    assert asset_retry.fetch_assets_with_retry(config, tmp_path)["status"] == "assets_verified"
    assert len(calls) == 3 and sleeps == [20, 20]


def test_long_server_cooldown_stops_instead_of_retrying_early(monkeypatch, tmp_path):
    sleeps = []
    headers = Message()
    headers["Retry-After"] = "600"

    def fetch(*args):
        raise HTTPError("https://example.invalid/asset", 429, "cooldown", headers, None)

    monkeypatch.setattr(asset_retry, "fetch_assets", fetch)
    monkeypatch.setattr(asset_retry.time, "sleep", sleeps.append)
    with pytest.raises(HTTPError):
        asset_retry.fetch_assets_with_retry({}, tmp_path)
    assert sleeps == []


@pytest.mark.parametrize("error", [ValueError("checksum mismatch"), ValueError("existing partial")])
def test_integrity_and_partial_failures_stop_without_retry(monkeypatch, tmp_path, error):
    sleeps = []

    def fetch(*args):
        raise error

    monkeypatch.setattr(asset_retry, "fetch_assets", fetch)
    monkeypatch.setattr(asset_retry.time, "sleep", sleeps.append)
    with pytest.raises(ValueError, match=str(error)):
        asset_retry.fetch_assets_with_retry({}, tmp_path)
    assert sleeps == []


@pytest.mark.parametrize(
    "code,attempts", [(429, 4), (500, 4), (502, 4), (503, 4), (504, 4), (404, 1)]
)
def test_retry_exhaustion_and_permanent_http_failure(monkeypatch, tmp_path, code, attempts):
    calls, sleeps = [], []

    def fetch(*args):
        calls.append(1)
        raise HTTPError("https://example.invalid/asset", code, "error", None, None)

    monkeypatch.setattr(asset_retry, "fetch_assets", fetch)
    monkeypatch.setattr(asset_retry.time, "sleep", sleeps.append)
    with pytest.raises(HTTPError):
        asset_retry.fetch_assets_with_retry({}, tmp_path)
    assert len(calls) == attempts and len(sleeps) == attempts - 1
