# ACE-PruningRAG: executed development experiments and open research gates

Generated from committed evidence. This is a reproducible research-status draft, not
an independently validated paper result or a completed five-phase roadmap.

## Abstract

ACE-PruningRAG investigates complementary evidence selection under a fixed request
budget. The implemented adapted pipeline completed 50 shared questions
across five selectors, producing 250 answers. All admitted
444 answer records have source-bound AI assessments;
those records include repeated policies and retries, not independent questions.
The selector experiment is web-only and uses lexical proxies rather than reviewed
support labels. Literal agreement and AI judgments do not establish a winning method.
Independent source/answer NLI diagnostics and structured extraction expose verification
failures. A browser-to-GPU demonstration survives API restart and page refresh. Faithful
original reproduction, genuine cross-source necessity, complete support labels, fresh
independent evaluation, general claim verification and full ablations remain incomplete.

## Hypothesis and implemented boundary

The hypothesis is that a set of evidence can answer requirements that its individual
items cannot. Test this by comparing shared candidate pools, generator and full model
budgets, and by running each source alone as a control. Different source names or low
text similarity do not establish complementarity.

The implemented selector supports relevance, coverage, redundancy and pair additions,
plus bounded exact search. In the executed cohort, coverage means query-term proxies;
groups/conflicts are disabled. Exact search optimizes that proxy objective, not a
reviewed support oracle. All 12 candidates come from pinned web snapshots, with at
most five excerpts selected. The generator is Qwen2.5-1.5B-Instruct revision
`989aa7980e4cf806f80c7fef2b1adb7bc71aa306`, float32 CUDA, greedy decoding, seed 42.
Each complete rendered request, including chat/provenance wrappers and the 96-token
output reserve, is capped at 2,048 tokens. The observed maximum is
2,036. This is an adapted generator/configuration; it
is not the original published PruningRAG baseline.

The originally frozen 50-question packet excluded recorded pilot IDs, duplicate
question text and overlapping canonical source pages. Inspecting and reviewing these
outputs converted this cohort into development data. Entity/event disjointness and
independent sealed-test status are not established. Do not tune on these questions
and continue to call them unseen evaluation.

## Selector outcomes

All values below are across 50 shared questions per method. Top-K selects by relevance;
MMR balances relevance and redundancy; coverage prioritizes the lexical requirement
proxy; joint uses the combined implemented objective; exact enumerates the bounded
candidate set. Their consumed token counts differ despite the same upper budget.

| Method | Literal matches | Exact abstentions | Input tokens | Output tokens |
| --- | ---: | ---: | ---: | ---: |
| top_k | 3 | 12 | 73,904 | 690 |
| mmr | 4 | 17 | 75,587 | 534 |
| coverage | 3 | 19 | 33,607 | 525 |
| joint | 4 | 18 | 75,094 | 557 |
| exact | 4 | 18 | 74,909 | 552 |

Literal matching is the frozen reference-string diagnostic, not semantic accuracy.
Exact abstention recognizes the frozen short form; AI review separately records four
prose abstentions. Question-level bootstrap comparisons use 10,000 resamples, seed 42.
MMR/joint/exact each differ from top-K by +0.02 literal agreement with exploratory
95% percentile interval [0, 0.06]; coverage differs by zero, interval [-0.06, 0.06].
No multiple-comparison adjustment or entity/event independence is established.
These results do not demonstrate grounded semantic improvement.

| Method | AI-correct | AI-incorrect | AI-uncertain | AI-abstained |
| --- | ---: | ---: | ---: | ---: |
| top_k | 9 | 17 | 11 | 13 |
| mmr | 9 | 13 | 10 | 18 |
| coverage | 5 | 15 | 11 | 19 |
| joint | 9 | 11 | 11 | 19 |
| exact | 9 | 12 | 10 | 19 |

These are complete source-bound AI development judgments, not independent human
accuracy labels. Total judgments are 41 correct, 68 incorrect, 53 uncertain and 88
abstained. Some factually plausible answers lack selected support; some follow a
source while missing the question's period, relation, answer type or completeness.
All original outputs and human exports remain separate. Coverage's lower context
cost and greater abstention cannot be promoted as better quality from these data.

The cohort used 333,101 input / 2,858 output tokens,
50 shared candidate retrievals and
250 generation calls. Model loading took
7.25 seconds; generation took
468.24 seconds. These exclude queue, acquisition, setup and
local reconstruction, and are not a production latency guarantee. Monetary cost is
not established; compute/tokens and call counts are the recorded costs. Assistant
AI-review token costs are outside the experiment's engine ledger and are not measured.
Zero pipeline judge calls does not mean those reviews had no model cost. These
per-run figures are not a reconciled whole-project bill; retained copies/superseded
outputs cannot be summed as new calls without provider execution identity.

## Reliability diagnostics and retained negative results

The historical closing-price path validates a narrow entity/date/field contract.
Eight actual retries reproduce their direct all-source control's context, prompt
and answer, adding generation cost without an observed answer change on six shared
questions. This is a development control, not representative routing performance.
Missing currency/adjustment metadata remains unresolved; no ticker-based assumption
fills those fields. General web claim verification is not established by this path.

The independent NLI diagnostic scored 1,089 source/answer pairs and
skipped 16 pairs over the full token cap, without truncation. It
used 69 classifier forward passes and zero answer
calls. At least one raw entailment occurs for 27 AI-incorrect answers: an all-time
count can follow a source but miss a decade question. The classifier and AI audit
have different targets; this is not classifier precision, recall or accuracy.
Raw text entailment must not automatically accept a QA response.

