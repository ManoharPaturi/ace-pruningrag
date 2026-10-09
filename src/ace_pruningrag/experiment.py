"""Execute a bounded retrieval-only experiment on genuine pinned records."""

import json
import platform
import statistics
import subprocess
import sys
import time
from datetime import UTC, datetime
from itertools import islice
from pathlib import Path
from typing import Any

from .artifacts import read_json, sha256_file, write_json
from .dataset import iter_records, verify_dataset
from .evidence import web_chunks
from .retrieval import bm25_rank, select_context


def retrieval_smoke(config_path: Path, root: Path, output: Path) -> dict[str, Any]:
    config = read_json(config_path)
    if config["limit"] < 1:
        raise ValueError("limit must be positive")
    if config["scope"] != "web_only_offline_retrieval_no_generation_no_judge":
        raise ValueError("this runner supports only the declared retrieval smoke scope")
    dataset_config = read_json(root / config["dataset_config"])
    dataset = verify_dataset(dataset_config, root)
    output.mkdir(parents=True, exist_ok=False)
    durations = []
    context_words = []
    selected_counts = []
    candidate_counts = []
    ids = []
    with (output / "retrieval_traces.jsonl").open("x", encoding="utf-8") as stream:
        for record in islice(iter_records(dataset), config["limit"]):
            query = record.inference_input()
            start = time.perf_counter()
            candidates = web_chunks(query, config["chunk_words"])
            ranked = bm25_rank(query.query, candidates, config["bm25_k1"], config["bm25_b"])
            selected = select_context(ranked, config["top_k"], config["max_context_words"])
            duration = time.perf_counter() - start
            ids.append(query.interaction_id)
            durations.append(duration)
            words = sum(item.word_count for item, _ in selected)
            context_words.append(words)
            selected_counts.append(len(selected))
            candidate_counts.append(len(candidates))
            trace = {
                "interaction_id": query.interaction_id,
                "query": query.query,
                "query_time": query.query_time,
                "candidate_count": len(candidates),
                "selected": [dict(item.as_dict(), bm25_score=score) for item, score in selected],
                "context_words": words,
                "retrieval_seconds": duration,
                "prediction": None,
                "generation_status": "not_run",
                "llm_calls": 0,
            }
            stream.write(json.dumps(trace, ensure_ascii=False) + "\n")
    if not ids:
        raise ValueError("no records loaded")
    summary = {
        "status": "retrieval_smoke_completed",
        "experiment_id": config["experiment_id"],
        "queries": len(ids),
        "mean_candidates": statistics.mean(candidate_counts),
        "mean_selected_chunks": statistics.mean(selected_counts),
        "mean_context_words": statistics.mean(context_words),
        "maximum_context_words": max(context_words),
        "mean_retrieval_seconds": statistics.mean(durations),
        "llm_calls": 0,
        "api_cost_usd": 0,
        "answer_accuracy": None,
        "retrieval_recall": None,
        "complete_evidence": None,
        "token_count": None,
        "published_baseline_reproduced": False,
        "limitations": [
            "Web-only BM25 smoke; no API retrieval, generator, router, dense model, or reranker.",
            "First records in file order; not a representative quality evaluation.",
            "Whitespace words are a smoke-test limit, not model context tokens.",
            "Evidence completeness and retrieval relevance labels are not available.",
        ],
    }
    try:
        head = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except subprocess.CalledProcessError:
        head = None
    manifest = {
        "created_at_utc": datetime.now(UTC).isoformat(),
        "config": config,
        "dataset": dataset_config,
        "config_sha256": sha256_file(config_path),
        "source_sha256": {
            str(path.relative_to(root)): sha256_file(path)
            for path in sorted((root / "src/ace_pruningrag").glob("*.py"))
        },
        "git_head_at_run": head,
        "python": sys.version,
        "platform": platform.platform(),
        "query_ids": ids,
        "seed": config["seed"],
        "randomness": "none; deterministic rank ties use evidence ID",
        "trace_sha256": sha256_file(output / "retrieval_traces.jsonl"),
    }
    write_json(output / "summary.json", summary)
    write_json(output / "manifest.json", manifest)
    return summary
