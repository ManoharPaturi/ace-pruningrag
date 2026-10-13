"""Tamper tests use a fake tokenizer, not fabricated claims of GPU execution."""

import json
import runpy
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.claim_extraction import (
    digest,
    extraction_messages,
    extraction_tasks,
    validate_proposal,
)

RAW = json.dumps(dict.fromkeys(("entity", "relation", "period", "unit", "predicate", "value")))


class FakeTokenizer:
    @classmethod
    def from_pretrained(cls, *args, **kwargs):
        return cls()

    def apply_chat_template(self, messages, **kwargs):
        return [1, 2] if "?" in messages[-1]["content"] else [1, 2, 3]

    def decode(self, ids, **kwargs):
        return RAW

    def __len__(self):
        return 10


@pytest.fixture
def artifact(tmp_path, monkeypatch):
    original = Path(__file__).resolve().parents[1]
    root = tmp_path / "root"
    for path in (
        "src/ace_pruningrag/claim_extraction.py",
        "scripts/claim_extraction_driver.py",
        "scripts/kaggle_generated_pilot.py",
        "configs/claim_extraction.json",
        "configs/generated_pilot.json",
    ):
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original / path, target)
    write_json(root / "data/models/generator/generation_config.json", {"eos_token_id": [9]})
    rows = [
        {
            "interaction_id": "q",
            "policy": "a",
            "query": "Who is A?",
            "query_time": "2024",
            "prediction": "NEVER MODEL INPUT",
            "selected": [{"evidence_id": "e", "content": "A is B."}],
        }
    ]
    trace = root / "trace.jsonl"
    trace.write_text(json.dumps(rows[0]) + "\n")
    build = runpy.run_path(str(original / "scripts/build_extraction_kernel.py"))["build"]
    bundle = root / "bundle"
    metadata = build(root, trace, bundle, "fixture")
    assert metadata["title"].lower().replace(" ", "-") == metadata["id"].split("/")[1]
    assert metadata["is_private"]
    run = root / "output"
    tasks = extraction_tasks(rows)
    records = []
    lengths = []
    for task in tasks:
        messages = extraction_messages(task)
        n = len(FakeTokenizer().apply_chat_template(messages))
        lengths.append(n)
        records.append(
            {
                "task_sha256": task["task_sha256"],
                "kind": task["kind"],
                "input_tokens": n,
                "output_ids": [1, 9],
                "output_tokens": 2,
                "raw_proposal": RAW,
                "messages_sha256": digest(messages),
                "validation": validate_proposal(task, RAW),
                "hit_output_cap_without_eos": False,
                "actual_extraction_sequences": 1,
            }
        )
    run.mkdir()
    for name in ("extractions.jsonl", "progress.jsonl"):
        (run / name).write_text("".join(json.dumps(r) + "\n" for r in records))
    hashes = read_json(bundle / "bundle-manifest.json")
    write_json(run / "bundle_manifest.json", hashes)
    write_json(
        run / "environment_isolation.json",
        {"base_preserved": True, "base_before": {}, "base_after": {}},
    )
    config = read_json(root / "configs/claim_extraction.json")
    write_json(
        run / "completion.json",
        {
            "status": "bounded_extraction_diagnostic_complete",
            "tasks": 2,
            "extraction_sequences": 2,
            "generate_invocations": 1,
            "unextracted": 0,
            "input_tokens": sum(lengths),
            "padded_input_tokens": max(lengths) * 2,
            "output_tokens": 4,
            "maximum_reserved_request_tokens": max(lengths) + 160,
            "trace_sha256": sha256_file(run / "extractions.jsonl"),
            "tasks_sha256": hashes["configs/extraction_tasks.json"],
            "validation_counts": {"span_bound_proposal": 2},
            "actual_new_answer_generation_calls": 0,
            "answer_acceptance_enabled": False,
            "semantic_tuple_verification": False,
            "eos_token_ids": [9],
            "scope": config["scope"],
            "generation_seconds": 0.0,
            "model_loading_seconds": 0.0,
            "runtime": {"dtype": "float32"},
            "dependency_versions": {
                "transformers": "4.57.3",
                "huggingface_hub": "0.36.0",
                "tokenizers": "0.22.1",
                "safetensors": "0.6.2",
                "sentencepiece": "0.2.1",
            },
        },
    )
    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace(AutoTokenizer=FakeTokenizer))
    verify = runpy.run_path(str(original / "scripts/verify_claim_extraction.py"))["verify"]
    return root, bundle, run, trace, verify


def test_reconstruction_reports_limits_not_semantic_quality(artifact):
    root, bundle, run, trace, verify = artifact
    result = verify(root, bundle, run, trace)
    assert result["extraction_sequences"] == 2
    assert not result["answer_acceptance_enabled"]
    assert result["semantic_tuple_accuracy"] is None
    assert not result["neural_generation_independently_recomputed"]


@pytest.mark.parametrize(
    "mutation", ["decode", "cost", "progress", "source", "manifest", "termination"]
)
def test_changed_provenance_decode_cost_and_progress_are_rejected(artifact, mutation):
    root, bundle, run, trace, verify = artifact
    if mutation in ("decode", "termination"):
        records = [
            json.loads(line) for line in (run / "extractions.jsonl").read_text().splitlines()
        ]
        if mutation == "decode":
            records[0]["raw_proposal"] = "Unbound replacement"
        else:
            records[0]["output_ids"] = [9, 1]
        (run / "extractions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    elif mutation == "cost":
        summary = read_json(run / "completion.json")
        summary["generate_invocations"] = 0
        write_json(run / "completion.json", summary)
    elif mutation == "progress":
        (run / "progress.jsonl").write_text("")
    elif mutation == "source":
        row = json.loads(trace.read_text())
        row["selected"][0]["content"] = "Changed under same ID"
        trace.write_text(json.dumps(row) + "\n")
    elif mutation == "manifest":
        write_json(run / "bundle_manifest.json", {})
    with pytest.raises(ValueError):
        verify(root, bundle, run, trace)
