# Current-version completion audit

Audit opened 12 October 2026. The user requested completion of the current version, checking every response and planning the next version. The approved five-phase roadmap and merged implementation define the scope; this audit does not replace their incomplete requirements with a smaller success criterion.

## Requirements and current evidence

| Requirement | Authoritative evidence | Audit result | Next action |
| --- | --- | --- | --- |
| Locked reproducible environment and genuine inputs | `uv.lock`, pinned configs, required CI, dataset/asset verifiers | Existing foundation verified; 180 local tests pass; required CI runs on every pushed PR head | Run required checks on final branch |
| Faithful original PruningRAG baseline | Original router/checkpoints, full API backing data and paper model/evaluator contract | Not achieved; upstream releases empty and `models/router` lookup returned 404 during fresh audit | Obtain original artifacts or keep adapted-only claims explicit; do not invent a reproduced baseline |
| Shared-budget five-selector implementation | Selection code, smoke traces and budget verifiers | Implemented; prior contexts were engineering smoke | Execute the separately scoped explicit-cohort comparison |
| Main complementary-evidence scientific hypothesis | Reviewed atomic support labels, genuine cross-source cases, source-only controls | Not achieved; current real candidate pools are web-only and groups/conflicts are disabled | Retain this limitation; build genuine cross-source evaluation |
| Explicit prospective-cohort generation | Frozen packet/config/IDs, 250 requests, GPU traces | Runner, tokenizer preflight and 250 real generations complete; all outputs reconstructed | AI source review complete; independent review still required |
| Source routing and bounded reliability | Historical runs, independent verifiers, source/time/price-field checks | Narrow six-case implementation verified; general source/claim verification absent | Audit old and new responses; preserve scope and negative outcomes |
| Check every response | Per-answer audit records bound to exact prediction/prompt/evidence | All 444 admitted records AI source-audited; declared failed/superseded local outputs separately audited and excluded from results | Keep the completed AI audit distinct from independent human review |
| Independent human annotation and semantic evaluation | Attested reviewer exports matched to frozen traces | First-50 development review exists; prospective evidence and newer answer review unresolved | Preserve missing/uncertain status; AI review cannot satisfy the independent-human gate |
| Final paired metrics, costs and report | Completed experiment outputs, scoring definitions, uncertainty calculations | Partially implemented; full evaluated comparison incomplete | Separate literal agreement, AI judgments, human labels, coverage and costs |
| FastAPI/Next.js cited demo | Running app, API/data flow and evidence-linked answers | Explorer, production build and browser-to-GPU execution verified; durable restart recovery demonstrated | Complete adaptive multi-source execution and general claim verification |
| Next-version plan | Prioritized milestones, contracts, promotion criteria | Priorities updated from complete accepted-output audit; scientific promotion gates retained | Finalize around actual results, not expected improvements |
| Owner-only main merges | Protected branch and feature PR workflow | Preserved | Leave concrete checked PRs for owner merge |

## Current experiment contract

`configs/cohort_evaluation.json` freezes all 50 IDs from the admitted packet, five selectors, the existing generator/prompt, 12 candidates, five evidence items, greedy seed 42, 96 output tokens and 2,048 total tokens per request. There are at most 250 genuine generations. Gold answers and human support sets do not enter selector inputs.

This experiment uses the established query-term proxy objective with groups/conflicts disabled. Exact search optimizes that objective; it is not a gold-support oracle. Selector-only candidates are shared, and actual generator calls are counted separately. Preparation caches token costs across methods; per-method preparation timings are not unbiased standalone runtime benchmarks.

The user authorized autonomous checking. New review records produced by this assistant must be labeled AI-assisted, retain uncertainty, and remain separate from independent human exports. Running and inspecting this cohort exposes it; it must be treated as development/AI-reviewed data for future tuning and excluded from a newly frozen version-2 test set.

## Completion status

**The overall goal is not yet achieved.** Passing unit tests, submitting a GPU job, or drafting this document is not completion. Keep the active goal until the actual requirements are verified or genuine external blockers satisfy the blocked audit. Update this table as evidence arrives. The original roadmap's open research gates remain visible even when a deployable adapted implementation exists.

## Evidence added during this audit

The checkpoints below are chronological history. Earlier pending counts and test totals
are superseded by later checkpoints and the current requirements table above.

