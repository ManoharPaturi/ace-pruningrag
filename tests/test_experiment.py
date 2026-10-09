import json

import pytest

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.experiment import retrieval_smoke


def test_smoke_cli_contract_and_artifact_provenance(row, tmp_path):
    # Small fixture checks plumbing only; it is not a research measurement.
    dataset = tmp_path / "data.jsonl"
    dataset.write_text(json.dumps(row) + "\n")
    write_json(
        tmp_path / "dataset.json",
        {
            "path": "data.jsonl",
            "bytes": dataset.stat().st_size,
            "sha256": sha256_file(dataset),
        },
    )
    config = tmp_path / "smoke.json"
    write_json(
        config,
        {
            "experiment_id": "unit-fixture",
            "dataset_config": "dataset.json",
            "limit": 1,
            "scope": "web_only_offline_retrieval_no_generation_no_judge",
            "chunk_words": 2,
            "bm25_k1": 1.5,
            "bm25_b": 0.75,
            "top_k": 3,
            "max_context_words": 4,
            "seed": 42,
        },
    )
    output = tmp_path / "output"
    result = retrieval_smoke(config, tmp_path, output)
    assert result["queries"] == 1
    assert result["maximum_context_words"] <= 4
    assert result["answer_accuracy"] is None
    trace = read_json(output / "retrieval_traces.jsonl")
    assert trace["prediction"] is None
    assert "answer" not in trace and "alt_ans" not in trace
    manifest = read_json(output / "manifest.json")
    assert manifest["trace_sha256"] == sha256_file(output / "retrieval_traces.jsonl")
    with pytest.raises(FileExistsError):
        retrieval_smoke(config, tmp_path, output)
