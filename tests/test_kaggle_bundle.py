import base64
import importlib.util
import json
import zlib
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "kaggle_builder", Path(__file__).resolve().parents[1] / "scripts/build_kaggle_kernel.py"
)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def test_bundle_excludes_credentials_and_preserves_private_gpu_metadata(tmp_path):
    root = tmp_path / "repo"
    (root / "src/ace_pruningrag").mkdir(parents=True)
    (root / "configs").mkdir()
    (root / "scripts").mkdir()
    (root / "src/ace_pruningrag/__init__.py").write_text("# first-party fixture\n")
    for name in ("dataset.json", "upstream.json", "retrieval_smoke.json"):
        (root / "configs" / name).write_text("{}")
    (root / "configs/secrets.json").write_text('{"api_key":"unit-secret-sentinel"}')
    (root / ".env").write_text("TOKEN=unit-secret-sentinel")
    (root / "scripts/kaggle_bootstrap.py").write_text('PAYLOAD = "__BUNDLE__"\n')
    output = tmp_path / "bundle"
    metadata = builder.build(root, output, "fixture-owner")
    assert metadata["is_private"] is True
    assert metadata["enable_gpu"] is True
    source = (output / "bootstrap.py").read_text()
    payload = source.split("=", 1)[1].strip().strip("'")
    decoded = zlib.decompress(base64.b64decode(payload)).decode()
    assert "unit-secret-sentinel" not in decoded
    assert len(json.loads(decoded)["files"]) == 4
    with pytest.raises(FileExistsError):
        builder.build(root, output, "fixture-owner")


def test_bundle_rejects_owner_path_injection(tmp_path):
    with pytest.raises(ValueError, match="owner"):
        builder.build(tmp_path, tmp_path / "output", "../another-account")


def test_retrieval_bundle_includes_fresh_process_driver_and_excludes_secrets(tmp_path):
    root = tmp_path / "repo"
    (root / "src/ace_pruningrag").mkdir(parents=True)
    (root / "configs").mkdir()
    (root / "scripts").mkdir()
    (root / "src/ace_pruningrag/__init__.py").write_text("# fixture\n")
    for name in (
        "dataset",
        "upstream",
        "retrieval_smoke",
        "compatibility",
        "crag_finance",
        "learned_smoke",
    ):
        (root / "configs" / f"{name}.json").write_text("{}")
    (root / "configs/secrets.json").write_text('{"key":"unit-secret-sentinel"}')
    (root / "scripts/learned_driver.py").write_text("# fresh-process driver\n")
    (root / "scripts/kaggle_retrieval_pilot.py").write_text('PAYLOAD = "__BUNDLE__"\n')
    out = tmp_path / "bundle"
    metadata = builder.build(root, out, "fixture-owner", "retrieval")
    source = (out / "bootstrap.py").read_text()
    payload = source.split("=", 1)[1].strip().strip("'")
    decoded = zlib.decompress(base64.b64decode(payload)).decode()
    assert "unit-secret-sentinel" not in decoded
    assert "scripts/learned_driver.py" in json.loads(decoded)["files"]
    assert metadata["id"].endswith("retrieval-pilot")
    assert metadata["is_private"] is True


def test_generation_bundle_is_private_and_contains_only_allowed_protocol_files(tmp_path):
    root = tmp_path / "repo"
    for directory in ("src/ace_pruningrag", "configs", "scripts"):
        (root / directory).mkdir(parents=True)
    (root / "src/ace_pruningrag/__init__.py").write_text("# fixture\n")
    for name in ("dataset", "upstream", "retrieval_smoke", "generated_pilot", "crag_prices"):
        (root / "configs" / f"{name}.json").write_text("{}")
    (root / "scripts/generated_driver.py").write_text("# driver\n")
    (root / "scripts/kaggle_generated_pilot.py").write_text('PAYLOAD = "__BUNDLE__"\n')
    (root / "configs/private-review.json").write_text("private-review-sentinel")
    out = tmp_path / "kernel"
    metadata = builder.build(root, out, "fixture-owner", "generation")
    payload = (out / "bootstrap.py").read_text().split("=", 1)[1].strip().strip("'")
    files = json.loads(zlib.decompress(base64.b64decode(payload)))["files"]
    assert "configs/generated_pilot.json" in files and "scripts/generated_driver.py" in files
    assert "private-review-sentinel" not in str(files)
    assert metadata["is_private"] is True
    assert metadata["id"] == "fixture-owner/ace-pruningrag-phase3-generated-pilot"


def test_historical_bundle_keeps_original_protocol_and_selects_new_driver_config(tmp_path):
    root = Path(__file__).resolve().parents[1]
    out = tmp_path / "historical"
    metadata = builder.build(root, out, "fixture-owner", "historical")
    source = (out / "bootstrap.py").read_text()
    assert '"--config", "configs/historical_routing.json"' in source
    import ast

    tree = ast.parse(source)
    payload = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "PAYLOAD" for target in node.targets)
    )
    files = json.loads(zlib.decompress(base64.b64decode(payload)))["files"]
    original = json.loads(files["configs/generated_pilot.json"])
    historical = json.loads(files["configs/historical_routing.json"])
    assert original["limit"] == 50 and historical["limit"] == 6
    assert original["generator"] == historical["generator"]
    assert original["system_prompt"] == historical["system_prompt"]
    assert metadata["id"].endswith("historical-routing-diagnostic") and metadata["is_private"]
