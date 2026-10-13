import ast
import base64
import copy
import json
import runpy
import zlib
from pathlib import Path

import pytest

from ace_pruningrag.artifacts import read_json
from ace_pruningrag.unicode_protocol import validate_protocol

ROOT = Path(__file__).resolve().parents[1]


def test_unicode_protocol_rejects_identity_budget_and_policy_drift():
    config = read_json(ROOT / "configs/unicode_extraction.json")
    validate_protocol(ROOT, config)
    for key, value in (
        ("protocol_id", "frozen_v1"),
        ("span_policy_module", "ace_pruningrag.constrained_claims"),
        ("span_policy_sha256", "0" * 64),
        ("max_output_tokens", 161),
        ("allow_answer_acceptance", True),
    ):
        changed = copy.deepcopy(config)
        changed[key] = value
        with pytest.raises(ValueError, match="Unicode protocol"):
            validate_protocol(ROOT, changed)


def test_unicode_bundle_uses_corrected_policy_without_answer_labels(tmp_path):
    trace = tmp_path / "trace.jsonl"
    row = {
        "interaction_id": "q",
        "policy": "test",
        "query": "Who won?",
        "query_time": "2024",
        "prediction": "PRIVATE ANSWER",
        "gold": "PRIVATE LABEL",
        "selected": [{"evidence_id": "s", "content": "Victoria Mone\u0301t won."}],
    }
    trace.write_text(json.dumps(row) + "\n")
    build = runpy.run_path(str(ROOT / "scripts/build_unicode_kernel.py"))["build"]
    output = tmp_path / "bundle"
    metadata = build(ROOT, trace, output, "test-owner")
    tree = ast.parse((output / "bootstrap.py").read_text())
    assignment = next(
        n
        for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "PAYLOAD" for t in n.targets)
    )
    payload = json.loads(zlib.decompress(base64.b64decode(ast.literal_eval(assignment.value))))
    tasks = payload["files"]["configs/constrained_tasks.json"]
    assert "PRIVATE" not in tasks
    assert len(json.loads(tasks)["tasks"]) == 2
    driver = payload["files"]["scripts/unicode_extraction_driver.py"]
    assert "from ace_pruningrag.unicode_claims import" in driver
    assert "validate_protocol(args.root, config)" in driver
    assert "from ace_pruningrag.constrained_claims import" not in driver
    assert metadata["is_private"] and metadata["enable_gpu"]
    assert metadata["id"].startswith("test-owner/ace-unicode-")
    assert read_json(output / "task-manifest.json")["protocol_id"] == "unicode_combining_marks_v2"
    with pytest.raises(FileExistsError):
        build(ROOT, trace, output, "test-owner")
