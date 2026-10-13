import ast
import base64
import json
import runpy
import shutil
import zlib
from pathlib import Path

import pytest

from ace_pruningrag.artifacts import read_json, sha256_file
from ace_pruningrag.requirements_3b_protocol import validate_protocol

ROOT = Path(__file__).resolve().parents[1]


def test_model_variant_preserves_control_decoding_and_rejects_asset_budget_drift(tmp_path):
    config = read_json(ROOT / "configs/query_requirements_3b.json")
    validate_protocol(ROOT, config)
    decoding = read_json(ROOT / config["decoding_config"])
    assert decoding["repetition_penalty"] == 1.1
    original = read_json(ROOT / "configs/generated_pilot.json")
    original_defaults = next(
        a for a in original["assets"] if a["local_path"].endswith("generation_config.json")
    )
    assert sha256_file(ROOT / config["decoding_config"]) == original_defaults["sha256"]
    for key, value in (
        ("generator_config", "configs/generated_pilot.json"),
        ("generator_config_sha256", "0" * 64),
        ("decoding_config_sha256", "0" * 64),
        ("max_input_and_output_tokens", 4097),
        ("max_output_tokens", 2049),
        ("batch_size", 1),
        ("dtype", "float16"),
        ("allow_answer_acceptance", True),
    ):
        with pytest.raises(ValueError, match="3B"):
            validate_protocol(ROOT, {**config, key: value})
    shutil.copytree(ROOT / "configs", tmp_path / "configs")
    (tmp_path / "src/ace_pruningrag").mkdir(parents=True)
    shutil.copyfile(
        ROOT / "src/ace_pruningrag/query_requirements.py",
        tmp_path / "src/ace_pruningrag/query_requirements.py",
    )
    manifest = tmp_path / config["generator_config"]
    manifest.write_text(manifest.read_text() + " ")
    with pytest.raises(ValueError, match="3B"):
        validate_protocol(tmp_path, config)


def test_model_variant_bundle_excludes_labels_sources_and_loads_frozen_decoding(tmp_path):
    trace = tmp_path / "trace.jsonl"
    trace.write_text(
        json.dumps(
            {
                "interaction_id": "q",
                "policy": "test",
                "query": "Who won 14 awards?",
                "query_time": "2024",
                "prediction": "PRIVATE ANSWER",
                "gold": "PRIVATE LABEL",
                "selected": [{"evidence_id": "s", "content": "PRIVATE SOURCE"}],
            }
        )
        + "\n"
    )
    build = runpy.run_path(str(ROOT / "scripts/build_requirements_3b_kernel.py"))["build"]
    output = tmp_path / "bundle"
    metadata = build(ROOT, trace, output, "test-owner")
    code = (output / "bootstrap.py").read_text()
    tree = ast.parse(code)
    assignment = next(
        n
        for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "PAYLOAD" for t in n.targets)
    )
    payload = json.loads(zlib.decompress(base64.b64decode(ast.literal_eval(assignment.value))))
    tasks = payload["files"]["configs/constrained_tasks.json"]
    assert "PRIVATE" not in tasks and len(json.loads(tasks)["tasks"]) == 1
    assert 'fetch_assets(read_json(root / "configs/requirements_extractor_3b.json"), root)' in code
    driver = payload["files"]["scripts/requirements_3b_driver.py"]
    assert "model.generation_config = GenerationConfig.from_dict" in driver
    assert 'read_json(args.root / config["decoding_config"])' in driver
    assert '"decoding_defaults_sha256"' in driver
    assert metadata["is_private"] and metadata["enable_gpu"]
    assert metadata["title"].lower().replace(" ", "-") == metadata["id"].split("/")[1]
    assert len(metadata["title"]) <= 45  # Keep names below the observed rejected 51-char form.
    assert read_json(output / "task-manifest.json")["new_answer_generation_calls"] == 0
