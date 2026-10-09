"""Planning-only audit on genuine questions; no source execution or quality claims."""

import json
from collections import Counter
from itertools import islice
from pathlib import Path

from .artifacts import read_json, sha256_file, write_json
from .dataset import iter_records, verify_dataset
from .routing import Capability, route


def routing_smoke(config_path: Path, root: Path, output: Path) -> dict:
    config = read_json(config_path)
    if config["scope"] != "phase3_inference_only_routing_plan_smoke":
        raise ValueError("unexpected routing smoke scope")
    if type(config["limit"]) is not int or config["limit"] < 1:
        raise ValueError("positive integer query limit required")
    if config["policies"] != ["fixed_web", "all_available", "adaptive"]:
        raise ValueError("smoke requires the three declared policies")
    capabilities = tuple(Capability(**item) for item in config["capabilities"])
    dataset_config = read_json(root / config["dataset_config"])
    dataset = verify_dataset(dataset_config, root)
    output.mkdir(parents=True, exist_ok=False)
    blocked = Counter()
    eligible = {policy: Counter() for policy in config["policies"]}
    ids = []
    equivalent = 0
    with (output / "plans.jsonl").open("x", encoding="utf-8") as stream:
        for record in islice(iter_records(dataset), config["limit"]):
            query = record.inference_input()
            plans = [
                route(
                    query,
                    capabilities,
                    policy,
                    config["total_budget_tokens"],
                    config["reserved_tokens"],
                )
                for policy in config["policies"]
            ]
            ids.append(query.interaction_id)
            blocked.update(name + ":" + reason for name, reason in plans[-1].blocked_hints)
            equivalent += int(len({plan.allocations for plan in plans}) == 1)
            for plan in plans:
                eligible[plan.policy].update(name for name, _ in plan.allocations)
            stream.write(
                json.dumps(
                    {
                        "interaction_id": query.interaction_id,
                        "query": query.query,
                        "query_time": query.query_time,
                        "plans": [plan.as_dict() for plan in plans],
                        "actual_source_calls": 0,
                        "actual_llm_calls": 0,
                        "actual_context_tokens": 0,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    if not ids:
        raise ValueError("no questions loaded")
    result = {
        "status": "routing_plan_smoke_completed",
        "queries": len(ids),
        "plans": len(ids) * len(config["policies"]),
        "equivalent_allocations": equivalent,
        "blocked_hint_counts": dict(sorted(blocked.items())),
        "allocated_source_counts": {p: dict(c) for p, c in eligible.items()},
        "actual_source_calls": 0,
        "actual_llm_calls": 0,
        "answer_accuracy": None,
        "quality_cost_tradeoff_measured": False,
        "scientific_phase3_complete": False,
        "limitations": [
            "Planning-only audit; no source calls, generated answers, or latency savings measured.",
            "Keyword scores are heuristic hints, not probabilities or validated source labels.",
            "Unknown-date finance snapshots cannot be assumed aligned to historical question time.",
            "Blocked hints do not establish that web evidence cannot answer the question.",
            "Reserve is a planned allowance, not a verified generator prompt token count.",
            "Web eligibility does not certify every page is temporally valid.",
        ],
    }
    write_json(output / "summary.json", result)
    write_json(
        output / "manifest.json",
        {
            "config": config,
            "config_sha256": sha256_file(config_path),
            "dataset": dataset_config,
            "query_ids": ids,
            "trace_sha256": sha256_file(output / "plans.jsonl"),
            "source_sha256": {
                str(p.relative_to(root)): sha256_file(p)
                for p in sorted((root / "src/ace_pruningrag").glob("*.py"))
            },
        },
    )
    return result
