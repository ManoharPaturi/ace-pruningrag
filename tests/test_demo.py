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
        assert not answer.json()["answer_form_checks"]["factual_correctness_verified"]
        assert answer.json()["prediction"] == "Recorded output"
        assert "MUST NOT LEAK" not in answer.text
        assert "gold_answer" not in answer.text
        retrieval = client.get(f"/retrieve/{row['interaction_id']}").json()
        assert retrieval["used_words"] <= retrieval["max_words"]
        assert retrieval["mode"] == "fresh_retrieval"
        assert client.get("/answers/fixture/unknown/fixed_web").status_code == 404
        assert client.get("/retrieve/unknown").status_code == 404
        assert client.get("/live").json()["enabled"] is False
        assert (
            client.post(
                f"/live/generate/{row['interaction_id']}", headers={"Idempotency-Key": "a" * 32}
            ).status_code
            == 503
        )


def test_live_http_recovery_identity_and_unknown_question(tmp_path, row):
    from fastapi.testclient import TestClient

    fixture_root(tmp_path, row)
    write_json(tmp_path / "configs/live_service.json", {"owner": "fixture", "max_jobs": 1})

    class Provider:
        def build(self, job, directory):
            directory.mkdir()
            return "fixture/" + job["id"]

        def submit(self, directory):
            pass

        def status(self, kernel):
            return "complete"

        def collect(self, kernel, bundle, directory):
            return {"prediction": "Fixture only"}

    with TestClient(create_app(tmp_path, live_provider=Provider(), live_enabled=True)) as client:
        headers = {"Idempotency-Key": "a" * 32}
        assert client.get("/live").json()["enabled"] is True
        assert client.post("/live/generate/unknown", headers=headers).status_code == 404
        job = client.post(f"/live/generate/{row['interaction_id']}", headers=headers).json()
        repeated = client.post(f"/live/generate/{row['interaction_id']}", headers=headers).json()
        assert repeated["id"] == job["id"]
        assert client.get(f"/live/jobs/{job['id']}").status_code == 200
        assert client.get("/live/jobs/unknown").status_code == 404
