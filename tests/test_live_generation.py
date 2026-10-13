import ast
import base64
import json
import runpy
import zlib
from pathlib import Path

import pytest

from ace_pruningrag.dataset import validate_record
from ace_pruningrag.live_generation import finish_live, prepare_live

ROOT = Path(__file__).resolve().parents[1]


def test_live_preparation_has_no_gold_or_api_allocation(row):
    config = json.loads((ROOT / "configs/generated_pilot.json").read_text())
    row["answer"] = "SECRET_EVALUATION_LABEL"
    row["query_time"] = "01/01/2024, 00:00:00 PT"
    q = validate_record(row).inference_input()
    prepared = prepare_live(q, config, lambda m: list(range(len(json.dumps(m).split()))))
    assert "SECRET_EVALUATION_LABEL" not in json.dumps(
        {"messages": prepared["messages"], "evidence": prepared["evidence"]}
    )
    assert prepared["source_calls"] == {"web": 1, "finance": 0}
    result = finish_live(q, config, prepared, [42], "Fixture answer", 1, {"fixture": True})
    assert result["actual_llm_calls"] == 1
    assert result["mode"] == "new_gpu_generation"
    assert result["maximum_reserved_tokens"] <= 2048
    assert not result["answer_form_checks"]["claim_support_verified"]
    assert "evaluation" not in result
    with pytest.raises(ValueError, match="token IDs"):
        finish_live(q, config, prepared, [42] * 97, "Too long", 1, {})
    with pytest.raises(ValueError, match="no answer"):
        finish_live(q, config, prepared, [], "", 1, {})


@pytest.mark.parametrize(
    "field,value", [("sampling", True), ("total_tokens", 4096), ("max_new_tokens", 100)]
)
def test_live_worker_cannot_silently_change_protocol(row, field, value):
    config = json.loads((ROOT / "configs/generated_pilot.json").read_text())
    config[field] = value
    with pytest.raises(ValueError, match="live worker"):
        prepare_live(validate_record(row).inference_input(), config, lambda m: [1])


def test_live_bundle_is_private_bounded_and_does_not_include_workspace_artifacts(tmp_path):
    build = runpy.run_path(str(ROOT / "scripts/build_live_kernel.py"))["build"]
    request_id = "a" * 32
    qid = "12345678-1234-1234-1234-123456789abc"
    output = tmp_path / "new-kernel"
    metadata = build(ROOT, output, "fixture-owner", request_id, qid)
    assert metadata["id"] == f"fixture-owner/ace-live-{request_id}"
    assert metadata["is_private"] and metadata["enable_gpu"]
    source = (output / "bootstrap.py").read_text()
    assignment = next(
        n
        for n in ast.parse(source).body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "PAYLOAD" for t in n.targets)
    )
    bundle = json.loads(zlib.decompress(base64.b64decode(ast.literal_eval(assignment.value))))
    assert json.loads(bundle["files"]["configs/live_request.json"]) == {
        "interaction_id": qid,
        "request_id": request_id,
    }
    assert not any(name.startswith(("runs/", "data/", ".cache/")) for name in bundle["files"])
    assert "configs/crag_prices.json" not in bundle["files"]
    assert "scripts/live_driver.py" in source
    compile(source, "live-kernel", "exec")
    with pytest.raises(FileExistsError):
        build(ROOT, output, "fixture-owner", request_id, qid)
    with pytest.raises(ValueError):
        build(ROOT, tmp_path / "other", "owner;bad", request_id, qid)
