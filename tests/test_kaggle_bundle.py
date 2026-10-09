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
