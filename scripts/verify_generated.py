"""Independent raw-input, token-budget, output decoding, and exact-agreement verification."""

import argparse
import hashlib
import itertools
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from transformers import AutoTokenizer

from ace_pruningrag.artifacts import read_json, sha256_file, write_json
from ace_pruningrag.dataset import iter_records, verify_dataset
from ace_pruningrag.evidence import web_chunks
from ace_pruningrag.retrieval import bm25_rank


def verify(root: Path, run: Path) -> dict:
    manifest = read_json(run / "manifest.json")
    config = manifest["config"]
    summary = read_json(run / "summary.json")
    assert sha256_file(run / "predictions.jsonl") == manifest["trace_sha256"]
    tokenizer = AutoTokenizer.from_pretrained(
        root / config["generator"]["directory"], local_files_only=True, trust_remote_code=False
    )
    records = {
        r.interaction_id: r
        for r in itertools.islice(
            iter_records(verify_dataset(manifest["dataset"], root)), config["limit"]
        )
    }
    assert list(records) == manifest["query_ids"]
    expected_runtime = {
        "transformers": "4.57.3",
        "huggingface_hub": "0.36.0",
        "tokenizers": "0.22.1",
        "safetensors": "0.6.2",
        "sentencepiece": "0.2.1",
    }
    assert all(manifest["runtime"][key] == value for key, value in expected_runtime.items())
    assert manifest["runtime"]["gpus"] and manifest["runtime"]["cuda"]
    assert config["generator"]["dtype"] == "float32"
    assert summary["numerical_diagnostic"] == {
        "dtype": "float32",
        "all_parameters_finite": True,
        "per_step_scores_guarded": True,
    }
    rows = [json.loads(line) for line in (run / "predictions.jsonl").read_text().splitlines()]
    assert len(rows) == len(records) * len(config["policies"])
    assert not all(row["output_ids"] and set(row["output_ids"]) == {0} for row in rows)
    seen = set()
    groups = defaultdict(list)
    for row in rows:
        pair = (row["interaction_id"], row["policy"])
        assert pair not in seen
        seen.add(pair)
        assert row["policy"] in config["policies"]
        record = records[row["interaction_id"]]
        q = record.inference_input()
        assert row["query"] == q.query and row["query_time"] == q.query_time
        pool = bm25_rank(q.query, web_chunks(q, config["chunk_words"]))[: config["candidate_limit"]]
        original = {e.evidence_id: e.as_dict() for e, _ in pool}
        # Current original daily-price probes end Feb 28, before all 50 question dates.
        assert row["actual_source_calls"] == {"web": 1, "finance": 0}
        assert row["candidate_ids"] == [e.evidence_id for e, _ in pool]
        assert row["actual_llm_calls"] == 1
        assert not any(key in row for key in ("answer", "domain", "split", "alt_ans"))
        assert len(row["selected"]) <= config["max_items"]
        assert len({e["evidence_id"] for e in row["selected"]}) == len(row["selected"])
        for e in row["selected"]:
            assert e == original[e["evidence_id"]]
            page = q.search_results[e["page_index"]]
            assert page[e["field"]][e["char_start"] : e["char_end"]] == e["content"]
        context = "\n\n".join(
            f"[{e['evidence_id']}] web "
            f"{e['source_url'] or 'page:' + str(e['page_index'])}\n{e['content']}"
            for e in sorted(row["selected"], key=lambda e: e["evidence_id"])
        )
        msg = [
            {"role": "system", "content": config["system_prompt"]},
            {
                "role": "user",
                "content": (
                    f"Question timestamp: {q.query_time}\nQuestion: {q.query}\n"
                    f"<evidence>\n{context}\n</evidence>\nAnswer:"
                ),
            },
        ]
        assert (
            hashlib.sha256(json.dumps(msg, ensure_ascii=False).encode()).hexdigest()
            == row["prompt_sha256"]
        )
        ids = tokenizer.apply_chat_template(msg, tokenize=True, add_generation_prompt=True)
        assert len(ids) == row["input_tokens"]
        assert len(row["output_ids"]) == row["output_tokens"] <= config["max_new_tokens"]
        assert row["input_tokens"] + row["output_tokens"] <= config["total_tokens"]
        assert row["input_tokens"] + config["max_new_tokens"] <= config["total_tokens"]
        assert (
            tokenizer.decode(row["output_ids"], skip_special_tokens=True).strip()
            == row["prediction"]
        )
        normalized = row["prediction"].strip().casefold()
        exact = any(normalized == answer.strip().casefold() for answer in record.answers)
        abstained = normalized in {
            "i don't know",
            "i don't know.",
            "i do not know",
            "i do not know.",
        }
        outcome = (
            "abstained" if abstained else "exact_agreement" if exact else "needs_semantic_review"
        )
        assert row["evaluation"] == {
            "exact_agreement": exact,
            "abstained": abstained,
            "outcome": outcome,
        }
        assert all(
            math.isfinite(row[key]) and row[key] >= 0
            for key in ("generation_seconds", "retrieval_seconds")
        )
        assert row["plan"]["total_budget"] == config["total_tokens"]
        assert row["plan"]["allocations"] == [["web", row["plan"]["evidence_budget"]]]
        assert (
            row["plan"]["evidence_budget"] + row["plan"]["reserved_tokens"]
            == config["total_tokens"]
        )
        groups[row["policy"]].append(row)
    for policy, group in groups.items():
        reported = summary["policies"][policy]
        assert len(group) == config["limit"]
        assert reported["outcomes"] == dict(Counter(r["evaluation"]["outcome"] for r in group))
        assert reported["exact_agreement_rate"] == sum(
            r["evaluation"]["exact_agreement"] for r in group
        ) / len(group)
        assert reported["abstention_rate"] == sum(
            r["evaluation"]["abstained"] for r in group
        ) / len(group)
        for field in ("input_tokens", "output_tokens", "generation_seconds", "retrieval_seconds"):
            assert math.isclose(reported["mean_" + field], statistics.mean(r[field] for r in group))
        assert reported["maximum_total_tokens"] == max(
            r["input_tokens"] + r["output_tokens"] for r in group
        )
        assert reported["semantic_accuracy"] is None and reported["unsupported_claim_rate"] is None
    assert summary["actual_llm_calls"] == len(rows)
    assert (
        summary["actual_web_retrieval_calls"] == len(rows) and summary["actual_finance_calls"] == 0
    )
    assert summary["published_baseline_reproduced"] is False
    return {
        "status": "independently_verified",
        "queries": len(records),
        "generated_answers": len(rows),
        "actual_llm_calls": len(rows),
        "maximum_reserved_tokens": max(r["input_tokens"] + config["max_new_tokens"] for r in rows),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = verify(args.root, args.run)
    if args.output:
        write_json(args.output, result)
    print(json.dumps(result, indent=2))
