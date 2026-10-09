# Evaluation protocol

Status: the Phase 1 retrieval smoke configuration is fixed. The publication evaluation contract is a draft, not a frozen experiment.

## Fixed pilot inputs

- Upstream implementation commit: `cfae4e46e73144b07df84d7760f759e39db54062`.
- RM3QA revision: `f56a19b1348559be73b7ae4e4626d0d2ed778b21`.
- Pilot variant: `RM3QA_5web.jsonl.bz2`; compressed SHA-256 is in `configs/dataset.json`.
- Pilot sample: first 25 records in release file order, with all selected query IDs recorded.
- Independent web-only BM25: `k1=1.5`, `b=0.75`, 200 whitespace words per chunk, at most 3 chunks and 600 whitespace words of context.
- Seed 42 is recorded; the smoke has no randomized decisions. Ties sort by evidence ID.
- No generator, API retriever, model router, dense model, reranker, or correctness judge runs in this pilot. Word limits are not token budgets.

This pilot tests data loading, deterministic retrieval, budget enforcement, and exact evidence provenance. Its latency and context counts are plumbing measurements, not paper performance results. Unit-test fixtures are synthetic and never enter research runs.

## Before publication evaluation is frozen

1. Resolve router artifacts, mock API service/backing data, and the target paper configuration. Record every compatibility change outside the untouched upstream checkout.
2. Assign and justify development/held-out splits. Preserve raw release split values; do not guess their meanings. Review entity/event overlap before tuning.
3. Select a generator and judge with exact checkpoint/revision or provider model identifiers, tokenizer, prompts, temperature, seed list, context limit, and API settings. Preserve the original evaluator separately from added metrics.
4. Lock query IDs and corpus/API snapshots. Ground truth stays in evaluation only. Inference receives query text/time and evidence; it never receives gold domain labels, answers, split assignments, or supporting-fact labels.
5. Annotate acceptable supporting-evidence sets and genuinely cross-source requirements. Raw RM3QA has no `supporting_facts`, `evidence_ids`, or API-result fields in this release. Do not compute evidence recall or completeness from answer-string matches as a substitute.
6. Lock identical candidate pools for selector experiments. Run end-to-end retrieval separately at matched total budgets, including routing, extraction, verification, re-retrieval, generation, and judging costs.
7. Tune weights and thresholds on development data only. Human-review annotation and judge errors independently; preserve reviewer records and negative outcomes.
8. Use paired comparisons over identical queries, report confidence intervals and all chosen seeds, and separate cross-source, single-source, missing-evidence, conflict, and temporal cases.

## Original outcome metrics

`score = (2 * correct + misses) / total - 1`

A correct answer contributes +1, an abstention contributes 0, and an incorrect answer contributes -1. The upstream evaluator checks abstentions, then exact case-insensitive matches, then uses a model judge for remaining answers. Preserve its specific rules when reproducing it. The independent `score_outcomes` helper only aggregates already evaluated labels; it does not replace the judge.

Accuracy, exact accuracy, hallucination rate, and miss rate must be reported together. Add citation support, completeness, and abstention coverage as separate metrics with validated labels. Unjudged outcomes cannot be scored.

## Artifacts

Each run retains configuration, raw-input checksum, source-file hashes, query IDs, runtime information, trace checksum, and limitations. Keep full traces and raw data in ignored `runs/` and `data/`; commit compact summaries and manifests under `results/`. Never replace an old run directory with a new experiment.
