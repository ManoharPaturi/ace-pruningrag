"""Shared web/API candidate pool and source-only request controls with full token costs."""

from itertools import combinations

from .claim_extraction import digest
from .evidence import web_chunks
from .generation import messages
from .retrieval import bm25_rank, terms
from .selection import Candidate, SelectionProblem
from .selection_experiment import STOPWORDS


def prepare_source_controls(query, api_evidence, config, tokenize, methods=("top_k", "joint")):
    if any(
        e.source_kind != "api" or e.interaction_id != query.interaction_id for e in api_evidence
    ):
        raise ValueError("source controls require API evidence bound to the same query")
    if type(config["candidate_limit"]) is not int or not 1 <= config["candidate_limit"] <= 14:
        raise ValueError("shared source-control pool must contain at most fourteen candidates")
    all_evidence = web_chunks(query, config["chunk_words"]) + list(api_evidence)
    if len({e.evidence_id for e in all_evidence}) != len(all_evidence):
        raise ValueError("source controls reject duplicate evidence identities")
    # Retrieve once, then filter the same pool. Do not compare separately changed pools.
    ranked = bm25_rank(query.query, all_evidence)[: config["candidate_limit"]]
    requirements = tuple(sorted(set(terms(query.query)) - STOPWORDS)) or ("__no_terms__",)
    maximum = max((score for _, score in ranked), default=0) or 1
    candidates = [
        Candidate(
            e.evidence_id,
            e.content,
            e.source_kind,
            e.source_url or f"page:{e.page_index}",
            score / maximum,
            tuple(float(term in set(terms(e.content))) for term in requirements),
        )
        for e, score in ranked
    ]
    by_id = {e.evidence_id: e.as_dict() for e, _ in ranked}
    term_sets = {c.evidence_id: set(terms(c.content)) for c in candidates}
    similarities = {}
    for a, b in combinations(candidates, 2):
        left, right = term_sets[a.evidence_id], term_sets[b.evidence_id]
        similarities[tuple(sorted((a.evidence_id, b.evidence_id)))] = len(left & right) / max(
            1, len(left | right)
        )

    def cost(items):
        return (
            len(tokenize(messages(query, items, config["system_prompt"])))
            + config["max_new_tokens"]
        )

    requests = {}
    for mode, kinds in (
        ("web_only", ("web",)),
        ("api_only", ("api",)),
        ("combined", ("web", "api")),
    ):
        pool = [c for c in candidates if c.source_kind in kinds]
        ids = {c.evidence_id for c in pool}
        problem = SelectionProblem(
            pool,
            requirements,
            (),
            {pair: value for pair, value in similarities.items() if set(pair) <= ids},
            {},
            cost,
            config["total_tokens"],
            config["max_items"],
        )
        for method in methods:
            selected = problem.select(method)
            msg = messages(query, selected, config["system_prompt"])
            encoded = tokenize(msg)
            if len(encoded) + config["max_new_tokens"] > config["total_tokens"]:
                raise ValueError("source control exceeds full prompt/output budget")
            requests[f"{mode}/{method}"] = {
                "mode": mode,
                "method": method,
                "messages": msg,
                "input_ids": encoded,
                "selected": [by_id[c.evidence_id] for c in selected],
                "candidate_ids": [c.evidence_id for c in pool],
                "full_reserved_tokens": len(encoded) + config["max_new_tokens"],
                "prompt_sha256": digest(msg),
                "proxy_requirements": list(requirements),
                "groups": [],
                "conflicts": [],
                "semantic_support_verified": False,
                "answer_acceptance_enabled": False,
            }
    return requests, {
        "shared_candidate_ids": [c.evidence_id for c in candidates],
        "shared_candidate_counts": {
            k: sum(c.source_kind == k for c in candidates) for k in ("web", "api")
        },
        "retrieval_pool_policy": "rank_union_once_then_filter_for_source_controls",
        "retrieval_score_is_semantic_support": False,
        "actual_answer_generation_calls": 0,
    }
