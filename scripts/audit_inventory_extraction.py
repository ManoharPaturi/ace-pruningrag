"""Audit all real inventory outputs only after full execution reconstruction."""

import argparse
import json
import runpy
from pathlib import Path

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.claim_extraction import extraction_tasks
from ace_pruningrag.inventory_audit import summarize


def audit(root, bundle, run, source, verification):
    reconstruct = runpy.run_path(str(root / "scripts/verify_inventory_extraction.py"))["verify"]
    proof = reconstruct(root, bundle, run, source)
    if read_json(verification) != proof:
        raise ValueError("inventory audit requires freshly reconstructed execution proof")
    tasks = extraction_tasks([json.loads(x) for x in source.read_text().splitlines()])
    output = run / "extractions.jsonl"
    records = [json.loads(x) for x in output.read_text().splitlines()]
    return {
        **summarize(tasks, records),
        "source_trace_sha256": sha256_file(source),
        "extraction_trace_sha256": sha256_file(output),
        "execution_verification_sha256": sha256_file(verification),
        "additional_model_calls": 0,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--source-trace", type=Path, required=True)
    p.add_argument("--verification", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise FileExistsError(a.output)
    write_json(a.output, audit(Path.cwd(), a.bundle, a.run, a.source_trace, a.verification))
