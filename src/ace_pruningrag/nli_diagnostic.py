"""Separate-model textual-support diagnostics; never a complete answer verifier."""

import hashlib
import json
import math


def answer_source_pairs(rows, max_pairs=1250):
    pairs = []
    seen = set()
    for row in rows:
        key = (row["interaction_id"], row["policy"])
        if key in seen:
            raise ValueError("duplicate response identity")
        seen.add(key)
        for evidence in row["selected"]:
            record = {
                "interaction_id": key[0],
                "policy": key[1],
                "evidence_id": evidence["evidence_id"],
                "query": row["query"],
                "query_time": row["query_time"],
                "premise": evidence["content"],
                "hypothesis": row["prediction"],
            }
            if not record["premise"].strip() or not record["hypothesis"].strip():
                raise ValueError("nonempty exact premise/answer required")
            record["pair_sha256"] = hashlib.sha256(
                json.dumps(record, sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest()
            pairs.append(record)
    if len(pairs) > max_pairs:
        raise ValueError("NLI comparison cap exceeded")
    return pairs


def diagnostic_record(pair, token_count, scores=None, cap=512):
    if type(token_count) is not int or token_count < 1:
        raise ValueError("positive pair token count required")
    result = {k: pair[k] for k in ("interaction_id", "policy", "evidence_id", "pair_sha256")}
    result.update(
        pair_tokens=token_count,
        answer_acceptance="not_established",
        factual_correctness_verified=False,
        query_completeness_verified=False,
        calibrated=False,
    )
    if token_count > cap:
        if scores is not None:
            raise ValueError("over-budget pair must not be scored or truncated silently")
        return dict(result, status="over_pair_budget_unscored")
    if (
        scores is None
        or len(scores) != 3
        or any(type(s) not in (int, float) or not math.isfinite(s) for s in scores)
    ):
        raise ValueError("three finite classifier logits required")
    labels = ("contradiction", "entailment", "neutral")
    return dict(
        result,
        status="model_textual_relation_only",
        logits=scores,
        model_label=labels[max(range(3), key=lambda i: scores[i])],
    )
