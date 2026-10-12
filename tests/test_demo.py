import json

import pytest

from ace_pruningrag.artifacts import sha256_file, write_json
from ace_pruningrag.demo import DemoStore, create_app


def fixture_root(tmp_path, row):
    (tmp_path / "configs").mkdir()
    data = tmp_path / "dataset.jsonl"
    data.write_text(json.dumps(row) + "\n")
    write_json(
        tmp_path / "configs/dataset.json",
        {
            "path": data.name,
            "bytes": data.stat().st_size,
            "sha256": sha256_file(data),
        },
    )
    trace = tmp_path / "trace.jsonl"
    trace.write_text(
        json.dumps(
            {
                "interaction_id": row["interaction_id"],
                "policy": "fixed_web",
                "query": row["query"],
                "query_time": row["query_time"],
                "prediction": "Recorded output",
                "prompt_sha256": "prompt",
                "input_tokens": 10,
                "output_tokens": 2,
                "selected": [],
                "gold_answer": "MUST NOT LEAK",
            }
        )
        + "\n"
    )
    write_json(
        tmp_path / "configs/demo.json",
        {
            "runs": {
                "fixture": {
                    "path": trace.name,
                    "sha256": sha256_file(trace),
                    "responses": 1,
                }
            }
        },
    )
    return trace


def test_tampered_admitted_trace_rejected(tmp_path, row):
    trace = fixture_root(tmp_path, row)
    trace.write_text(trace.read_text().replace("Recorded output", "Changed output"))
    with pytest.raises(ValueError, match="hash differs"):
        DemoStore(tmp_path)


def test_missing_artifact_is_visible_without_fabricated_answers(tmp_path, row):
    fixture_root(tmp_path, row).unlink()
    assert DemoStore(tmp_path).catalog() == [
        {"name": "fixture", "status": "missing_artifact", "questions": []}
    ]


def test_api_replay_and_retrieval_do_not_leak_gold(tmp_path, row):
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    fixture_root(tmp_path, row)
    with TestClient(create_app(tmp_path)) as client:
        assert client.get("/health").status_code == 200
        answer = client.get(f"/answers/fixture/{row['interaction_id']}/fixed_web")
        assert answer.status_code == 200
        assert answer.json()["mode"] == "recorded_answer"
        assert answer.json()["actual_new_llm_calls"] == 0
        assert "MUST NOT LEAK" not in answer.text
        assert "gold_answer" not in answer.text
        retrieval = client.get(f"/retrieve/{row['interaction_id']}").json()
        assert retrieval["used_words"] <= retrieval["max_words"]
        assert retrieval["mode"] == "fresh_retrieval"
        assert client.get("/answers/fixture/unknown/fixed_web").status_code == 404
        assert client.get("/retrieve/unknown").status_code == 404
