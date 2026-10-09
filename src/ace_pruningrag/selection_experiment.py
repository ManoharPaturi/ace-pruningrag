"""Real-input engineering comparison with lexical proxies, not relevance annotations."""

import json
import platform
import sys
from itertools import combinations, islice
from pathlib import Path

from .artifacts import read_json, sha256_file, write_json
from .dataset import iter_records, verify_dataset
from .evidence import web_chunks
from .retrieval import bm25_rank, terms
from .selection import Candidate, SelectionProblem, render_context

STOPWORDS = frozenset(
    (
        "a an and are as at be by did do does for from how in is it of on or the to "
        "was were what when where which who with"
    ).split()
)
METHODS = ("top_k", "mmr", "coverage", "joint", "exact")


def selection_smoke(config_path: Path, root: Path, output: Path) -> dict:
    from tokenizers import Tokenizer

    config = read_json(config_path)
    if (
        config["scope"] != "lexical_selection_engineering_smoke"
        or not 1 <= config["pool_size"] <= 14
    ):
        raise ValueError("expected lexical smoke with at most 14 candidates")
    if config["limit"] < 1:
        raise ValueError("limit must be positive")
    asset = config["assets"][0]
    tokenizer_path = root / asset["local_path"]
    if sha256_file(tokenizer_path) != asset["sha256"]:
        raise ValueError("tokenizer checksum mismatch; run fetch-selection")
    tokenizer = Tokenizer.from_file(str(tokenizer_path))

    # Count every provenance header and separator in the rendered evidence context.
    def cost(selected):
        return len(tokenizer.encode(render_context(selected), add_special_tokens=False).ids)

    dataset_config = read_json(root / config["dataset_config"])
    dataset = verify_dataset(dataset_config, root)
    output.mkdir(parents=True, exist_ok=False)
    query_ids = []
    counts = {method: [] for method in METHODS}
    gaps = []
    with (output / "traces.jsonl").open("x", encoding="utf-8") as stream:
        for record in islice(iter_records(dataset), config["limit"]):
            query = record.inference_input()
            ranked = bm25_rank(query.query, web_chunks(query, config["chunk_words"]))[
                : config["pool_size"]
            ]
            requirements = tuple(sorted(set(terms(query.query)) - STOPWORDS)) or ("__no_terms__",)
            maximum = max((score for _, score in ranked), default=0) or 1
            candidates = [
                Candidate(
                    item.evidence_id,
                    item.content,
                    item.source_kind,
                    item.source_url or f"page:{item.page_index}",
                    score / maximum,
                    tuple(float(term in set(terms(item.content))) for term in requirements),
                )
                for item, score in ranked
            ]
            term_sets = {item.evidence_id: set(terms(item.content)) for item in candidates}
            similarities = {}
            for a, b in combinations(sorted(candidates, key=lambda i: i.evidence_id), 2):
                left, right = term_sets[a.evidence_id], term_sets[b.evidence_id]
                similarities[(a.evidence_id, b.evidence_id)] = len(left & right) / max(
                    1, len(left | right)
                )
            problem = SelectionProblem(
                candidates,
                requirements,
                (),
                similarities,
                {},
                cost,
                config["context_tokens"],
                config["max_items"],
            )
            results = {}
            for method in METHODS:
                selected = problem.select(method)
                tokens = problem.context_cost(selected)
                counts[method].append(tokens)
                results[method] = {
                    "selected_ids": [item.evidence_id for item in selected],
                    "context_tokens": tokens,
                    "objective": problem.objective(selected),
                    "components": problem.components(selected),
                }
            gaps.append(results["exact"]["objective"] - results["joint"]["objective"])
            query_ids.append(query.interaction_id)
            stream.write(
                json.dumps(
                    {
                        "interaction_id": query.interaction_id,
                        "query": query.query,
                        "query_time": query.query_time,
                        "proxy_requirements": requirements,
                        "groups": [],
                        "conflicts": [],
                        "candidates": [
                            {
                                "evidence": item.as_dict(),
                                "relevance": candidate.relevance,
                                "support": candidate.support,
                            }
                            for (item, _), candidate in zip(ranked, candidates, strict=True)
                        ],
                        "results": results,
                        "prediction": None,
                        "llm_calls": 0,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    summary = {
        "status": "selection_engineering_smoke_completed",
        "queries": len(query_ids),
        "methods": list(METHODS),
        "budget_tokens": config["context_tokens"],
        "tokenizer": config["tokenizer"],
        "maximum_context_tokens": {
            method: max(values, default=0) for method, values in counts.items()
        },
        "maximum_joint_objective_gap": max(gaps, default=0),
        "answer_accuracy": None,
        "evidence_completeness": None,
        "published_baseline_reproduced": False,
        "llm_calls": 0,
        "limitations": [
            "Engineering smoke on first file-order queries; no held-out quality evaluation.",
            "Query-term occurrence is a lexical proxy, not evidence requirement support.",
            "No predicted true requirement groups or conflicts: both features disabled.",
            "Exact search optimizes this experimental objective, not gold evidence quality.",
            "BGE tokenizer counts evidence including provenance; generator prompt overhead absent.",
            "Web-only real pool; API joint selection is currently unit-tested only.",
        ],
    }
    write_json(output / "summary.json", summary)
    write_json(
        output / "manifest.json",
        {
            "config": config,
            "config_sha256": sha256_file(config_path),
            "dataset": dataset_config,
            "query_ids": query_ids,
            "trace_sha256": sha256_file(output / "traces.jsonl"),
            "python": sys.version,
            "platform": platform.platform(),
            "source_sha256": {
                str(path.relative_to(root)): sha256_file(path)
                for path in sorted((root / "src/ace_pruningrag").glob("*.py"))
            },
        },
    )
    return summary
