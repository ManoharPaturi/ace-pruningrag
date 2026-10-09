"""Synthetic unit fixtures only; research runs always use the real pinned dataset."""

import pytest


@pytest.fixture
def row():
    return {
        "interaction_id": "fixture-1",
        "query": "Which year was the device built?",
        "query_time": "2024-01-01",
        "domain": "open",
        "question_type": "simple",
        "static_or_dynamic": "static",
        "answer": "2020",
        "alt_ans": [2020, "2020"],
        "split": 0,
        "search_results": [
            {
                "page_name": "Device",
                "page_url": "https://example.test/device",
                "page_snippet": "Built in 2020.",
                "page_result": "The device was built in 2020.",
                "page_last_modified": "2024-01-01",
            }
        ],
    }
