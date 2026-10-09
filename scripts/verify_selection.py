"""Recompute provenance, token counts, proxy features, and exact objective optimum."""

import argparse
import itertools
import json
import math
import re
from pathlib import Path

from tokenizers import Tokenizer

from ace_pruningrag.artifacts import read_json, sha256_file
from ace_pruningrag.dataset import iter_records, verify_dataset
from ace_pruningrag.evidence import web_chunks
from ace_pruningrag.retrieval import bm25_rank


def verify(root: Path, run: Path) -> dict:
    manifest = read_json(run / "manifest.json")
    config = manifest["config"]
    traces = run / "traces.jsonl"
    assert sha256_file(traces) == manifest["trace_sha256"]
    dataset = verify_dataset(manifest["dataset"], root)
    asset = config["assets"][0]
    assert sha256_file(root / asset["local_path"]) == asset["sha256"]
    tokenizer = Tokenizer.from_file(str(root / asset["local_path"]))
    records = itertools.islice(iter_records(dataset), config["limit"])
    contexts = 0
    ids = []
    with traces.open(encoding="utf-8") as stream:
        for record, line in itertools.zip_longest(records, stream):
            assert record is not None and line is not None
            trace = json.loads(line)
            query = record.inference_input()
            assert (trace["interaction_id"], trace["query"], trace["query_time"]) == (
                query.interaction_id,
                query.query,
                query.query_time,
            )
            assert trace["prediction"] is None and trace["llm_calls"] == 0
            assert not any(key in trace for key in ("answer", "domain", "split", "alt_ans"))
            assert trace["groups"] == [] and trace["conflicts"] == []
            ids.append(query.interaction_id)
            ranked = bm25_rank(query.query, web_chunks(query, config["chunk_words"]))[
                : config["pool_size"]
            ]
            assert [row["evidence"] for row in trace["candidates"]] == [
                e.as_dict() for e, _ in ranked
            ]
            maximum = max((score for _, score in ranked), default=0) or 1
            items = {}
            for (evidence, score), row in zip(ranked, trace["candidates"], strict=True):
                assert row["relevance"] == score / maximum
                words = set(re.findall(r"\w+", evidence.content.casefold()))
                assert row["support"] == [
                    float(term in words) for term in trace["proxy_requirements"]
                ]
                page = query.search_results[evidence.page_index]
                assert (
                    page[evidence.field][evidence.char_start : evidence.char_end]
                    == evidence.content
                )
                row["reference"] = evidence.source_url or f"page:{evidence.page_index}"
                items[evidence.evidence_id] = row

            def evaluate(selected, items=items, requirements=tuple(trace["proxy_requirements"])):
                assert len(selected) == len(set(selected)) and len(selected) <= config["max_items"]
                chosen = [items[identity] for identity in sorted(selected)]
                context = "\n\n".join(
                    f"[{row['evidence']['evidence_id']}] web "
                    f"{row.get('reference')}"
                    f"\n{row['evidence']['content']}"
                    for row in chosen
                )
                cost = len(tokenizer.encode(context, add_special_tokens=False).ids)
                coverage = sum(
                    max((row["support"][i] for row in chosen), default=0)
                    for i in range(len(requirements))
                ) / len(requirements)
                relevance = sum(row["relevance"] for row in chosen) / config["max_items"]
                redundancy = 0
                for a, b in itertools.combinations(chosen, 2):
                    left = set(re.findall(r"\w+", a["evidence"]["content"].casefold()))
                    right = set(re.findall(r"\w+", b["evidence"]["content"].casefold()))
                    redundancy += len(left & right) / max(1, len(left | right))
                redundancy /= max(1, config["max_items"] * (config["max_items"] - 1) / 2)
                return cost, 0.2 * relevance + 0.6 * coverage - 0.1 * redundancy

            exact_best = 0.0
            for size in range(config["max_items"] + 1):
                for subset in itertools.combinations(items, size):
                    cost, objective = evaluate(subset)
                    if cost <= config["context_tokens"]:
                        exact_best = max(exact_best, objective)
            assert set(trace["results"]) == {"top_k", "mmr", "coverage", "joint", "exact"}
            for method, result in trace["results"].items():
                cost, objective = evaluate(result["selected_ids"])
                assert cost == result["context_tokens"] <= config["context_tokens"]
                assert math.isclose(objective, result["objective"], abs_tol=1e-12)
                assert objective <= exact_best + 1e-12
                assert result["components"]["complementarity"] == 0
                assert result["components"]["conflict"] == 0
                if method == "exact":
                    assert math.isclose(objective, exact_best, abs_tol=1e-12)
                contexts += 1
    assert ids == manifest["query_ids"]
    summary = read_json(run / "summary.json")
    assert summary["queries"] == len(ids)
    assert summary["answer_accuracy"] is None and summary["evidence_completeness"] is None
    return {"status": "independently_verified", "queries": len(ids), "contexts": contexts}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.root, args.run), indent=2))
