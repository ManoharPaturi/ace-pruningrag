"""Validate and preserve an exported review against the generated trace."""

import argparse
import json
from pathlib import Path

from ace_pruningrag.generated_reviews import import_generated_review

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(import_generated_review(args.export, args.predictions, args.output), indent=2))
