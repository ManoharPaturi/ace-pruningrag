import ast
import base64
import json
import runpy
import zlib
from pathlib import Path

from ace_pruningrag.artifacts import read_json

ROOT = Path(__file__).resolve().parents[1]


def test_query_graph_bundle_excludes_labels_sources_and_loads_frozen_decoding(tmp_path):
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
    build = runpy.run_path(str(ROOT / "scripts/build_query_graph_kernel.py"))["build"]
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
    driver = payload["files"]["scripts/query_graph_driver.py"]
    assert "model.generation_config = GenerationConfig.from_dict" in driver
    assert 'read_json(args.root / config["decoding_config"])' in driver
    assert '"decoding_defaults_sha256"' in driver
    assert metadata["is_private"] and metadata["enable_gpu"]
    assert metadata["title"].lower().replace(" ", "-") == metadata["id"].split("/")[1]
    assert len(metadata["title"]) <= 45  # Keep names below the observed rejected 51-char form.
    assert read_json(output / "task-manifest.json")["new_answer_generation_calls"] == 0