- Revalidated all 150 accepted first-50 development generations against the pinned inputs, prompt/output budgets, decoded token IDs and literal/abstention definitions. Maximum reserved request tokens remain 2,028.
- Revalidated the preserved 150 human review records. Full prediction coverage holds; the same two question-level correctness judgments remain uncertain.
- Began a separate AI-assisted source audit of those two uncertain questions, covering six policy responses. The Grand Slam question lacks event/category specificity; the Halloween evidence does not substantiate a three-film all-time viewing ranking. Original human labels remain untouched. This is not a completed audit of all 50 legacy questions.
- The explicit 250-request tokenizer preflight completed. The new private GPU job is submitted; remote execution and output verification remain pending. Do not interpret preparation as completed generation.

### Additional response audit findings

A second AI-assisted batch inspected six more distinct legacy questions (18 policy responses), bringing current AI review coverage to 8/50 legacy questions and 24/150 responses. The three original policy variants have identical prompts, selected evidence and predictions for these cases; each assessment remains bound to its own trace identity.

Observed failures include metric/unit confusion (assists per 48 minutes versus three-point attempts per game), entity/relation confusion (an acquisition target substituted for a CEO's former employer), ETF recommendations substituted for dated constituent performance, and speculative/truncated movie examples without supporting evidence. One Tenet answer is semantically supported despite literal punctuation differences.

The animated-film case exposes a different failure: supplied source text supports the model's Incredibles/2004 answer, but official ceremony records give Finding Nemo in 2004 and The Incredibles in 2005, honoring 2004 releases. Grounding in the supplied text and world correctness therefore need separate judgments. Sources: [Academy 2004 ceremony](https://www.oscars.org/oscars/ceremonies/2004), [Academy 2005 ceremony](https://www.oscars.org/oscars/ceremonies/2005). External audit evidence was not added to the original model's input and human labels were not changed.

A structural AI-audit validator rejects changed predictions, prompt/evidence bindings, duplicate reviews and false promotion to human validation. Its successful result proves binding and coverage only; it does not independently prove the assistant's semantic judgments. The full version-wide response audit remains incomplete; the legacy first-50 subset is now fully inspected as recorded below.


### Completed first-50 AI-assisted source audit (12 October)

All **50 distinct questions / 150 policy responses** now have assessments bound to exact predictions, prompt hashes and selected evidence IDs. Nine private batches are preserved under `runs/version1/`; compact [progress](../results/version1/legacy_review_progress.json) and [validation](../results/version1/legacy_ai_audit_validation.json) record their hashes and complete trace coverage. The validator also rejects abstention labels that contradict actual response text.

| AI assessment | Distinct questions | Policy responses |
| --- | ---: | ---: |
| Correct under the recorded interpretation | 12 | 36 |
| Incorrect | 15 | 45 |
| Uncertain / underspecified | 11 | 33 |
| Abstained | 12 | 36 |

These are assistant judgments, not independently validated semantic accuracy. All three policies had identical prompts, evidence and outputs for these cases, so the response counts are repeated variants rather than independent observations. Original human labels remain unchanged; differences require explicit adjudication rather than silent replacement.

Additional failure mechanisms include incomplete qualifying sets, missing comparison operands, selecting irrelevant page navigation numbers, franchise installment confusion, source facts from the wrong period, and non-exhaustive counts with an undefined universe. The F1 example satisfies the threshold for Schumacher but omits other qualifying drivers; this is an answer-completeness ambiguity. Tesla's Q1 EPS was recast as a fiscal-year value and omitted the quarterly series.

The NHL example violates the never-won-Hart constraint: official records identify Esposito as a winner. The WTA comparison goes the other direction: official records support Keys above Kasatkina at year-end 2023, but the selected model evidence lacks that comparison. External checks are retained in private review records and were not injected into generation. Sources: [NHL Hart winners](https://www.nhl.com/news/topic/nhl-awards/nhl-hart-memorial-trophy-winners-complete-list-287743272), [WTA Keys statistics](https://www.wtatennis.com/players/316959/madison-keys/stats), [WTA match notes](https://wtafiles.wtatennis.com/pdf/matchnotes/2025/2014_4.pdf).

The existing prospective-selector job was checked live and remains QUEUED with no failure message. No new generation result is claimed. The historical and regeneration traces have now been freshly verified and assessed below. General cross-source evaluation, independent human gates and product packaging still require completion.


### Historical and regeneration audits completed (12 October)

Fresh independent reconstruction passed for the six-question historical run (18 outputs; maximum reserved request 1,657 tokens) and admitted regeneration run (18 initial outputs plus eight real retries; maximum combined reserve 2,872 tokens). Verification checks the pinned dataset and price snapshot, dated row identity, reconstructed selections/prompts, decoded output IDs, eligibility, decisions and recorded costs. See [historical verification](../results/version1/historical_reverification.json), [regeneration verification](../results/version1/regeneration_reverification.json) and [AI audit bindings](../results/version1/historical_regeneration_ai_audit.json).

All **44 actual response records** have separate hash-bound AI assessments: 18 historical, 18 regeneration initial and eight retry outputs. The two initial runs match in every reviewed field. All eight retries match the same question's direct all-available control in prediction, prompt hash and selected evidence. These are six shared questions, not 44 independent cases.

| Run | Correct within pinned price-field contract | Incorrect | Uncertain monetary claim | Abstained |
| --- | ---: | ---: | ---: | ---: |
| Historical initial | 4 | 2 | 4 | 8 |
| Regeneration initial | 4 | 2 | 4 | 8 |
| Eight retries | 5 | 0 | 2 | 1 |

The two web-only substantive answers use wrong-period quotes: UBSI from July 2024 and WNW from October 2023 for a February 2024 query. API-based UBSI/WNW responses agree numerically with the dated rows but add dollars without established currency metadata, so full monetary claims remain uncertain. BLACW abstains even when the dated close is available. Correct entries refer to the exact pinned price-field contract; this review does not independently establish real-market currency, adjustment basis or snapshot accuracy.

The accepted current-run audit coverage is now **194 response records** (150 legacy plus 44 historical/regeneration), not 194 independent questions. The pending cohort's 250 responses are not included. Failed/superseded runs remain retained and excluded from accepted outcome claims; no blanket all-version review is asserted.


### Demo implementation checkpoint

A read-only FastAPI/Next.js evidence explorer is now implemented; see [demo setup](DEMO.md). Backend HTTP checks compared all 194 admitted responses to their trace records and checked fresh BM25 excerpt spans against pinned source text. Three additional tests exercise tampering, unavailable artifacts, field exclusion and API errors. Recorded answers are explicitly replays; live inference and the complete roadmap demo gate remain pending. The production build and browser→proxy→API→data→answer/retrieval flow now pass. Live generation remains pending.


### Cohort execution completed — 13 October

The existing GPU job is COMPLETE. All 250 outputs passed full reconstruction; [selector results](COHORT_SELECTOR_RESULTS.md) record exact protocol, costs and exploratory paired metrics. Source review has reached 95 responses across 19 questions, with 155 still pending. Literal abstention undercounts explicitly declining prose in the first inspected case; frozen diagnostics remain unchanged and AI semantic abstention is tracked separately with exact response spans. The overall goal remains incomplete.


The latest source-review checkpoint covers **289 accepted response records** (194 prior plus 95 cohort); 155 cohort records remain. The five room-area errors show a missing arithmetic verification path beyond the price-only verifier. Negative eligibility, answer type, comparison completeness and temporal/source conflicts also remain general reliability gaps. See the current selector report for retained failures and uncertainty.


### Reconciled handoff checkpoint — 13 October

The sixth saved cohort AI review batch also validates against the exact trace. Current coverage is **115/250 responses across 23/50 questions**, with **135 responses pending**. Verdict counts are 25 correct, 26 incorrect, 37 uncertain and 27 abstained. These are AI-assisted assessments, not independent human semantic labels. See `results/version1/cohort/ai_review_progress.json` and [the contributor handoff](PROJECT_HANDOFF.md) for the current continuation instructions. Earlier partial checkpoints remain historical.


### Accepted-output AI audit complete — current checkpoint

All 444 admitted records now have source-bound AI assessments, including all 250 cohort answers. [Completed cohort report](COHORT_RESPONSE_AUDIT.md) gives per-method counts and reproducible aggregation. The code/test checkpoint is 138 passing tests with the demo extra. This closes the accepted-output AI review task only. The overall roadmap remains incomplete; the open independent-human, cross-source, faithful-baseline, general reliability, final reporting and live-inference gates above remain required. Earlier incremental counts are historical.


### Answer-form checks added

[Query-only answer diagnostics](ANSWER_CHECKS.md) now run in the replay API/UI; all 444 original outputs remain unchanged. Twelve responses have observable form flags, including four identifiers returned as answers. Explicit rectangle arithmetic is unit-tested on fresh cases, but no admitted query meets its strict geometry contract. There are 141 passing local tests and the production web build passes. General entity/date/unit/claim verification, live inference and scientific validation remain open; these checks do not close those requirements.


### Declared retained-output audit complete

[Retained response audit](RETAINED_RESPONSE_AUDIT.md) now covers all ten declared local prediction-file paths: 646 stored records, 620 across eight unique file hashes. Failed float16 outputs are punctuation-only nonanswers; superseded regeneration assessments require full input equivalence before reuse. The accepted 444-record results are unchanged. There are 147 passing local tests. This closes the declared local AI audit, not remote-artifact completeness or independent scientific evaluation.


### Single-question GPU worker executed

[Live GPU worker](LIVE_GPU_WORKER.md) completed one actual pinned-model generation, separately from frozen experiments, and passed independent output/source/prompt reconstruction. It produced a supported director answer on an inspected development case with 1,302 reserved tokens. The browser submission/polling bridge, full latency accounting and general claim-level verification remain unfinished. Local tests now total 152.


### Browser-to-GPU path verified

[Live demo flow](LIVE_DEMO_FLOW.md) now submits, tracks, reconstructs and renders an actual GPU answer. API restart during RUNNING and browser refresh recovered the same request. The journal contains one job; one actual model call produced the supported actor answer. Tests now total 156. This closes the asynchronous fixed-web live-flow task, while adaptive multi-source generation, general claim verification and the open scientific/reporting requirements remain incomplete.


### Independent NLI component investigated

[Bounded textual-support diagnostic](NLI_SUPPORT_DIAGNOSTIC.md) executed and reconstructed all 1,105 cohort source/answer comparisons, with 69 classifier forwards and zero new answer-generation calls. Sixteen long pairs were unscored. Raw entailment appears on 27 AI-incorrect answer variants across seven questions, confirming that query requirements and support are separate gates. Acceptance remains disabled; general entity/date/unit/claim verification is not yet complete. Local tests now total 159.


### Partial query-contract checkpoint — 13 October

[Query contracts](QUERY_CONTRACTS.md) now retain explicit query requirements and flag
narrow asserted scope/date/price-field conflicts. Fresh adversarial synthetic tests
pass; all 444 admitted records were replayed with hashes and unchanged raw outputs.
The new scope checks add zero findings beyond 12 prior form warnings; 295 responses
remain unresolved and 137 match exact generator abstention. No automatic acceptance
is enabled. General entity/unit/claim verification and independent evaluation remain
open. Local validation now passes 163 tests.


### Blinded structured extraction submitted

[Structured query/source extraction](STRUCTURED_CLAIM_EXTRACTION.md) is implemented
and the private GPU job was observed RUNNING. It covers 50 question tasks and 336
deduplicated selected excerpt tasks without answers/reference labels in prompts.
Independent source/token/span/cost reconstruction and literal field comparison tools
are implemented. Actual completion, output verification and tuple audit remain pending.
All results keep automatic acceptance disabled; one proposed claim per source does not
establish complete evidence. Local tests now total 168.


### Structured extraction completed — retained negative result

The same GPU job completed 386 extraction sequences / 97 batch invocations. Every
input/output/span/cost binding reconstructed; [complete extraction audit](STRUCTURED_CLAIM_EXTRACTION.md)
retains 380 contract-invalid outputs and source-review rationales for all six valid
ones. No query proposal passes the contract; all 1,105 comparisons remain unresolved.
This closes execution and audit of this diagnostic, not general semantic verification.
Do not enable this extractor for acceptance. Enforced schema/span choices and measured
field-role binding remain next requirements. Local tests total 175; the submitted-code
commit passed all three required CI jobs. Earlier RUNNING status is historical.


### Closed-span extraction submitted

[Constrained extraction](CONSTRAINED_EXTRACTION.md) is implemented as a separate
experiment on the same blinded tasks and pinned generator. The private job was observed
QUEUED. A fixed JSON-key sequence and source-specific serialized span trie prevent
completed outputs from inventing fields; cap failures and semantic role errors remain
unresolved. Quote/Unicode tests use the actual enforcement parser rather than dropping
valid source text. Local validation passes 180 tests; remote completion and audit remain
pending. This does not close general verification or scientific evaluation.
