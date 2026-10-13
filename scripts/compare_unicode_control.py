"""Compare reconstructed Unicode GPU outputs with the immutable v1 control."""

import argparse
import json
from collections import Counter
from pathlib import Path

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.claim_extraction import digest
from ace_pruningrag.unicode_protocol import validate_protocol


def compare(root, revised_run, revised_proof):
    old_path = root / "runs/version1/constrained-output-v1/constrained-pilot/extractions.jsonl"
    new_path = revised_run / "extractions.jsonl"
    old_proof_path = root / "results/version1/constrained_verification.json"
    old_proof, new_proof = read_json(old_proof_path), read_json(revised_proof)
    config = read_json(root / "configs/unicode_extraction.json")
    validate_protocol(root, config)
    if (
        old_proof["status"] != "constrained_spans_decode_and_costs_reconstructed"
        or new_proof["status"] != "unicode_spans_decode_and_costs_reconstructed"
        or old_proof["trace_sha256"] != sha256_file(old_path)
        or new_proof["trace_sha256"] != sha256_file(new_path)
        or old_proof["source_trace_sha256"] != new_proof["source_trace_sha256"]
        or old_proof["tasks_sha256"] != new_proof["tasks_sha256"]
        or old_proof["generator_revision"] != new_proof["generator_revision"]
        or new_proof["protocol_id"] != config["protocol_id"]
        or new_proof["span_policy_sha256"] != config["span_policy_sha256"]
        or new_proof["answer_acceptance_enabled"] is not False
    ):
        raise ValueError("Unicode comparison requires matching reconstructed controls")
    old = [json.loads(x) for x in old_path.read_text().splitlines()]
    new = [json.loads(x) for x in new_path.read_text().splitlines()]
    if len(old) != len(new) or len(new) != new_proof["tasks"]:
        raise ValueError("Unicode control task coverage differs")
    changed, counters = [], Counter()
    for a, b in zip(old, new, strict=True):
        for key in ("task_sha256", "kind", "input_tokens", "messages_sha256"):
            if a[key] != b[key]:
                raise ValueError("Unicode control identity, input or prompt differs")
        same_raw = a["raw_proposal"] == b["raw_proposal"]
        same_ids = a["output_ids"] == b["output_ids"]
        counters["unchanged_raw_proposals" if same_raw else "changed_raw_proposals"] += 1
        counters["unchanged_output_ids" if same_ids else "changed_output_ids"] += 1
        if not same_raw or not same_ids:
            changed.append(
                {
                    "task_sha256": a["task_sha256"],
                    "kind": a["kind"],
                    "old_proposal_sha256": digest(a["raw_proposal"]),
                    "new_proposal_sha256": digest(b["raw_proposal"]),
                    "old_validation": a["validation"]["status"],
                    "new_validation": b["validation"]["status"],
                    "raw_proposal_changed": not same_raw,
                    "output_ids_changed": not same_ids,
                }
            )
    return {
        "scope": (
            "Same-task Unicode policy GPU control; structural change is not semantic improvement"
        ),
        "tasks": len(new),
        "all_task_bindings_equal": True,
        "all_prompts_equal": True,
        "all_input_token_counts_equal": True,
        "protocol_id": config["protocol_id"],
        "span_policy_sha256": config["span_policy_sha256"],
        "control_trace_sha256": sha256_file(old_path),
        "revised_trace_sha256": sha256_file(new_path),
        "control_verification_sha256": sha256_file(old_proof_path),
        "revised_verification_sha256": sha256_file(revised_proof),
        "generator_config_sha256": sha256_file(root / config["generator_config"]),
        "runtime_snapshots_equal": old_proof["runtime"] == new_proof["runtime"],
        "output_comparison": dict(counters),
        "changed_records": changed,
        "control_output_tokens": old_proof["output_tokens"],
        "revised_output_tokens": new_proof["output_tokens"],
        "revised_validation_counts": new_proof["validation_counts"],
        "changed_proposal_reviews_complete": False,
        "semantic_role_improvement_established": False,
        "external_truth_verified": False,
        "answer_acceptance_enabled": False,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--verification", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise FileExistsError(a.output)
    write_json(a.output, compare(Path.cwd(), a.run, a.verification))
