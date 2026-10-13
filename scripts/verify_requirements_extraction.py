"""Reconstruct extraction inputs, decoded outputs, exact spans and cumulative costs."""

import argparse
import ast
import base64
import hashlib
import json
import math
import zlib
from collections import Counter
from pathlib import Path

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.claim_extraction import (
    digest,
)
from ace_pruningrag.query_requirements import character_parser
from ace_pruningrag.query_requirements import (
    messages as extraction_messages,
)
from ace_pruningrag.query_requirements import (
    validate as validate_constrained,
)
from ace_pruningrag.requirements_protocol import requirement_tasks
from ace_pruningrag.unicode_claims import permitted_spans


def verify(root, bundle_dir, run, trace):
    from transformers import AutoTokenizer

    tree = ast.parse((bundle_dir / "bootstrap.py").read_text())
    assignment = next(
        n
        for n in tree.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "PAYLOAD" for t in n.targets)
    )
    payload = json.loads(zlib.decompress(base64.b64decode(ast.literal_eval(assignment.value))))
    hashes = read_json(bundle_dir / "bundle-manifest.json")
    if payload["sha256"] != hashes or read_json(run / "bundle_manifest.json") != hashes:
        raise ValueError("extraction bundle manifests differ")
    if set(payload["files"]) != set(hashes):
        raise ValueError("extraction bundle coverage differs")
    for name, content in payload["files"].items():
        if hashlib.sha256(content.encode()).hexdigest() != hashes[name]:
            raise ValueError("extraction submitted content differs")
        if name != "configs/constrained_tasks.json" and sha256_file(root / name) != hashes[name]:
            raise ValueError(f"extraction current source differs from submitted: {name}")
    config = read_json(root / "configs/query_requirements.json")
    from ace_pruningrag.requirements_protocol import validate_protocol

    validate_protocol(root, config)
    base = read_json(root / config["generator_config"])
    input_payload = json.loads(payload["files"]["configs/constrained_tasks.json"])
    tasks = requirement_tasks([json.loads(line) for line in trace.read_text().splitlines()])
    if input_payload["tasks"] != tasks or input_payload["source_trace_sha256"] != sha256_file(
        trace
    ):
        raise ValueError("blinded extraction tasks differ from original trace")
    if len(tasks) > config["max_tasks"]:
        raise ValueError("extraction task cap differs")
    tokenizer = AutoTokenizer.from_pretrained(
        root / base["generator"]["directory"], local_files_only=True, trust_remote_code=False
    )
    vocabulary_size = len(tokenizer)
    eos = read_json(root / base["generator"]["directory"] / "generation_config.json")[
        "eos_token_id"
    ]
    eos = set(eos if isinstance(eos, list) else [eos])
    records = [json.loads(line) for line in (run / "extractions.jsonl").read_text().splitlines()]
    if len(records) != len(tasks):
        raise ValueError("extraction coverage differs")
    eligible_lengths, eligible_records = [], []
    for task, record in zip(tasks, records, strict=True):
        messages = extraction_messages(task)
        n = len(tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True))
        if n + config["max_output_tokens"] > config["max_input_and_output_tokens"]:
            expected = {
                "task_sha256": task["task_sha256"],
                "input_tokens": n,
                "status": "over_budget_unextracted",
                "actual_extraction_sequences": 0,
            }
        else:
            ids = record["output_ids"]
            if (
                not isinstance(ids, list)
                or not ids
                or len(ids) > config["max_output_tokens"]
                or any(type(i) is not int or i < 0 or i >= vocabulary_size for i in ids)
                or any(i in eos for i in ids[:-1])
            ):
                raise ValueError("extraction token IDs/caps/termination differ")
            raw = tokenizer.decode(ids, skip_special_tokens=True).strip()
            expected = {
                "task_sha256": task["task_sha256"],
                "kind": task["kind"],
                "input_tokens": n,
                "output_ids": ids,
                "output_tokens": len(ids),
                "raw_proposal": raw,
                "messages_sha256": digest(messages),
                "validation": validate_constrained(task, raw),
                "permitted_span_count": len(permitted_spans(task["text"])),
                "hit_output_cap_without_eos": len(ids) == config["max_output_tokens"]
                and ids[-1] not in eos,
                "actual_extraction_sequences": 1,
            }
            parser = character_parser(task)
            for char in raw:
                if char not in parser.get_allowed_characters():
                    raise ValueError("requirements output differs from closed ordered grammar")
                parser = parser.add_character(char)
            if not parser.can_end() and not expected["hit_output_cap_without_eos"]:
                raise ValueError("requirements output ended before complete grammar")
            eligible_lengths.append(n)
            eligible_records.append(record)
        if record != expected:
            raise ValueError("extraction bindings, span validation or decode differs")
    progress = [json.loads(line) for line in (run / "progress.jsonl").read_text().splitlines()]
    if progress != eligible_records:
        raise ValueError("extraction progress differs from final trace")
    padded = sum(
        max(eligible_lengths[i : i + 4]) * len(eligible_lengths[i : i + 4])
        for i in range(0, len(eligible_lengths), 4)
    )
    expected_summary = {
        "status": "bounded_requirements_extraction_complete",
        "protocol_id": config["protocol_id"],
        "span_policy_sha256": config["span_policy_sha256"],
        "tasks": len(tasks),
        "extraction_sequences": len(eligible_records),
        "generate_invocations": math.ceil(len(eligible_records) / config["batch_size"]),
        "unextracted": len(tasks) - len(eligible_records),
        "input_tokens": sum(eligible_lengths),
        "padded_input_tokens": padded,
        "output_tokens": sum(r["output_tokens"] for r in eligible_records),
        "maximum_reserved_request_tokens": max(
            (n + config["max_output_tokens"] for n in eligible_lengths), default=0
        ),
        "trace_sha256": sha256_file(run / "extractions.jsonl"),
        "tasks_sha256": hashes["configs/constrained_tasks.json"],
        "validation_counts": dict(
            Counter(r.get("validation", {}).get("status", r.get("status")) for r in records)
        ),
        "actual_new_answer_generation_calls": 0,
        "answer_acceptance_enabled": False,
        "semantic_requirements_verification": False,
        "eos_token_ids": sorted(eos),
        "scope": config["scope"],
        "constraint_dependency_versions": config["constraints_dependencies"],
        "format_enforcement": "ordered_JSON_bounded_requirement_reference_trie",
    }
    summary = read_json(run / "completion.json")
    if any(summary.get(k) != value for k, value in expected_summary.items()):
        raise ValueError("extraction costs or protocol summary differs")
    for key in ("generation_seconds", "model_loading_seconds"):
        if (
            type(summary.get(key)) not in (int, float)
            or not math.isfinite(summary[key])
            or summary[key] < 0
        ):
            raise ValueError("extraction elapsed time differs")
    isolation = read_json(run / "environment_isolation.json")
    if (
        isolation["base_preserved"] is not True
        or isolation["base_before"] != isolation["base_after"]
    ):
        raise ValueError("extraction isolation differs")
    versions = {
        "transformers": "4.57.3",
        "huggingface_hub": "0.36.0",
        "tokenizers": "0.22.1",
        "safetensors": "0.6.2",
        "sentencepiece": "0.2.1",
    }
    if summary["dependency_versions"] != versions or summary["runtime"]["dtype"] != "float32":
        raise ValueError("extraction runtime versions differ")
    return {
        **expected_summary,
        "status": "requirements_spans_decode_and_costs_reconstructed",
        "generator_revision": base["generator"]["revision"],
        "source_trace_sha256": sha256_file(trace),
        "semantic_requirement_accuracy": None,
        "complete_requirement_coverage": None,
        "neural_generation_independently_recomputed": False,
        "timing": {k: summary[k] for k in ("generation_seconds", "model_loading_seconds")},
        "runtime": summary["runtime"],
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--source-trace", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise FileExistsError(a.output)
    write_json(a.output, verify(Path.cwd(), a.bundle, a.run, a.source_trace))
