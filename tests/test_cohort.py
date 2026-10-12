import ast
import base64
import importlib.util
import json
import zlib
from pathlib import Path

from ace_pruningrag.cohort import METHODS, prepare_selectors
from ace_pruningrag.dataset import QueryInput


def test_all_selectors_share_candidates_and_count_complete_prompt_budget():
    page = {
        "page_url": "https://fixture.invalid/source",
        "page_name": "Fixture",
        "page_last_modified": "",
        "page_result": "alpha beta alpha gamma delta beta",
        "page_snippet": "beta delta gamma",
    }
    query = QueryInput("fixture", "alpha beta?", "02/28/2024, 09:00:00 PT", (page,))
    config = {
        "chunk_words": 2,
        "candidate_limit": 6,
        "max_items": 2,
        "total_tokens": 500,
        "max_new_tokens": 20,
        "system_prompt": "Use supplied evidence.",
    }

    def tokenize(msgs):
        return list(range(len(json.dumps(msgs).split())))

    prepared, cost = prepare_selectors(query, config, tokenize)
    assert tuple(prepared) == METHODS
    assert cost["shared_web_retrieval_calls"] == 1
    assert len({tuple(r["candidate_ids"]) for r in prepared.values()}) == 1
    for row in prepared.values():
        assert len(row["input_ids"]) + 20 <= 500
        assert len(row["selected"]) <= 2
        assert row["groups"] == row["conflicts"] == []
        assert "answer" not in row and "domain" not in row


def test_cohort_gpu_bundle_uses_distinct_driver_and_preserves_frozen_ledger(tmp_path):
    root = Path(__file__).parents[1]
    spec = importlib.util.spec_from_file_location(
        "builder", root / "scripts/build_kaggle_kernel.py"
    )
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    metadata = builder.build(root, tmp_path / "kernel", "fixture-owner", "cohort")
    source = (tmp_path / "kernel/bootstrap.py").read_text()
    assert 'str(root / "scripts/cohort_driver.py"),' in source
    assert '"--config"' not in source
    assert 'str(output / "generated")' in source
    tree = ast.parse(source)
    payload = next(
        ast.literal_eval(n.value)
        for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "PAYLOAD" for t in n.targets)
    )
    files = json.loads(zlib.decompress(base64.b64decode(payload)))["files"]
    assert "configs/cohort_evaluation.json" in files
    assert "results/evaluation/prospective_v1/manifest.json" in files
    assert all(
        name in files
        for name in json.loads(files["configs/prospective_evaluation.json"])["exposure_sources"]
    )
    assert not any(name.startswith(("runs/", "data/")) for name in files)
    assert metadata["is_private"] and metadata["id"].endswith("prospective-selectors")
