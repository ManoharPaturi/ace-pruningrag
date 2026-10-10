"""Audit pinned real questions against immutable price availability before GPU runs."""

import argparse
from pathlib import Path

from ace_pruningrag.artifacts import read_json, write_json
from ace_pruningrag.price_eligibility import audit_price_eligibility

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    root = Path.cwd()
    result = audit_price_eligibility(
        read_json(root / "configs/dataset.json"), read_json(root / "configs/crag_prices.json"), root
    )
    write_json(args.output, result)
    print(result["counts"])
    print("Explicit-ticker expansion candidates:", result["expansion_candidate_count"])
