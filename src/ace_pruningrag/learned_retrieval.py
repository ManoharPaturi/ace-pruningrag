"""Bounded BGE dense/reranker smoke on the same original evidence pool."""

import json
import math
import platform
import statistics
import sys
import time
from itertools import islice
from pathlib import Path
from typing import Any

from .artifacts import read_json, sha256_file, write_json
from .assets import verify_asset
from .dataset import iter_records, verify_dataset
from .evidence import Evidence, web_chunks
from .retrieval import bm25_rank, select_context


def score_ranking(items: list[Evidence], scores: list[float]) -> list[tuple[Evidence, float]]:
    if len(items) != len(scores) or any(not math.isfinite(value) for value in scores):
        raise ValueError("model must return one finite score for each candidate")
    return sorted(zip(items, scores, strict=True), key=lambda pair: (-pair[1], pair[0].evidence_id))


class BGERetriever:
    def __init__(self, config: dict[str, Any], root: Path):
        import torch
        from transformers import AutoModel, AutoModelForSequenceClassification, AutoTokenizer

        if not torch.cuda.is_available():
            raise ValueError("learned smoke requires the selected remote CUDA environment")
        if config["precision"] != "float32":
            raise ValueError("this protocol requires float32; do not silently change precision")
        self.torch = torch
        self.config = config
        torch.manual_seed(config["seed"])
        self.encoder_device = "cuda:0"
        self.reranker_device = "cuda:1" if torch.cuda.device_count() > 1 else "cuda:0"
        encoder_path = root / config["models"]["encoder"]["directory"]
        reranker_path = root / config["models"]["reranker"]["directory"]
        self.encoder_tokenizer = AutoTokenizer.from_pretrained(
            encoder_path,
            local_files_only=True,
            trust_remote_code=False,
        )
        self.reranker_tokenizer = AutoTokenizer.from_pretrained(
            reranker_path,
            local_files_only=True,
            trust_remote_code=False,
        )
        self.encoder = (
            AutoModel.from_pretrained(
                encoder_path,
                local_files_only=True,
                trust_remote_code=False,
                torch_dtype=torch.float32,
                weights_only=True,
            )
            .to(self.encoder_device)
            .eval()
        )
        self.reranker = (
            AutoModelForSequenceClassification.from_pretrained(
                reranker_path,
                local_files_only=True,
                trust_remote_code=False,
                torch_dtype=torch.float32,
                weights_only=True,
            )
            .to(self.reranker_device)
            .eval()
        )
        self.max_encoder_observed = 0
        self.max_pair_observed = 0

    def embeddings(self, texts: list[str]):
        vectors = []
        for offset in range(0, len(texts), self.config["batch_size"]):
            batch = texts[offset : offset + self.config["batch_size"]]
            tokens = self.encoder_tokenizer(
                batch, padding=True, truncation=False, return_tensors="pt"
            )
            length = tokens["input_ids"].shape[1]
            self.max_encoder_observed = max(self.max_encoder_observed, length)
            if length > self.config["max_encoder_tokens"]:
                raise ValueError("candidate exceeds encoder length; refusing silent truncation")
            with self.torch.inference_mode():
                hidden = self.encoder(**tokens.to(self.encoder_device)).last_hidden_state[:, 0]
                vector = self.torch.nn.functional.normalize(hidden, p=2, dim=1)
                vectors.append(vector.detach().cpu())
        return self.torch.cat(vectors)

    def dense(self, query: str, items: list[Evidence]):
        if not items:
            return []
        vectors = self.embeddings([query, *(item.content for item in items)])
        scores = (vectors[1:] @ vectors[0]).tolist()
        return score_ranking(items, scores)

    def rerank(self, query: str, candidates: list[tuple[Evidence, float]]):
        items = [item for item, _ in candidates]
        scores = []
        for offset in range(0, len(items), self.config["batch_size"]):
            pairs = [
                [query, item.content] for item in items[offset : offset + self.config["batch_size"]]
            ]
            tokens = self.reranker_tokenizer(
                pairs, padding=True, truncation=False, return_tensors="pt"
            )
            length = tokens["input_ids"].shape[1]
            self.max_pair_observed = max(self.max_pair_observed, length)
            if length > self.config["max_pair_tokens"]:
                raise ValueError("pair exceeds reranker length; refusing silent truncation")
            with self.torch.inference_mode():
                logits = self.reranker(**tokens.to(self.reranker_device)).logits.view(-1)
                scores.extend(logits.detach().cpu().tolist())
        return score_ranking(items, scores)


