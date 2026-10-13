"""Reproduce compact method diagnostics from private, provenance-bound AI assessments."""

import argparse
from pathlib import Path

from ace_pruningrag.artifacts import write_json
from ace_pruningrag.response_audit import summarize_ai_audits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, required=True)
    parser.add_argument("--audits", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    report = summarize_ai_audits(args.audits, args.trace)
    write_json(args.output, report)


if __name__ == "__main__":
    main()
