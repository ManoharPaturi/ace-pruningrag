"""Independent budget/source-gating audit of planning-only traces."""

import argparse
import hashlib
import itertools
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from ace_pruningrag.artifacts import read_json, sha256_file
from ace_pruningrag.dataset import iter_records, verify_dataset


def verify(root: Path, output: Path) -> dict:
    manifest = read_json(output / "manifest.json")
    config = manifest["config"]
    trace = output / "plans.jsonl"
    assert sha256_file(trace) == manifest["trace_sha256"]
    caps = {item["name"]: item for item in config["capabilities"]}
    assert len(caps) == len(config["capabilities"])
    ids = []
    count = 0
    blocked = Counter()
    equivalent = 0
    records = itertools.islice(
        iter_records(verify_dataset(manifest["dataset"], root)), config["limit"]
    )
    with trace.open(encoding="utf-8") as stream:
        for record, line in itertools.zip_longest(records, stream):
            assert record is not None and line is not None
            row = json.loads(line)
            query = record.inference_input()
            assert row["interaction_id"] == query.interaction_id
            assert row["query"] == query.query and row["query_time"] == query.query_time
            assert not any(key in row for key in ("answer", "domain", "split", "alt_ans"))
            assert (
                row["actual_source_calls"]
                == row["actual_llm_calls"]
                == row["actual_context_tokens"]
                == 0
            )
            ids.append(query.interaction_id)
            date = datetime.strptime(query.query_time, "%m/%d/%Y, %H:%M:%S PT").date().isoformat()
            eligible = {
                name
                for name, cap in caps.items()
                if cap["available"] and (not cap["requires_as_of"] or cap["as_of_date"] == date)
            }
            assert [p["policy"] for p in row["plans"]] == config["policies"]
            equivalent += int(len({json.dumps(p["allocations"]) for p in row["plans"]}) == 1)
            for p in row["plans"]:
                assert (
                    p["query_id"] == query.interaction_id
                    and p["execution_status"] == "not_executed"
                )
                assert p["total_budget"] == config["total_budget_tokens"]
                assert p["reserved_tokens"] == config["reserved_tokens"]
                assert p["evidence_budget"] + p["reserved_tokens"] == p["total_budget"]
                allocations = dict(p["allocations"])
                assert len(allocations) == len(p["allocations"])
                assert all(type(t) is int and t > 0 for t in allocations.values())
                assert set(allocations) <= eligible
                assert sum(allocations.values()) <= p["evidence_budget"]
                if allocations:
                    assert sum(allocations.values()) == p["evidence_budget"]
                assert p["max_source_calls"] == len(allocations)
                if p["policy"] == "fixed_web":
                    assert set(allocations) <= {"web"}
                elif p["policy"] == "adaptive":
                    assert set(allocations) <= set(p["requested_hints"])
                for name, reason in p["blocked_hints"]:
                    assert name not in eligible
                    cap = caps.get(name)
                    expected = "capability_not_provisioned"
                    if cap:
                        expected = (
                            "unavailable"
                            if not cap["available"]
                            else "snapshot_date_unknown"
                            if cap["as_of_date"] is None
                            else "snapshot_date_mismatch"
                        )
                    assert reason == expected
                if p["policy"] == "adaptive":
                    blocked.update(name + ":" + reason for name, reason in p["blocked_hints"])
                count += 1
    assert ids == manifest["query_ids"]
    summary = read_json(output / "summary.json")
    assert (summary["queries"], summary["plans"], summary["equivalent_allocations"]) == (
        len(ids),
        count,
        equivalent,
    )
    assert summary["blocked_hint_counts"] == dict(blocked)
    assert summary["answer_accuracy"] is None and summary["quality_cost_tradeoff_measured"] is False
    assert summary["scientific_phase3_complete"] is False
    return {
        "status": "independently_verified",
        "queries": len(ids),
        "plans": count,
        "query_ids_sha256": hashlib.sha256(json.dumps(ids).encode()).hexdigest(),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.root, args.run), indent=2))
