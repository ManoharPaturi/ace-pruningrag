"""Reconstruct both extractor runs and compare identities/costs without semantic promotion."""

import argparse
import json
import runpy
from pathlib import Path

from transformers import AutoTokenizer

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.claim_extraction import digest
from ace_pruningrag.query_requirements import messages
from ace_pruningrag.requirements_protocol import requirement_tasks


def compare(root):
    source = root / "runs/kaggle/cohort-output-v1/cohort-pilot/generated/predictions.jsonl"
    tasks = requirement_tasks([json.loads(s) for s in source.read_text().splitlines()])
    runs, proofs, outputs = [], [], []
    for script, bundle, run, proof in (
        (
            "verify_requirements_extraction.py",
            "requirements-kernel-v1",
            "requirements-output-v1/requirements-pilot",
            "requirements_verification.json",
        ),
        (
            "verify_requirements_3b.py",
            "requirements-3b-kernel-v1",
            "requirements-3b-output-v1/requirements-3b-pilot",
            "requirements_3b_verification.json",
        ),
    ):
        path = root / "runs/version1" / run
        reconstruct = runpy.run_path(str(root / "scripts" / script))["verify"]
        fresh = reconstruct(root, root / "runs/version1" / bundle, path, source)
        if fresh != read_json(root / "results/version1" / proof):
            raise ValueError("model comparison proof differs from fresh reconstruction")
        proofs.append(fresh)
        runs.append(read_json(path / "completion.json"))
        outputs.append(
            [json.loads(s) for s in (path / "extractions.jsonl").read_text().splitlines()]
        )
    if (
        proofs[0]["tasks_sha256"] != proofs[1]["tasks_sha256"]
        or runs[0]["runtime"] != runs[1]["runtime"]
        or runs[0]["dependency_versions"] != runs[1]["dependency_versions"]
        or runs[0]["constraint_dependency_versions"] != runs[1]["constraint_dependency_versions"]
        or runs[0]["eos_token_ids"] != runs[1]["eos_token_ids"]
        or runs[0]["span_policy_sha256"] != runs[1]["span_policy_sha256"]
        or runs[0]["maximum_reserved_request_tokens"] != runs[1]["maximum_reserved_request_tokens"]
        or runs[1]["decoding_defaults_sha256"]
        != next(
            a["sha256"]
            for a in read_json(root / "configs/generated_pilot.json")["assets"]
            if a["local_path"].endswith("generation_config.json")
        )
    ):
        raise ValueError("model comparison task/runtime/decode identities differ")
    base = read_json(root / "configs/generated_pilot.json")
    tokenizer = AutoTokenizer.from_pretrained(
        root / base["generator"]["directory"], local_files_only=True, trust_remote_code=False
    )
    for task, control, variant in zip(tasks, *outputs, strict=True):
        encoded = tokenizer.apply_chat_template(
            messages(task), tokenize=True, add_generation_prompt=True
        )
        if (
            control["messages_sha256"] != variant["messages_sha256"]
            or control["input_tokens"] != variant["input_tokens"]
            or variant["input_ids_sha256"] != digest(encoded)
            or control["permitted_span_count"] != variant["permitted_span_count"]
        ):
            raise ValueError("model comparison input/prompt/spans differ")
    reviews = read_json(root / "results/version1/requirements_3b_review_progress.json")
    if reviews["execution_verification_sha256"] != sha256_file(
        root / "results/version1/requirements_3b_verification.json"
    ):
        raise ValueError("model comparison review proof binding differs")
    bound = [
        i
        for i, r in enumerate(outputs[1])
        if r["validation"]["status"] == "bound_requirement_proposal"
    ]
    empty_bound = []
    for i in bound:
        p = json.loads(outputs[1][i]["raw_proposal"])
        if all(
            all(value is None for key, value in c.items() if key != "text") for c in p["clauses"]
        ):
            empty_bound.append(i)
    return {
        "scope": (
            "Executed model-variant comparison on inspected development tasks; "
            "no independent accuracy"
        ),
        "tasks": len(tasks),
        "same_task_payload": True,
        "same_prompts": True,
        "same_reconstructed_input_ids": True,
        "same_runtime_and_dependencies": True,
        "same_span_policy_and_budgets": True,
        "control_revision": proofs[0]["generator_revision"],
        "variant_revision": proofs[1]["generator_revision"],
        "variant_decode_defaults_sha256": runs[1]["decoding_defaults_sha256"],
        "raw_proposals_changed": sum(
            a["raw_proposal"] != b["raw_proposal"] for a, b in zip(*outputs, strict=True)
        ),
        "control_validation_counts": runs[0]["validation_counts"],
        "variant_validation_counts": runs[1]["validation_counts"],
        "variant_bound_indices": bound,
        "variant_bound_with_all_clause_roles_null": empty_bound,
        "control_costs": {
            k: runs[0][k]
            for k in (
                "generate_invocations",
                "input_tokens",
                "padded_input_tokens",
                "output_tokens",
                "generation_seconds",
                "model_loading_seconds",
            )
        },
        "variant_costs": {
            k: runs[1][k]
            for k in (
                "generate_invocations",
                "input_tokens",
                "padded_input_tokens",
                "output_tokens",
                "generation_seconds",
                "model_loading_seconds",
            )
        },
        "control_trace_sha256": runs[0]["trace_sha256"],
        "variant_trace_sha256": runs[1]["trace_sha256"],
        "variant_review_progress_sha256": sha256_file(
            root / "results/version1/requirements_3b_review_progress.json"
        ),
        "independent_human_review": False,
        "semantic_requirement_improvement_established": False,
        "answer_acceptance_enabled": False,
        "timing_is_unbiased_hardware_benchmark": False,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    write_json(args.output, compare(Path.cwd()))
