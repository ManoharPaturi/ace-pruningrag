import ast
import base64
import json
import runpy
import zlib
from pathlib import Path

import pytest

from ace_pruningrag.artifacts import read_json
from ace_pruningrag.requirements_protocol import validate_protocol

ROOT = Path(__file__).resolve().parents[1]


def test_requirements_protocol_rejects_prompt_hash_and_budget_drift():
    config = read_json(ROOT / "configs/query_requirements.json")
    validate_protocol(ROOT, config)
    for key, value in (
        ("protocol_id", "unicode_combining_marks_v2"),
        ("span_policy_module", "ace_pruningrag.unicode_claims"),
        ("span_policy_sha256", "0" * 64),
        ("max_clauses", 13),
        ("max_output_tokens", 2049),
        ("max_input_and_output_tokens", 4097),
        ("allow_answer_acceptance", True),
    ):
        with pytest.raises(ValueError, match="requirements"):
            validate_protocol(ROOT, {**config, key: value})


def test_inventory_bundle_is_blinded_and_uses_plural_decoder(tmp_path):
    trace = tmp_path / "trace.jsonl"
    trace.write_text(
        json.dumps(
            {
                "interaction_id": "q",
                "policy": "test",
                "query": "Compare A and B wins.",
                "query_time": "2024",
                "prediction": "PRIVATE ANSWER",
                "gold": "PRIVATE LABEL",
                "selected": [{"evidence_id": "s", "content": "A won. B lost."}],
            }
        )
        + "\n"
    )
    build = runpy.run_path(str(ROOT / "scripts/build_requirements_kernel.py"))["build"]
    output = tmp_path / "bundle"
    metadata = build(ROOT, trace, output, "test-owner")
    tree = ast.parse((output / "bootstrap.py").read_text())
    assignment = next(
        n
        for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "PAYLOAD" for t in n.targets)
    )
    bundle = json.loads(zlib.decompress(base64.b64decode(ast.literal_eval(assignment.value))))
    assert "PRIVATE" not in bundle["files"]["configs/constrained_tasks.json"]
    tasks = json.loads(bundle["files"]["configs/constrained_tasks.json"])["tasks"]
    assert len(tasks) == 1 and tasks[0]["kind"] == "query"
    assert "A won. B lost." not in bundle["files"]["configs/constrained_tasks.json"]
    driver = bundle["files"]["scripts/requirements_extraction_driver.py"]
    assert "from ace_pruningrag.query_requirements import" in driver
    assert "messages as extraction_messages" in driver
    assert "max_new_tokens=2048" in driver
    assert metadata["is_private"] and metadata["enable_gpu"]
    manifest = read_json(output / "task-manifest.json")
    assert manifest["protocol_id"] == "query_requirements_v1"
    assert manifest["max_total_reserved_tokens"] == 4096
    assert manifest["new_answer_generation_calls"] == 0
    with pytest.raises(FileExistsError):
        build(ROOT, trace, output, "test-owner")
