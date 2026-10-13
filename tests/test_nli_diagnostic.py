import json
import runpy
from pathlib import Path

import pytest

from ace_pruningrag.nli_diagnostic import answer_source_pairs, diagnostic_record


def rows():
    return [
        {
            "interaction_id": "q",
            "policy": "p",
            "query": "Who?",
            "query_time": "2024",
            "prediction": "A person",
            "gold_answer": "PRIVATE_LABEL",
            "evaluation": {"correct": True},
            "selected": [{"evidence_id": "e", "content": "An actual source excerpt"}],
        }
    ]


def test_pairs_bind_exact_source_and_prediction_without_labels():
    pair = answer_source_pairs(rows())[0]
    assert pair["hypothesis"] == "A person"
    assert "gold_answer" not in pair and "evaluation" not in pair
    original = pair["pair_sha256"]
    changed = rows()
    changed[0]["selected"][0]["content"] += " altered"
    assert answer_source_pairs(changed)[0]["pair_sha256"] != original
    with pytest.raises(ValueError, match="duplicate"):
        answer_source_pairs(rows() + rows())
    with pytest.raises(ValueError, match="cap"):
        answer_source_pairs(rows(), max_pairs=0)


def test_entailment_diagnostic_does_not_promote_accuracy_or_completeness():
    pair = answer_source_pairs(rows())[0]
    record = diagnostic_record(pair, 30, [-2, 5, 0])
    assert record["model_label"] == "entailment"
    assert record["answer_acceptance"] == "not_established"
    assert not record["query_completeness_verified"] and not record["factual_correctness_verified"]
    assert not record["calibrated"]
    assert diagnostic_record(pair, 513)["status"] == "over_pair_budget_unscored"
    with pytest.raises(ValueError, match="over-budget"):
        diagnostic_record(pair, 513, [0, 1, 0])
    with pytest.raises(ValueError, match="finite"):
        diagnostic_record(pair, 30, [0, float("nan"), 0])


def test_new_kernel_title_resolves_to_its_private_unique_id(tmp_path):
    root = Path(__file__).resolve().parents[1]
    trace = tmp_path / "source.jsonl"
    trace.write_text(json.dumps(rows()[0]) + "\n")
    build = runpy.run_path(str(root / "scripts/build_nli_kernel.py"))["build"]
    metadata = build(root, trace, tmp_path / "bundle", "fixture")
    assert metadata["title"].lower().replace(" ", "-") == metadata["id"].split("/")[1]
    assert metadata["is_private"]
    compile((tmp_path / "bundle/bootstrap.py").read_text(), "bounded-nli", "exec")
