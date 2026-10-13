# Explicit-cohort selector run: verified exploratory results

Updated 13 October 2026. The private Kaggle kernel `ionrey/ace-pruningrag-prospective-selectors`, version 1, completed 50 frozen questions × five selectors = **250 actual generations**. All outputs passed independent reconstruction; AI-assisted source review is in progress. This is an adapted web-only development experiment, not independently human-validated research accuracy.

## Verified execution

[Verification](../results/version1/cohort/verification.json) reconstructs the exact frozen question IDs, original source spans, shared candidates, selections, prompt hashes, output decoding and budgets. The packet hash remains `324b5c35dc08ac43ce9c841f1a6a35086007badc8436b1d139f2fb01d3a80b33`. All requests reserve at most 2,036 tokens under the 2,048 cap, including 96 output tokens.

The run used 333,101 input tokens and 2,858 output tokens, with 50 shared candidate retrievals, 250 generation calls, zero finance calls and zero judge calls. Reported generation time is 468.24 seconds; model loading is 7.25 seconds. Runtime is the pinned Qwen2.5-1.5B-Instruct in float32 on Tesla T4. These timings describe this job, not a production latency guarantee. See [GPU summary](../results/version1/cohort/gpu_summary.json).

## Frozen literal diagnostics

| Method | Literal reference matches / 50 | Exact short-form abstentions / 50 | Input tokens | Output tokens |
| --- | ---: | ---: | ---: | ---: |
| Top-K | 3 | 12 | 73,904 | 690 |
| MMR | 4 | 17 | 75,587 | 534 |
| Coverage | 3 | 19 | 33,607 | 525 |
| Joint | 4 | 18 | 75,094 | 557 |
| Exact | 4 | 18 | 74,909 | 552 |

[Paired diagnostics](../results/version1/cohort/paired_metrics.json) use 10,000 question-level bootstrap samples, seed 42. MMR/joint/exact show a +0.02 literal-agreement difference versus top-K, with exploratory 95% percentile interval [0, 0.06]. Coverage shows 0 difference, interval [-0.06, 0.06]. No multiple-comparison adjustment or entity/event independence is established. These intervals do not demonstrate an improvement in grounded semantic answers.

All methods use the same upper budget and shared candidates; they need not consume identical tokens. Coverage uses one to four excerpts, while most other methods select five. Its lower cost and greater abstention need to be assessed together with actual support and answer completeness.

## Source review and scoring boundary

The first batch covers three questions / 15 method responses; **235 responses remain**. See [review progress](../results/version1/cohort/ai_review_progress.json). Every assessment is bound to its actual prediction, prompt hash and selected evidence IDs; AI review remains separate from independent human review.

- Real Sociedad answers explicitly abstain because dated weekly evidence is missing. Four methods add an explanation around “I don't know,” which the frozen exact-string abstention metric does not recognize. AI review records an exact abstention span separately; the frozen experimental metric is preserved.
- Lille's four substantive answers give a weekly total without dated fixture support. Season aggregates and undated examples are insufficient; actual truth remains unresolved rather than being inferred from the reference.
- The YSL founder question receives a Gunna transfer rumor instead of a founder's latest album. Selected evidence names Young Thug as founder; the response fails entity binding and requested answer type. Coverage abstains.

The audit validator checks binding and coverage, not independent semantic truth. A prose abstention span must occur in the exact response, but presence alone does not prove the rest of the answer is harmless or correct; the reviewer must inspect the complete response.

## Remaining gates

Complete source review of all 250 actual responses, obtain independent review, assess genuine complete-support sets, audit entity/event overlap, and run cross-source/source-only controls. Groups/conflicts are disabled; query-term proxy coverage and exact optimization are not annotated support oracles. Keep these inspected questions out of a fresh version-2 held-out cohort.
