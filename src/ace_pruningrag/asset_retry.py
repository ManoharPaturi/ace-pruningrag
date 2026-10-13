"""Bounded retries of pre-body HTTP rate limits; immutable asset checks stay intact."""

import time
from urllib.error import HTTPError

from .assets import fetch_assets


def fetch_assets_with_retry(config, root):
    for attempt, delay in enumerate((5, 15, 30, None)):
        try:
            return fetch_assets(config, root)
        except HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or delay is None:
                raise
            # HTTPError precedes opening the destination. Existing partial files,
            # size/hash errors and interruptions are not caught or discarded here.
            retry_after = error.headers.get("Retry-After", "") if error.headers else ""
            if retry_after.isdecimal():
                if int(retry_after) > 30:
                    raise  # Do not retry before a longer server-requested cooldown.
                delay = max(delay, int(retry_after))
            print(f"Asset HTTP {error.code}; retry {attempt + 1}/3 after {delay}s", flush=True)
            time.sleep(delay)
