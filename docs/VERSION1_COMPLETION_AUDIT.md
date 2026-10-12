# Current-version completion audit

Audit opened 12 October 2026. The user requested completion of the current version, checking every response and planning the next version. The approved five-phase roadmap and merged implementation define the scope; this audit does not replace their incomplete requirements with a smaller success criterion.

## Requirements and current evidence

| Requirement | Authoritative evidence | Audit result | Next action |
| --- | --- | --- | --- |
| Locked reproducible environment and genuine inputs | `uv.lock`, pinned configs, required CI, dataset/asset verifiers | Existing foundation verified; new branch checks pending | Run required checks on final branch |
| Faithful original PruningRAG baseline | Original router/checkpoints, full API backing data and paper model/evaluator contract | Not achieved; upstream releases empty and `models/router` lookup returned 404 during fresh audit | Obtain original artifacts or keep adapted-only claims explicit; do not invent a reproduced baseline |
| Shared-budget five-selector implementation | Selection code, smoke traces and budget verifiers | Implemented; prior contexts were engineering smoke | Execute the separately scoped explicit-cohort comparison |
| Main complementary-evidence scientific hypothesis | Reviewed atomic support labels, genuine cross-source cases, source-only controls | Not achieved; current real candidate pools are web-only and groups/conflicts are disabled | Retain this limitation; build genuine cross-source evaluation |
| Explicit prospective-cohort generation | Frozen packet/config/IDs, 250 requests, GPU traces | New runner added; tokenizer preflight complete; private GPU job submitted | Verify all outputs against original inputs and decoding |
| Source routing and bounded reliability | Historical runs, independent verifiers, source/time/price-field checks | Narrow six-case implementation verified; general source/claim verification absent | Audit old and new responses; preserve scope and negative outcomes |
| Check every response | Per-answer audit records bound to exact prediction/prompt/evidence | New cohort outputs not yet available; broader audit unfinished | AI-assisted review of each output; do not label it independent human review |
| Independent human annotation and semantic evaluation | Attested reviewer exports matched to frozen traces | First-50 development review exists; prospective evidence and newer answer review unresolved | Preserve missing/uncertain status; AI review cannot satisfy the independent-human gate |
| Final paired metrics, costs and report | Completed experiment outputs, scoring definitions, uncertainty calculations | Partially implemented; full evaluated comparison incomplete | Separate literal agreement, AI judgments, human labels, coverage and costs |
| FastAPI/Next.js cited demo | Running app, API/data flow and evidence-linked answers | Not implemented | Build and verify after research flow stabilizes |
| Next-version plan | Prioritized milestones, contracts, promotion criteria | Draft below/linked; subject to final failure analysis | Finalize around actual results, not expected improvements |
| Owner-only main merges | Protected branch and feature PR workflow | Preserved | Leave concrete checked PRs for owner merge |

## Current experiment contract

`configs/cohort_evaluation.json` freezes all 50 IDs from the admitted packet, five selectors, the existing generator/prompt, 12 candidates, five evidence items, greedy seed 42, 96 output tokens and 2,048 total tokens per request. There are at most 250 genuine generations. Gold answers and human support sets do not enter selector inputs.

This experiment uses the established query-term proxy objective with groups/conflicts disabled. Exact search optimizes that objective; it is not a gold-support oracle. Selector-only candidates are shared, and actual generator calls are counted separately. Preparation caches token costs across methods; per-method preparation timings are not unbiased standalone runtime benchmarks.

The user authorized autonomous checking. New review records produced by this assistant must be labeled AI-assisted, retain uncertainty, and remain separate from independent human exports. Running and inspecting this cohort exposes it; it must be treated as development/AI-reviewed data for future tuning and excluded from a newly frozen version-2 test set.

## Completion status

**The overall goal is not yet achieved.** Passing unit tests, submitting a GPU job, or drafting this document is not completion. Keep the active goal until the actual requirements are verified or genuine external blockers satisfy the blocked audit. Update this table as evidence arrives. The original roadmap's open research gates remain visible even when a deployable adapted implementation exists.

## Evidence added during this audit

- Revalidated all 150 accepted first-50 development generations against the pinned inputs, prompt/output budgets, decoded token IDs and literal/abstention definitions. Maximum reserved request tokens remain 2,028.
- Revalidated the preserved 150 human review records. Full prediction coverage holds; the same two question-level correctness judgments remain uncertain.
- Began a separate AI-assisted source audit of those two uncertain questions, covering six policy responses. The Grand Slam question lacks event/category specificity; the Halloween evidence does not substantiate a three-film all-time viewing ranking. Original human labels remain untouched. This is not a completed audit of all 50 legacy questions.
- The explicit 250-request tokenizer preflight completed. The new private GPU job is submitted; remote execution and output verification remain pending. Do not interpret preparation as completed generation.

### Additional response audit findings

A second AI-assisted batch inspected six more distinct legacy questions (18 policy responses), bringing current AI review coverage to 8/50 legacy questions and 24/150 responses. The three original policy variants have identical prompts, selected evidence and predictions for these cases; each assessment remains bound to its own trace identity.

Observed failures include metric/unit confusion (assists per 48 minutes versus three-point attempts per game), entity/relation confusion (an acquisition target substituted for a CEO's former employer), ETF recommendations substituted for dated constituent performance, and speculative/truncated movie examples without supporting evidence. One Tenet answer is semantically supported despite literal punctuation differences.

The animated-film case exposes a different failure: supplied source text supports the model's Incredibles/2004 answer, but official ceremony records give Finding Nemo in 2004 and The Incredibles in 2005, honoring 2004 releases. Grounding in the supplied text and world correctness therefore need separate judgments. Sources: [Academy 2004 ceremony](https://www.oscars.org/oscars/ceremonies/2004), [Academy 2005 ceremony](https://www.oscars.org/oscars/ceremonies/2005). External audit evidence was not added to the original model's input and human labels were not changed.

A structural AI-audit validator rejects changed predictions, prompt/evidence bindings, duplicate reviews and false promotion to human validation. Its successful result proves binding and coverage only; it does not independently prove the assistant's semantic judgments. The full response audit remains incomplete.