def learned_smoke(config_path: Path, root: Path, output: Path) -> dict[str, Any]:
    config = read_json(config_path)
    if config["scope"] != "adapted_web_retrieval_smoke" or not 1 <= config["limit"] <= 25:
        raise ValueError("invalid learned smoke scope or query limit")
    for asset in config["assets"]:
        verify_asset(asset, root)
    dataset_config = read_json(root / config["dataset_config"])
    dataset = verify_dataset(dataset_config, root)
    output.mkdir(parents=True, exist_ok=False)
    engine = BGERetriever(config, root)
    trace_path = output / "retrieval_traces.jsonl"
    ids = []
    timing = {name: [] for name in ("bm25", "dense", "dense_reranked")}
    context_words = {name: [] for name in timing}
    with trace_path.open("x", encoding="utf-8") as stream:
        for record in islice(iter_records(dataset), config["limit"]):
            query = record.inference_input()
            candidates = web_chunks(query, config["chunk_words"])
            trace = {
                "interaction_id": query.interaction_id,
                "query": query.query,
                "candidate_count": len(candidates),
                "methods": {},
                "prediction": None,
            }
            start = time.perf_counter()
            lexical = bm25_rank(query.query, candidates)
            timing["bm25"].append(time.perf_counter() - start)
            start = time.perf_counter()
            dense = engine.dense(query.query, candidates)
            dense_seconds = time.perf_counter() - start
            timing["dense"].append(dense_seconds)
            start = time.perf_counter()
            refined = engine.rerank(query.query, dense[: config["dense_top_k"]])
            timing["dense_reranked"].append(dense_seconds + time.perf_counter() - start)
            for method, ranked in (
                ("bm25", lexical),
                ("dense", dense),
                ("dense_reranked", refined),
            ):
                selected = select_context(ranked, config["top_k"], config["max_context_words"])
                words = sum(item.word_count for item, _ in selected)
                context_words[method].append(words)
                trace["methods"][method] = {
                    "selected": [dict(item.as_dict(), score=score) for item, score in selected],
                    "context_words": words,
                    "retrieval_seconds": timing[method][-1],
                }
            stream.write(json.dumps(trace, ensure_ascii=False) + "\n")
            stream.flush()
            ids.append(query.interaction_id)
            print(f"Learned retrieval query {len(ids)}/{config['limit']} completed", flush=True)
    summary = {
        "status": "learned_retrieval_smoke_completed",
        "queries": len(ids),
        "scope": config["scope"],
        "models": config["models"],
        "precision": config["precision"],
        "mean_retrieval_seconds": {k: statistics.mean(v) for k, v in timing.items()},
        "mean_context_words": {k: statistics.mean(v) for k, v in context_words.items()},
        "max_encoder_tokens_observed": engine.max_encoder_observed,
        "max_pair_tokens_observed": engine.max_pair_observed,
        "llm_calls": 0,
        "answer_accuracy": None,
        "retrieval_recall": None,
        "published_baseline_reproduced": False,
        "limitations": [
            "Independent adapted web-only retrieval, not the released PruningRAG pipeline.",
            "200-word chunks and a 600-word limit; not the original token chunking protocol.",
            "Only five smoke queries; no supporting-evidence labels or answer-quality evaluation.",
            "Dense+reranker latency includes both stages; downloads and loading are excluded.",
        ],
    }
    write_json(output / "summary.json", summary)
    write_json(
        output / "manifest.json",
        {
            "config": config,
            "dataset": dataset_config,
            "query_ids": ids,
            "config_sha256": sha256_file(config_path),
            "trace_sha256": sha256_file(trace_path),
            "python": sys.version,
            "platform": platform.platform(),
            "source_sha256": {
                str(p.relative_to(root)): sha256_file(p)
                for p in sorted((root / "src/ace_pruningrag").glob("*.py"))
            },
        },
    )
    return summary
