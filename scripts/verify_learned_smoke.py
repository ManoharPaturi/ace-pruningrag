"""Verify remote learned-retrieval traces against original pinned evidence and budgets."""

import argparse
import json
import math
from itertools import islice
from pathlib import Path

from ace_pruningrag.artifacts import read_json, sha256_file
from ace_pruningrag.dataset import iter_records, verify_dataset
from ace_pruningrag.evidence import web_chunks


def verify(root: Path, run: Path) -> dict:
    manifest = read_json(run / "manifest.json")
    summary = read_json(run / "summary.json")
    config = manifest["config"]
    traces_path = run / "retrieval_traces.jsonl"
    if sha256_file(traces_path) != manifest["trace_sha256"]:
        raise ValueError("trace checksum mismatch")
    if summary["models"] != config["models"] or summary["precision"] != config["precision"]:
        raise ValueError("model/precision mismatch")
    records = list(islice(iter_records(verify_dataset(manifest["dataset"], root)), config["limit"]))
    traces = [json.loads(line) for line in traces_path.read_text().splitlines()]
    if len(records) != len(traces) or len(traces) != summary["queries"]:
        raise ValueError("query count mismatch")
    if [r.interaction_id for r in records] != manifest["query_ids"]:
        raise ValueError("query ID mismatch")
    for record, trace in zip(records, traces, strict=True):
        if (
            trace["interaction_id"] != record.interaction_id
            or trace["query"] != record.raw["query"]
        ):
            raise ValueError("trace belongs to a different query")
        if trace["prediction"] is not None or any(k in trace for k in ("answer", "alt_ans")):
            raise ValueError("retrieval scope violated")
        candidates = {
            e.evidence_id: e for e in web_chunks(record.inference_input(), config["chunk_words"])
        }
        if trace["candidate_count"] != len(candidates):
            raise ValueError("candidate pool count mismatch")
        if set(trace["methods"]) != {"bm25", "dense", "dense_reranked"}:
            raise ValueError("unexpected retrieval method set")
        for result in trace["methods"].values():
            if len(result["selected"]) > config["top_k"]:
                raise ValueError("selected chunk count exceeds budget")
            selected_ids = [e["evidence_id"] for e in result["selected"]]
            if len(selected_ids) != len(set(selected_ids)):
                raise ValueError("duplicate evidence in context")
            words = 0
            for selected in result["selected"]:
                original = candidates.get(selected["evidence_id"])
                if original is None or any(selected[k] != v for k, v in original.as_dict().items()):
                    raise ValueError("selected evidence/provenance differs from raw source")
                if not math.isfinite(selected["score"]):
                    raise ValueError("nonfinite model score")
                words += original.word_count
            if words != result["context_words"] or words > config["max_context_words"]:
                raise ValueError("context word budget mismatch")
    return {
        "status": "verified",
        "queries": len(traces),
        "methods_per_query": 3,
        "scope": "provenance, candidate pool, model metadata, and context budgets",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(json.dumps(verify(args.root.resolve(), args.run), indent=2))
