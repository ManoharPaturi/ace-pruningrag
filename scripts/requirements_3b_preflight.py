"""Tokenize blinded query tasks with the pinned tokenizer; no model inference."""

import argparse
import json
from pathlib import Path

from transformers import AutoTokenizer

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.claim_extraction import digest
from ace_pruningrag.query_requirements import messages
from ace_pruningrag.requirements_3b_protocol import validate_protocol
from ace_pruningrag.requirements_protocol import requirement_tasks
from ace_pruningrag.unicode_claims import permitted_spans


def preflight(root, trace):
    config = read_json(root / "configs/query_requirements_3b.json")
    validate_protocol(root, config)
    base = read_json(root / config["generator_config"])
    tasks = requirement_tasks([json.loads(s) for s in trace.read_text().splitlines()])
    if not tasks or len(tasks) > config["max_tasks"]:
        raise ValueError("requirements task count outside bounded protocol")
    tokenizer = AutoTokenizer.from_pretrained(
        root / base["generator"]["directory"], local_files_only=True, trust_remote_code=False
    )
    records = []
    for task in tasks:
        spans = permitted_spans(task["text"])
        encoded = tokenizer.apply_chat_template(
            messages(task), tokenize=True, add_generation_prompt=True
        )
        n = len(encoded)
        reserved = n + config["max_output_tokens"]
        if reserved > config["max_input_and_output_tokens"]:
            raise ValueError("requirements request over full reserved budget")
        records.append(
            {
                "task_sha256": task["task_sha256"],
                "messages_sha256": digest(messages(task)),
                "input_tokens": n,
                "input_ids_sha256": digest(encoded),
                "reserved_tokens": reserved,
                "permitted_span_count": len(spans),
            }
        )
    return {
        "status": "requirements_tokenizer_preflight_complete",
        "protocol_id": config["protocol_id"],
        "span_policy_sha256": config["span_policy_sha256"],
        "source_trace_sha256": sha256_file(trace),
        "generator_revision": base["generator"]["revision"],
        "tasks": len(tasks),
        "source_tasks": 0,
        "input_tokens": sum(r["input_tokens"] for r in records),
        "maximum_reserved_tokens": max(r["reserved_tokens"] for r in records),
        "max_generate_invocations": (len(tasks) + config["batch_size"] - 1) // config["batch_size"],
        "actual_llm_calls": 0,
        "answer_acceptance_enabled": False,
        "semantic_requirements_verified": False,
        "requests": records,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--trace", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    write_json(args.output, preflight(Path.cwd(), args.trace))
