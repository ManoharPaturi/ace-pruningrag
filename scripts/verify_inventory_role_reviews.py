"""Reconstruct inventory execution and validate valid/rejected AI assessment progress."""

import argparse
import json
import runpy
from pathlib import Path

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.claim_extraction import extraction_tasks
from ace_pruningrag.inventory_role_review import summarize


def verify(root, batches):
    reconstruct = runpy.run_path(str(root / "scripts/verify_inventory_reviews.py"))["verify"]
    valid_proof_path = root / "results/version1/inventory_valid_review_progress.json"
    if read_json(valid_proof_path) != reconstruct(root):
        raise ValueError("inventory valid-role progress differs from fresh reconstruction")
    source = root / "runs/kaggle/cohort-output-v1/cohort-pilot/generated/predictions.jsonl"
    trace = root / "runs/version1/inventory-output-v1/inventory-pilot/extractions.jsonl"
    valid_path = root / "runs/version1/inventory-valid-ai-review-v1.json"
    tasks = extraction_tasks([json.loads(s) for s in source.read_text().splitlines()])
    outputs = [json.loads(s) for s in trace.read_text().splitlines()]
    records, hashes = [], {}
    for path in batches:
        if str(path) in hashes:
            raise ValueError("duplicate inventory rejected-review batch")
        batch = read_json(path)
        if batch["source_trace_sha256"] != sha256_file(source) or batch[
            "extraction_trace_sha256"
        ] != sha256_file(trace):
            raise ValueError("inventory rejected-review trace binding differs")
        records.extend(batch["records"])
        hashes[str(path.relative_to(root))] = sha256_file(path)
    return {
        **summarize(tasks, outputs, read_json(valid_path)["records"], records),
        "source_trace_sha256": sha256_file(source),
        "extraction_trace_sha256": sha256_file(trace),
        "valid_review_progress_sha256": sha256_file(valid_proof_path),
        "valid_review_batch_sha256": sha256_file(valid_path),
        "rejected_review_batches_sha256": hashes,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--batch", type=Path, action="append", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    root = Path.cwd()
    write_json(args.output, verify(root, [path.resolve() for path in args.batch]))