The unconstrained extractor completed 386 sequences
in 97 batched invocations, using
124,383 unpadded / 148,610 padded
input tokens and 17,991 output tokens. None of 50 question
proposals passes the required schema/span contract. Only six of 336 source proposals
passes it; AI review finds role/scope problems in five of those six. The remaining
historical water-level tuple does not establish a current answer or external truth.
All 1,105 question/source comparisons remain unresolved. Schema/span validation
exposes failures; it does not prove semantic roles. The separate constrained experiment
completed the same 386 tasks and passed complete reconstruction. Its completed
proposals include 385 structurally
valid objects and one retained capped invalid object, compared with six valid objects
in the control. Task identities, prompts, input counts and generator configuration
match; token filtering and its dependency overlay are changed factors. It used
16,198 output tokens, with the same 124,383 unpadded inputs.
Generation took 433.46 seconds and model loading
6.82 seconds; constraint preparation and
other setup are excluded, so these do not establish an end-to-end speed improvement.

None of 1,105 constrained literal comparisons has complete unambiguous alignment:
950 are unresolved and 155 have different explicit fields. All 50 question proposals
have AI role rationales; 48 are partial/misbound, one is a coherent minimal count core,
and one has underspecified query scope. These post-hoc categories are qualitative,
not calibrated accuracy. All 135 valid source proposals
still require role review. The partial source review covers
200 records / 181
distinct text/proposal pairs. Its coherent-claim judgments cover
10 records but only
8 distinct pairs; repeated copies are not
independent confirmation. Mixed facts, missing subjects, metadata and field-role
errors remain visible. These qualitative AI categories do not establish calibrated
accuracy or external truth. Structural success is not general support or complete
claim coverage; automatic acceptance remains disabled. See
[constrained reconstruction and review](CONSTRAINED_EXTRACTION.md).

The [versioned Unicode correction](UNICODE_SPAN_POLICY.md) preserves combining marks
in lexical words without normalizing source text. Full replay of 386 unchanged old
outputs rejects one truncated-name proposal that v1 permitted. This is a policy
revalidation, not corrected neural generation or semantic-role improvement. The
submitted v1 source, all outputs and all previous outcome counts remain intact.

Query-only form checks retain source-identifier answers and incomplete/unparsed lists
as warnings. The strict rectangle calculator requires explicit geometry and compatible
units; it is not silently applied to arbitrary room questions. Across all 444 admitted
outputs, 12 form warnings occur and narrow explicit scope/date checks add no additional
findings. Missing information remains unresolved rather than becoming a correction.

The retained inventory contains 10 stored trace paths,
646 stored records and
620 records across
8 distinct trace-file hashes. Only 444 are admitted.
Failed float16 punctuation outputs, superseded generations and duplicate downloads
remain separate from outcome counts. Every declared retained local answer trace has
AI audit coverage; this does not prove completeness of all possible remote artifacts.

## Product demonstration

The separate browser request returned `Gabriel Macht` using one actual model
call, 1,355 input / 5 output tokens and
1,451 reserved tokens. API restart during RUNNING and
browser refresh recovered the same journal job without resubmission. Observed request
creation to verified completion was 160.21
seconds, including queue/setup/transfer/reconstruction and restart recovery; these
components are not individually separated. This one inspected case verifies the
bounded fixed-web asynchronous path, not broad QA quality, adaptive multi-source
execution or general claim support. Raw answers, evidence provenance, replay/live
states and warnings remain visible.

## Completion requirements still open

| Phase | Executed evidence | Missing completion evidence |
| --- | --- | --- |
| 1: reproduction | Locked inputs, real GPU retrieval, adapted generation | Original checkpoints, full API backing and paper experiment contract |
| 2: complementary selection | Five selectors, 250 outputs and full AI audit | Independent requirements/support sets and cross-source/source-only controls |
| 3: adaptive retrieval | Deterministic routing and historical snapshot costs | Legitimate learned-router labels/calibration and fresh evaluation |
| 4: reliability | Bounded retries, NLI/extraction and retained failures | General semantic support, complete claims and measured regeneration benefit |
| 5: research/product | Asynchronous demo and evidence-bound report draft | Full ablations, fresh entity/event audit, independent metrics and final paper |

Independent human review cannot be manufactured by this assistant. Source-bound AI
review and robust engineering do not satisfy that gate.
The [completion audit](VERSION1_COMPLETION_AUDIT.md)
and [next-version plan](VERSION2_PLAN.md) retain the full objective and promotion gates.
Do not label these experiments publication-ready or report an unverified selector win.

## Reproduce this report

From the repository root, write to fresh output paths:

```sh
uv run --locked --no-editable python scripts/build_research_report.py \
  --output runs/report-reconstruction/RESEARCH_REPORT.md \
  --manifest runs/report-reconstruction/manifest.json
```

The manifest hashes every committed input artifact, the report and its renderer. It
establishes report provenance, not independent scientific truth. The underlying GPU
reconstruction/audit commands and limitations are documented in
[selector results](COHORT_SELECTOR_RESULTS.md), [retained audit](RETAINED_RESPONSE_AUDIT.md),
[NLI diagnostics](NLI_SUPPORT_DIAGNOSTIC.md),
[extraction diagnostics](STRUCTURED_CLAIM_EXTRACTION.md)
and [live-flow evidence](LIVE_DEMO_FLOW.md). Full private traces and review records are
required to independently reconstruct those runs; public summaries alone are weaker
than that reconstruction. Owner-only main merging remains unchanged.
