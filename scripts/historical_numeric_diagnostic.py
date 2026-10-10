"""Prespecified pure numeric agreement, separate from semantic human verdicts."""

import argparse
import json
import math
import re
from collections import defaultdict
from pathlib import Path

from ace_pruningrag.artifacts import read_json, sha256_file, write_json

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    manifest = read_json(args.run / "manifest.json")
    assert sha256_file(args.run / "predictions.jsonl") == manifest["trace_sha256"]
    config = read_json(Path("configs/historical_routing.json"))
    assert manifest["config"] == config
    audit_path = Path("results/phase3/price_eligibility.json")
    assert sha256_file(audit_path) == config["eligibility_report_sha256"]
    audit = read_json(audit_path)
    prices = {
        r["interaction_id"]: r["evidence"]["close"] for r in audit["prior_close_preparations"]
    }
    groups = defaultdict(list)
    for line in (args.run / "predictions.jsonl").read_text().splitlines():
        row = json.loads(line)
        prediction = row["prediction"].strip()
        numeric = re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", prediction) is not None
        match = numeric and math.isclose(
            float(prediction), prices[row["interaction_id"]], rel_tol=0, abs_tol=1e-6
        )
        groups[row["policy"]].append(
            {
                "interaction_id": row["interaction_id"],
                "pure_numeric": numeric,
                "matches_price_field": match,
            }
        )
    write_json(
        args.output,
        {
            "scope": (
                "Prespecified pure numeric price-value diagnostic, not independent semantic review"
            ),
            "absolute_tolerance": 1e-6,
            "per_policy": {
                policy: {
                    "questions": len(rows),
                    "pure_numeric_predictions": sum(r["pure_numeric"] for r in rows),
                    "price_value_matches": sum(r["matches_price_field"] for r in rows),
                    "rows": rows,
                }
                for policy, rows in groups.items()
            },
        },
    )
