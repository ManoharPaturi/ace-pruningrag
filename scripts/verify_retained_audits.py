"""Account for every declared retained prediction trace without promoting excluded runs."""

import argparse
from pathlib import Path

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.response_audit import validate_ai_audits, verify_assessment_reuse


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/retained_audits.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    root = Path.cwd()
    config = read_json(args.config)
    expected = {entry["trace"] for entry in config["traces"]}
    if len(expected) != len(config["traces"]):
        raise ValueError("duplicate declared trace path")
    discovered = {str(p) for p in Path(config["discovery_root"]).rglob("predictions.jsonl")}
    if discovered != expected:
        raise ValueError(f"retained inventory differs: {sorted(discovered ^ expected)}")
    admitted = {
        e["path"]: e["sha256"] for e in read_json(root / "configs/demo.json")["runs"].values()
    }
    results = []
    unique = {}
    for entry in config["traces"]:
        trace = root / entry["trace"]
        if entry["trace"] in admitted:
            if (
                entry["acceptance"] != "admitted"
                or entry["trace_sha256"] != admitted[entry["trace"]]
            ):
                raise ValueError("admitted inventory differs from demo admission")
        elif entry["acceptance"] not in ("excluded", "superseded_excluded"):
            raise ValueError("unadmitted retained trace cannot be promoted")
        if sha256_file(trace) != entry["trace_sha256"]:
            raise ValueError(f"retained trace hash differs: {entry['name']}")
        audits = [root / name for name in entry["audits"]]
        validation = validate_ai_audits(audits, trace)
        if not validation["full_ai_response_audit_complete"]:
            raise ValueError(f"retained review incomplete: {entry['name']}")
        result = {
            "name": entry["name"],
            "acceptance": entry["acceptance"],
            "trace_sha256": entry["trace_sha256"],
            "audit_sha256": {p.name: sha256_file(p) for p in audits},
            "validation": validation,
        }
        if "reuse_source_trace" in entry:
            result["reuse"] = verify_assessment_reuse(
                root / entry["reuse_source_trace"],
                [root / name for name in entry["reuse_source_audits"]],
                trace,
            )
        unique.setdefault(entry["trace_sha256"], validation["response_count"])
        results.append(result)
    write_json(
        args.output,
        {
            "scope": config["scope"],
            "config_sha256": sha256_file(args.config),
            "trace_paths": len(results),
            "unique_trace_files": len(unique),
            "stored_response_records": sum(r["validation"]["response_count"] for r in results),
            "response_records_in_unique_trace_files": sum(unique.values()),
            "admitted_response_records": sum(
                r["validation"]["response_count"] for r in results if r["acceptance"] == "admitted"
            ),
            "all_declared_retained_responses_ai_audited": True,
            "independent_human_review": False,
            "excluded_runs_promoted": False,
            "traces": results,
            "limitations": [
                "Byte-identical downloads and repeated methods are not independent observations.",
                "Review equivalence does not verify runtime, timing or model numerical stability.",
                "Coverage is limited to declared local predictions, not every remote job or log.",
                "Structural validation does not establish AI semantic truth or human review.",
            ],
        },
    )


if __name__ == "__main__":
    main()
