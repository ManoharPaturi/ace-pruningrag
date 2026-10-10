"""Date-compatible source provisioning for the frozen historical diagnostic."""

import sqlite3
from urllib.parse import quote

from .historical_prices import prior_close_evidence, prior_close_request
from .routing import Capability


def historical_source(query, prices, snapshot_sha256):
    with sqlite3.connect(f"file:{quote(str(prices.path.resolve()))}?mode=ro", uri=True) as db:
        inventory = {row[0] for row in db.execute('SELECT key FROM "unnamed"')}
    request = prior_close_request(query, inventory)
    if request is None or prior_close_evidence(request, prices, snapshot_sha256) is None:
        raise ValueError("frozen historical question lacks validated prior-day evidence")
    capabilities = (
        Capability("web", True, False, None),
        Capability("finance_prices", True, True, request.available_as_of),
    )

    def fetch():
        evidence = prior_close_evidence(request, prices, snapshot_sha256)
        if evidence is None:
            raise ValueError("frozen historical price disappeared")
        return evidence

    return capabilities, fetch
