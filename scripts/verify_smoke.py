"""Independently verify all trace spans, source IDs, and context limits in a real-data run."""

import argparse
import json
from itertools import islice
from pathlib import Path

from ace_pruningrag.artifacts import read_json, sha256_file
from ace_pruningrag.dataset import iter_records, verify_dataset


def verify(root: Path, run: Path) -> dict:
    manifest = read_json(run / "manifest.json")
    summary = read_json(run / "summary.json")
    config = manifest["config"]
    trace_path = run / "retrieval_traces.jsonl"
    if sha256_file(trace_path) != manifest["trace_sha256"]:
        raise ValueError("trace checksum mismatch")
    dataset = verify_dataset(manifest["dataset"], root)
    records = list(islice(iter_records(dataset), config["limit"]))
    traces = [json.loads(line) for line in trace_path.read_text().splitlines()]
    if len(traces) != len(records) or len(traces) != summary["queries"]:
        raise ValueError("trace count mismatch")
    if [row.interaction_id for row in records] != manifest["query_ids"]:
        raise ValueError("manifest query ID mismatch")
    for record, trace in zip(records, traces, strict=True):
        if trace["interaction_id"] != record.interaction_id:
            raise ValueError("trace query ID mismatch")
        if "answer" in trace or "alt_ans" in trace:
            raise ValueError("gold answers leaked into retrieval trace")
        if trace["prediction"] is not None or trace["llm_calls"] != 0:
            raise ValueError("smoke scope violated")
        if len(trace["selected"]) > config["top_k"]:
            raise ValueError("chunk budget exceeded")
        words = 0
        for evidence in trace["selected"]:
            page = record.raw["search_results"][evidence["page_index"]]
            original = page[evidence["field"]]
            if original[evidence["char_start"] : evidence["char_end"]] != evidence["content"]:
                raise ValueError("evidence does not match its original source span")
            if page["page_url"] != evidence["source_url"]:
                raise ValueError("source URL mismatch")
            count = len(evidence["content"].split())
            if count != evidence["word_count"]:
                raise ValueError("word count mismatch")
            words += count
        if words != trace["context_words"] or words > config["max_context_words"]:
            raise ValueError("context word budget mismatch")
    return {"status": "verified", "queries": len(traces), "checks": "source spans, IDs, budgets"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(json.dumps(verify(args.root.resolve(), args.run), indent=2))
