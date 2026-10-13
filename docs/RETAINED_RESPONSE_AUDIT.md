# Retained failed and superseded response audit

Updated 13 October 2026. All ten declared local Kaggle prediction-file paths are now covered by trace-bound AI assessments. Their 646 stored response records occupy eight distinct file hashes containing 620 records; 26 records are duplicated by a second download of the same superseded files. These counts describe stored records, not independent questions, model calls or semantic observations.

The accepted results remain **444 admitted response records**. Failed and superseded runs are excluded. See [the inventory contract](../configs/retained_audits.json) and [verification result](../results/version1/retained_trace_audit.json).

## Failed float16 generator

Every one of the 150 outputs is exactly 96 exclamation marks, with 96 repetitions of token ID zero. The pinned cached tokenizer vocabulary maps zero to `!`. The actual 50 questions request factual answers, not punctuation. All 150 question/timestamp/prompt-hash/full-selected-evidence/input-count tuples match the later accepted legacy inputs already source-reviewed.

These are AI-assessed incorrect nonanswers with a degeneration category. This establishes observable failure, not its numerical root cause: punctuation alone cannot prove NaNs, faulty weights or a particular library defect. The original summary reports float16 execution; the accepted run uses guarded float32. Preserve both artifacts and their distinctions. Failed outputs remain excluded from accepted accuracy calculations and the demo.

Private assessment: `runs/version1/excluded_float16-ai-audit-v1.json`, bound to trace hash `49e5f2264eb91ef4674b412791e0d2295b950c4647f41b81887421a1107b82a1`.

## Superseded regeneration and duplicate downloads

The superseded run's 18 initial responses and eight retries match their accepted counterparts across query identity/time, prediction, prompt hash, full selected evidence, token counts and raw output IDs. Its already reviewed judgments were reused only after those fields matched and the original source audits validated completely. The target audits bind separately to the superseded traces and record the original trace/audit hashes.

| Superseded trace | Correct within recorded interpretation | Incorrect | Uncertain | Abstained |
| --- | ---: | ---: | ---: | ---: |
| Initial 18 | 4 | 2 | 4 | 8 |
| Retry 8 | 5 | 0 | 2 | 1 |

The `regeneration-progress-v1` initial/retry downloads are byte-identical to `regeneration-output-v1`, so the same trace-bound assessments apply. Do not double-count the download copy. Field equivalence does not establish identical timing, model environment or numerical execution. The superseded run is still excluded; its currency ambiguities, wrong-date web answers and BLACW abstention stay visible.

Private assessments: `runs/version1/superseded_regeneration_initial-ai-audit-v1.json` and `superseded_regeneration_retry-ai-audit-v1.json`.

## Verification contract and reproduction

The verifier discovers all `predictions.jsonl` files under the declared local Kaggle directory and requires exact agreement with the inventory. It rejects changed trace hashes, incomplete reviews, unknown extra/missing paths and promotion of unadmitted runs. Review reuse rejects changed evidence text even if its ID is unchanged, changed query dates/token counts/output IDs, missing fields and incomplete source review.

Obtain the private traces and all declared review batches, then run from the repository root with a new output:

```bash
uv run --locked --no-editable python scripts/verify_retained_audits.py \
  --output runs/version1/retained-audit-reproduced.json
```

The compact result records per-trace validation, assessment hashes, acceptance status and reuse comparisons. Original private files are preserved. Tests exercise reuse safety and duplicate-independent accounting; all 147 local tests pass, along with Ruff lint/format and diff checks.

## Completion boundary

This closes the AI response audit for the **declared local prediction inventory**. It does not prove every possible remote kernel/log was recovered, independent human correctness, faithful baseline reproduction, cross-source scientific benefit, or completion of live inference and the final research deliverables. Accepted semantic results are unchanged. [Current-version completion audit](VERSION1_COMPLETION_AUDIT.md) retains those open requirements.
