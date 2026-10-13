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

Five batches now cover **19 questions / 95 method responses; 155 responses remain**. See [review progress](../results/version1/cohort/ai_review_progress.json). Every assessment is bound to its actual prediction, prompt hash and selected evidence IDs; AI review remains separate from independent human review.

- Real Sociedad answers explicitly abstain because dated weekly evidence is missing. Four methods add an explanation around “I don't know,” which the frozen exact-string abstention metric does not recognize. AI review records an exact abstention span separately; the frozen experimental metric is preserved.
- Lille's four substantive answers give a weekly total without dated fixture support. Season aggregates and undated examples are insufficient; actual truth remains unresolved rather than being inferred from the reference.
- The YSL founder question receives a Gunna transfer rumor instead of a founder's latest album. Selected evidence names Young Thug as founder; the response fails entity binding and requested answer type. Coverage abstains.

The audit validator checks binding and coverage, not independent semantic truth. A prose abstention span must occur in the exact response, but presence alone does not prove the rest of the answer is harmless or correct; the reviewer must inspect the complete response.

## Remaining gates

Complete source review of all 250 actual responses, obtain independent review, assess genuine complete-support sets, audit entity/event overlap, and run cross-source/source-only controls. Groups/conflicts are disabled; query-term proxy coverage and exact optimization are not annotated support oracles. Keep these inspected questions out of a fresh version-2 held-out cohort.


### Review expansion: 19-question checkpoint

The current AI assessments comprise 21 correct under the recorded interpretation, 24 incorrect, 33 uncertain and 17 abstaining responses. These are method-level judgments across 19 shared questions, not 95 independent observations or validated accuracy. Binding validation covers all 95 exactly once.

The expanded inspection identifies concrete failures:

- All five selectors miss the rectangular room calculation: 17 × 66 = 1,122 m². Coverage prints an invalid equality; other methods give unrelated numbers.
- Coverage answers five Murray Grand Slams despite its selected text stating three Slams and two Olympic golds; it also substitutes 2024 for Rodrigo's explicitly reported 2022 award. These are observed degradations, not discarded cases.
- Top-K reverses Carolina's elimination into playoff qualification. Other methods return the old six-per-conference format instead of the requested current team identities.
- Apple Music answers give an artist rather than a song and mix a 2023 global annual list with a dated US daily-chart question.
- INDB's quoted capitalization lacks the question-date binding. Dam heights, production durations, sequel counts and actor film-role counts often lack a comparable second operand or an aligned counting definition.
- A coverage lake excerpt loses its explicit name antecedent; the crocodile answer requires living-reptile scope, while top-K wrongly classifies a blue whale as a reptile. The publishing question retrieves Us Weekly ownership for In Touch Weekly, leaving requested historical ownership and its premise unresolved.

The election question conflates winning the popular vote with winning the presidency. Several methods give an electoral total or an unsupported margin; top-K/joint reproduce an older selected popular-vote report. Final FEC totals imply a different margin (65,853,514 − 62,984,828 = 2,868,686). This is a reference/source conflict, not a reason to silently rewrite the frozen reference or supply external information to inference. [FEC 2016 results](https://www.fec.gov/documents/1889/federalelections2016.pdf).

Full source review is still incomplete. External audit checks are recorded separately, and the original generation trace and independent-human gates remain unchanged.


### Reconciled handoff checkpoint — 13 October

The sixth saved cohort AI review batch also validates against the exact trace. Current coverage is **115/250 responses across 23/50 questions**, with **135 responses pending**. Verdict counts are 25 correct, 26 incorrect, 37 uncertain and 27 abstained. These are AI-assisted assessments, not independent human semantic labels. See `results/version1/cohort/ai_review_progress.json` and [the contributor handoff](PROJECT_HANDOFF.md) for the current continuation instructions. Earlier partial checkpoints remain historical.
