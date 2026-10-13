"""Freshly reconstruct GPU execution before binding all query-proposal AI reviews."""

import argparse
import json
import runpy
from pathlib import Path

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.requirements_protocol import requirement_tasks
from ace_pruningrag.requirements_review import summarize


def verify(root):
    source = root / "runs/kaggle/cohort-output-v1/cohort-pilot/generated/predictions.jsonl"
    run = root / "runs/version1/requirements-output-v1/requirements-pilot"
    proof = root / "results/version1/requirements_verification.json"
    reconstruct = runpy.run_path(str(root / "scripts/verify_requirements_extraction.py"))["verify"]
    if read_json(proof) != reconstruct(
        root, root / "runs/version1/requirements-kernel-v1", run, source
    ):
        raise ValueError("requirements execution proof differs from fresh reconstruction")
    checklist_path = root / "runs/version1/requirements-query-checklist-ai-v1.json"
    batch_path = root / "runs/version1/requirements-ai-review-v1.json"
    batch, checklist = read_json(batch_path), read_json(checklist_path)
    trace = run / "extractions.jsonl"
    if (
        batch["source_trace_sha256"] != sha256_file(source)
        or batch["extraction_trace_sha256"] != sha256_file(trace)
        or batch["query_checklist_sha256"] != sha256_file(checklist_path)
        or checklist["tasks_sha256"] != read_json(proof)["tasks_sha256"]
        or checklist["bundle_manifest_sha256"]
        != sha256_file(root / "runs/version1/requirements-kernel-v1/bundle-manifest.json")
    ):
        raise ValueError("requirements review trace/checklist hashes differ")
    tasks = requirement_tasks([json.loads(s) for s in source.read_text().splitlines()])
    outputs = [json.loads(s) for s in trace.read_text().splitlines()]
    return {
        **summarize(tasks, outputs, checklist, batch),
        "source_trace_sha256": sha256_file(source),
        "extraction_trace_sha256": sha256_file(trace),
        "execution_verification_sha256": sha256_file(proof),
        "query_checklist_sha256": sha256_file(checklist_path),
        "AI_review_batch_sha256": sha256_file(batch_path),
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    write_json(args.output, verify(Path.cwd()))
