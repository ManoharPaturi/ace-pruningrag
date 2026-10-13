"""Exercise reconstruction with a synthetic tokenizer, not a claimed neural run."""

import json
import runpy
from pathlib import Path

import pytest

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.claim_extraction import digest
from ace_pruningrag.query_requirements import messages, validate
from ace_pruningrag.requirements_protocol import requirement_tasks
from ace_pruningrag.unicode_claims import permitted_spans

ROOT = Path(__file__).resolve().parents[1]
AutoTokenizer = pytest.importorskip("transformers").AutoTokenizer


def test_reconstruction_checks_input_identity_outputs_progress_and_costs(tmp_path, monkeypatch):
    class Tokenizer:
        def __len__(self):
            return 151936

        def apply_chat_template(self, messages, **kwargs):
            return [100] * 10

        def decode(self, ids, **kwargs):
            return "".join(chr(i) for i in ids if i not in (151643, 151645))

    monkeypatch.setattr(AutoTokenizer, "from_pretrained", lambda *args, **kwargs: Tokenizer())
    trace = tmp_path / "source.jsonl"
    row = {
        "interaction_id": "q",
        "policy": "test",
        "query": "Who won?",
        "query_time": "2024",
        "selected": [],
    }
    trace.write_text(json.dumps(row) + "\n")
    bundle, run = tmp_path / "bundle", tmp_path / "run"
    run.mkdir()
    runpy.run_path(str(ROOT / "scripts/build_requirements_3b_kernel.py"))["build"](
        ROOT, trace, bundle, "test-owner"
    )
    hashes = read_json(bundle / "bundle-manifest.json")
    write_json(run / "bundle_manifest.json", hashes)
    config = read_json(ROOT / "configs/query_requirements_3b.json")
    base = read_json(ROOT / config["generator_config"])
    task = requirement_tasks([row])[0]
    raw = json.dumps(
        {
            "status": "ambiguous",
            "composition": "unknown",
            "cardinality": None,
            "variables": [],
            "clauses": [],
            "operation": {"kind": "unknown", "cue": None, "operands": [], "result": None},
        },
        separators=(",", ":"),
    )
    ids = [ord(c) for c in raw] + [151645]
    record = {
        "task_sha256": task["task_sha256"],
        "kind": "query",
        "input_tokens": 10,
        "input_ids_sha256": digest([100] * 10),
        "output_ids": ids,
        "output_tokens": len(ids),
        "raw_proposal": raw,
        "messages_sha256": digest(messages(task)),
        "validation": validate(task, raw),
        "permitted_span_count": len(permitted_spans(task["text"])),
        "hit_output_cap_without_eos": False,
        "actual_extraction_sequences": 1,
    }
    for name in ("extractions.jsonl", "progress.jsonl"):
        (run / name).write_text(json.dumps(record) + "\n")
    summary = {
        "status": "bounded_requirements_extraction_complete",
        "protocol_id": config["protocol_id"],
        "extractor_repository": base["generator"]["repository"],
        "extractor_revision": base["generator"]["revision"],
        "decoding_defaults_sha256": config["decoding_config_sha256"],
        "span_policy_sha256": config["span_policy_sha256"],
        "tasks": 1,
        "extraction_sequences": 1,
        "generate_invocations": 1,
        "unextracted": 0,
        "input_tokens": 10,
        "padded_input_tokens": 10,
        "output_tokens": len(ids),
        "maximum_reserved_request_tokens": 2058,
        "trace_sha256": sha256_file(run / "extractions.jsonl"),
        "tasks_sha256": hashes["configs/constrained_tasks.json"],
        "validation_counts": {record["validation"]["status"]: 1},
        "actual_new_answer_generation_calls": 0,
        "answer_acceptance_enabled": False,
        "semantic_requirements_verification": False,
        "eos_token_ids": [151643, 151645],
        "scope": config["scope"],
        "constraint_dependency_versions": config["constraints_dependencies"],
        "format_enforcement": "ordered_JSON_bounded_requirement_reference_trie",
        "generation_seconds": 0.2,
        "model_loading_seconds": 0.1,
        "dependency_versions": {
            "transformers": "4.57.3",
            "huggingface_hub": "0.36.0",
            "tokenizers": "0.22.1",
            "safetensors": "0.6.2",
            "sentencepiece": "0.2.1",
        },
        "runtime": {"dtype": "float32", "gpu": "synthetic"},
    }
    write_json(run / "completion.json", summary)
    write_json(
        run / "environment_isolation.json",
        {"base_preserved": True, "base_before": {}, "base_after": {}},
    )
    verify = runpy.run_path(str(ROOT / "scripts/verify_requirements_3b.py"))["verify"]
    result = verify(ROOT, bundle, run, trace)
    assert result["extraction_sequences"] == 1
    assert result["answer_acceptance_enabled"] is False
    assert not result["neural_generation_independently_recomputed"]
    bad = dict(record, input_ids_sha256="0" * 64)
    (run / "extractions.jsonl").write_text(json.dumps(bad) + "\n")
    with pytest.raises(ValueError, match="bindings"):
        verify(ROOT, bundle, run, trace)
    (run / "extractions.jsonl").write_text(json.dumps(record) + "\n")
    write_json(run / "completion.json", {**summary, "output_tokens": len(ids) + 1})
    with pytest.raises(ValueError, match="costs"):
        verify(ROOT, bundle, run, trace)
    write_json(run / "completion.json", summary)
    (run / "progress.jsonl").write_text("")
    with pytest.raises(ValueError, match="progress"):
        verify(ROOT, bundle, run, trace)
