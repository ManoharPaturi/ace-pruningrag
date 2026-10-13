# Next-version plan — priorities from completed accepted-output AI audit

The next version should address observed failure mechanisms rather than add features without evidence. The current system has reliable plumbing, but proxy support, limited source availability, conservative price-only verification and development-only evaluation constrain its research claims.

## Ordered milestones

| Milestone | Work | Promotion gate |
| --- | --- | --- |
| 1. Freeze a fresh evaluation extension | Exclude all prior pilot and current-cohort exposures; audit entity/event overlap; include single-source, cross-source, temporal, missing-evidence and comparable-conflict cases | Reviewed requirements and acceptable support sets; unresolved cases retained; inference cannot access labels |
| 2. Predict meaningful requirements | Extract atomic facts from the query alone; validate entity/date/unit fields; measure source support instead of query-word occurrence | Requirement/support errors audited on development data; extraction calls/version/prompt counted; no gold-derived features |
| 3. Test complementarity directly | Compare independent top-K, MMR, coverage, joint and a clearly labeled annotated oracle on identical candidate pools and a pinned generator | Complete-support and grounded-answer comparison with both source-only controls; negative outcomes retained |
| 4. Improve routing separately | Diagnose closing-price phrase misses; add validated request/entity contracts; then evaluate a trained/calibrated router only with legitimate labels | Measured source recall and quality/cost trade-off on a separate frozen cohort; heuristics not called probabilities |
| 5. Generalize verification | Structured entity/date/unit claims, compatible conflicts, explicit sufficiency and bounded regeneration | No majority resolution of copied claims; improved supported coverage without concealing abstention; all extra calls charged |
| 6. Finish research packaging | Reproducible baselines, component ablations, paired intervals and category-level error analysis; resolve original artifact scope | Evidence supports every reported claim; independent reviewer records exist; adapted vs faithful baseline distinction preserved |
| 7. Productize the verified path | FastAPI/Next.js interface, evidence citations, immutable run history and transparent missing-source/abstention states | Browser→API→data→answer checked end to end; displayed citations match actual evidence; no invented results |

## Design constraints

- Keep the existing pinned generator and dataset as controls. Any model/corpus change is a separate experimental factor.
- Keep reviewed annotations and reference answers in evaluation only. Learned/extracted requirements must depend on the query and available evidence, never the answer key.
- Avoid treating source diversity as complementarity. A web item plus an API item must jointly satisfy requirements that neither source alone supplies.
- Match full model budgets, including provenance/chat wrappers/output reserve. Report cumulative budgets and all calls when retries add work.
- Preserve raw/superseded outputs and bind reviews to exact prediction and prompt hashes.
- Calibrate uncertainty only with suitable held-out labels; heuristic scores remain scores.
- Use a new evaluation cohort after this version's response audit. Do not keep calling inspected/tuned-on questions unseen.

## Decisions to finalize after current-version audit

1. Which selector improvements are supported by genuine labels rather than literal agreement?
2. Which answer failures arise from retrieval, selection, temporal mismatch, ambiguous question premises, or generation?
3. How often does the conservative verifier withhold a factually correct but unparsed answer?
4. Where is all-source retrieval already cheaper than adaptive retry for equivalent outputs?
5. Which original reproduction assets are obtainable, and which remain unavailable?

This is a plan, not a completed experiment or a promised improvement. The accepted-output AI audit now supplies the priorities below. Scientific outcome targets still require independently reviewed evaluation before promotion.

## Observed failure requirements from the current audit

- Represent metric and unit explicitly: assists/48 minutes cannot satisfy three-point attempts/game.
- Bind entity roles and relations: company acquisition is not a CEO employment history.
- Distinguish daily constituent performance from generic index/ETF recommendations.
- Separate release year, award ceremony year, source publication time and question time.
- Check source factual quality separately from whether an answer follows the supplied text.
- Review dataset-reference quality for open or underspecified questions; a reference mismatch alone is insufficient to prove an answer wrong.
- Treat output truncation and speculative examples as observable failure modes, while keeping unresolved meaning explicitly uncertain.

These findings are AI-assisted development observations, not completed independent evaluation.


## Priorities after the completed legacy source audit

The first-50 AI-assisted review is complete; prospective-selector AI source analysis is now complete; historical and regeneration audits are now complete. The observed failures support this implementation order:

1. **Define the requested answer shape.** Query-only requirements must represent one example versus the complete qualifying set, quarterly series versus annual aggregate, both operands of a comparison, and the population behind a count/superlative. Leave ambiguous intent unresolved rather than inventing a singleton answer.
2. **Bind every measurement to its entity, relation and period.** Record instrument versus company, assists versus attempts, per-game versus per-48-minutes, career total versus one-opponent total, and franchise installment or award year. Negative eligibility such as never won is a required fact, not optional context.
3. **Remove boilerplate before ranking while preserving exact source spans.** Navigation numbers and unrelated linked articles should not be treated as evidentiary counts. Compare filtered and original retrieval as a retained ablation; do not assume filtering improves answers before measurement.
4. **Score support and factual correctness separately.** Keep externally correct but unsupported responses visible, and flag source chronology/quality conflicts even when the generator follows its context. Record external review evidence separately from the generation trace.
5. **Measure complete evidence rather than keyword overlap.** Include missing comparison operands and incomplete answer sets as explicit negative cases. A source-only control must show which requirements remain unsatisfied; diverse source IDs alone do not demonstrate complementarity.

Promotion requires fresh reviewed cases with the old inspected questions excluded, fixed generator controls, full cumulative costs, and independent evaluation of both answer quality and evidence support. These priorities do not close the current version's unfinished deliverables.


### Routing/retry decision from the historical audit

Retain direct all-source retrieval as a mandatory cost control: all eight actual retries reproduced its evidence, prompt and answer. On the inspected six-case set, retry adds generation cost without improving the resulting answer over fetching the eligible source initially. Do not generalize this to representative routing performance without a fresh cohort.

Separate three failure states in the next verifier: wrong-date evidence, correct numeric field with missing currency/adjustment metadata, and generator abstention despite sufficient field evidence. Test any structured extraction/rendering path as its own ablation against unchanged generator controls. Never infer missing currency from ticker familiarity or quietly replace an abstaining generator output in reported baseline results.


### Cohort execution findings — 13 October

The 250-response selector run is complete and structurally verified; full AI source review is now complete; independent review remains pending. Prioritize entity/role binding, time-window completeness and semantic abstention measurement. Coverage uses less context and abstains more often; compare complete support, substantive answer quality and total cost before promoting this behavior. The observed +1 literal match for several methods is not a demonstrated semantic improvement. Preserve the original metric and report reviewed prose abstentions separately.


### Requirements from the 19-question cohort source audit

Add a deterministic arithmetic check for explicit rectangular dimensions and other deliberately supported operations. Use operands from the query/evidence, record units and the calculation, and retain the unchanged generator answer as a control. A correct arithmetic tool must not be claimed as improved model reasoning or tested only on the already inspected room question.

Treat negative predicates and answer type as required constraints: eliminated differs from qualified, artist differs from song, individual height differs from height difference, and Olympic medals differ from Grand Slam titles. Preserve complete entity names and antecedents when selecting short excerpts. Validate matched comparison operands and definitions before issuing a ranking.

Do not promote coverage-only on cost reduction alone. Its inspected Grammy and Murray answers degrade despite directly relevant smaller evidence pools. Separate insufficient selected evidence, wrong computation, lost context and generator disregard of supplied facts in the final category analysis. The final method choice remains pending the complete source audit and independent evidence labels.


## Implementation order after all 444 accepted records were AI-audited

1. Implement query-only answer contracts and a conservative post-generation acceptance gate. Reject evidence identifiers as answers, detect required list cardinality and bind numeric claims to entity/field/unit/period. Keep raw generator outputs and controls immutable. Missing support yields an explicit unresolved result, not an invented correction.
2. Add deterministic arithmetic only for explicitly supported operations and units; keep it as a separate ablation. Count tool calls, retain model answers and test fresh cases.
3. Improve retrieval relevance and excerpt integrity while preserving exact source spans. Keep unfiltered retrieval as a control; avoid discarding evidence simply because it disagrees.
4. Add live generator inference to the existing replay/retrieval explorer, with fixed limits, truthful unavailable-model states, claim-level evidence checks and cumulative costs. Validate browser→API→model→evidence display. A replay endpoint does not satisfy this gate.
5. Complete the original open research deliverables: reviewed requirements/support sets, fresh entity/event-audited cases, true cross-source/source-only controls, full baseline/ablation matrix, paired reporting and evidence-backed paper. Resolve upstream assets or retain adapted-only scope.

Observed AI-correct counts are nine per method for top-K/MMR/joint/exact and five for coverage; this does not justify selecting a winning method. Treat the reviewed cohort as development data. Preserve 53 unresolved cohort judgments and separate factual correctness from selected support. [Completed failure analysis](COHORT_RESPONSE_AUDIT.md) supplies the current evidence; this plan is not a claim that the listed improvements have been implemented.


### Initial reliability implementation checkpoint

[Answer-form checks](ANSWER_CHECKS.md) now identify source-ID answers and unresolved/incomplete numbered lists, with a strict explicit-rectangle calculator. They are displayed in the replay demo and preserve all controls. This begins milestones 1–2 above; full semantic answer contracts, general claims and live generation are still unfinished. All 444 admitted outputs were checked through HTTP; 12 form warnings are diagnostics, not semantic improvement scores.


### Live-worker implementation checkpoint

A [private one-question GPU worker](LIVE_GPU_WORKER.md) executed and reconstructed one actual generation with the existing pinned model and budget. Next integrate durable asynchronous submission/polling into the existing FastAPI/Next.js app, with explicit states and no retry-by-resubmission after observation failure. Keep this development demonstration separate from research controls and finish claim-level support and cumulative latency/cost reporting.


### Durable browser job bridge verified

The [asynchronous GPU demo](LIVE_DEMO_FLOW.md) now survives API restart and page refresh without resubmission. Next implement entity/date/unit and claim-support contracts, then evaluate adaptive multi-source execution and genuine cross-source controls. Retain the old fixed-web worker and all frozen results as controls. This one development case is not a method-quality improvement claim.


### Evidence-driven verification decision

The [completed NLI diagnostic](NLI_SUPPORT_DIAGNOSTIC.md) does not justify raw-entailment acceptance. Prioritize explicit query contracts and faithful claim framing: requested entity/role, metric, date window, units, comparison operands and list completeness. Keep missing or ambiguous fields unresolved. Use the independent classifier only as a separately costed source-text diagnostic until the combined path is measured on fresh reviewed cases. Preserve all model/AI disagreements; do not label this experiment classifier accuracy.


### Partial query-contract findings

[The executed contract replay](QUERY_CONTRACTS.md) shows why explicit wording checks
alone are insufficient: no additional scope/date flags appear among all 444 admitted
answers. Implement span-bound structured source claims and query relations next; bare
numbers must remain unresolved until entity, metric and period are grounded. The
assistant continues implementation; the proposed friend handoff is no longer an
execution dependency. Owner-only PR merge and independent review gates still apply.


### Structured extraction execution checkpoint

[The bounded blinded extractor](STRUCTURED_CLAIM_EXTRACTION.md) is submitted for all
50 development questions and 336 distinct selected source excerpts. Wait for completion
of the existing job, reconstruct actual outputs/costs and audit tuple roles before
using its proposals. Literal aligned fields are not semantic support. Prioritize full
claim coverage, comparisons, relative-date handling and independently reviewed fresh
cases; none is closed by submission or substring validation.


### Decision after complete structured extraction audit

The [completed unconstrained run](STRUCTURED_CLAIM_EXTRACTION.md) yields zero contract-valid
query proposals and six source proposals; five of those have field-role/scope problems
in AI source review. Retain the failed protocol. Before further support experiments,
enforce schema and permitted span choices rather than trusting JSON instructions. Then
audit entity/relation/period attachment and complete claim coverage independently of
syntax. No validation pass alone permits automatic acceptance; independently reviewed
fresh cases and the full roadmap research gates remain required.


### Constrained decoder checkpoint

[Closed-span extraction](CONSTRAINED_EXTRACTION.md) is submitted with the same tasks,
prompts, generator and model budgets as the failed control. Do not confuse enforced
syntax/spans with correct entity/relation/period roles. Reconstruct the existing job,
audit every completed proposal and compare structural coverage and semantic failures
against the retained control before promotion. Keep output-cap failures and unresolved
comparisons visible; automatic acceptance remains disabled.


### Requirements from the first 100 constrained source reviews

Before any support promotion, separate publication metadata, event dates, comparison
periods and quantities; preserve table-row associations, film/character/person roles,
negative eligibility and lower-bound qualifiers. Do not repair wrong fields silently
by discarding units/periods after evaluation. Distinguish coherent excerpt claims
from external truth and question sufficiency. Deduplicate equal text/proposal pairs
in evidence analyses. The observed combining-mark boundary defect is a required
current-version correction with a frozen-source control, not evidence that schema
validity establishes entity completeness. The remaining 235 source proposals must
still be reviewed before final diagnostic conclusions.


### Unicode correction implementation checkpoint

The [combining-mark-aware v2 policy](UNICODE_SPAN_POLICY.md) and full old-output replay
are implemented. Integrate that explicitly versioned policy into a subsequent
controlled decoder before claiming new neural results. Preserve the v1 source and
outputs; do not normalize stored text or discard truncated-name failures. This
lexical correction does not satisfy multiword entity identity, complete atomic
requirements or semantic-support validation.


## Priorities from complete constrained proposal-role review

The complete post-hoc review binds 50 query proposals, 335 valid source proposals
and one capped failure. Its categories are qualitative AI judgments, not calibrated
accuracy: source validity does not establish role correctness or exhaustive claims.
Preserve the frozen v1 outputs, candidate policy and prompts as the control.

1. **Execute the versioned boundary correction.** Use the combining-mark-aware
   module in a separate explicit protocol and GPU bundle, with the same blinded
   386 tasks, generator pin, prompts, FP32, seed and token limits. Reconstruct
   decoded IDs, candidate spans, protocol identity and costs. Retain capped errors
   and record changed outputs; do not call CPU replay corrected neural generation.
2. **Represent atomic facts with typed roles.** A frame needs subject, relation,
   object/value, measurement unit, event time and observation time, plus exact
   supporting spans and attribution. Distinguish acquired magazine from purchaser,
   investor sales from an executive biography, IPO offer from first-day close,
   nomination from award win, film from character and lake area from visit season.
   Preserve negation, estimates, rumors, plans, upper/lower bounds and comparators.
3. **Handle multi-claim requirements explicitly.** A single six-field tuple cannot
   express both sides of a comparison, complete lists or all required time windows.
   Extract query requirements from the query alone and source claims from evidence
   alone; count every extraction call. Validate direction and typed bindings before
   calculating support. Missing or ambiguous relations remain unresolved.
4. **Reject assertion promotion from page structure.** Related questions, navigation,
   author credentials and publication timestamps are not answers or event dates.
   Keep them distinguishable from source assertions without discarding legitimate
   factual image captions. Preserve unfiltered retrieval as an ablation.
5. **Measure improvement on fresh cases.** This inspected cohort is development
   data. Keep all prior exposures excluded from fresh entity/event-audited evaluation.
   Separate source fidelity, external correctness and complete answer support;
   compare fixed model/candidate controls and charge added calls. Independent human
   labels remain a distinct promotion gate rather than relabeled AI judgments.

These implementation priorities do not close the original artifact, independent
review, cross-source/source-only control, router calibration, full ablation and
evidence-backed paper gates. The source-role audit is complete; the scientific
objective remains in progress.


### Implementation checkpoint: corrected decoder and plural frames

The versioned Unicode GPU control is complete, reconstructed and fully review-bound.
It corrects the observed name boundary in one output; semantic row mixing remains.
The plural-frame prompts and exact statement-local validator are now implemented
with six regression tests. Inventory GPU generation, role/completeness measurement
and support composition remain next. Preserve the completed single-frame controls
and measure changed prompts/budgets as explicit experimental factors. Do not infer
complete extraction from a proposed_complete output or acceptance from exact spans.


### Priorities from the completed plural-inventory control

The v1 inventory run is a retained negative result: 386 sequences, 176,078 output
tokens and 21 structurally valid inventories. All 21 valid outputs show role or
requirement problems in qualitative AI review; 365 rejected outputs have not had
full semantic assessment. Do not turn these counts into calibrated accuracy.

1. Separate known query constraints from unknown answer variables. Explicit numbers,
   comparison operands, cardinality and eligibility may be copied query facts without
   being guessed answers. Represent their logical relationships rather than forcing
   every query value to null or burying them in relation prose.
2. Version statement-aware generation separately, with provenance-bound context
   metadata where attribution/observation dates legitimately lie outside a clause.
   Preserve strict binding and handle duplicate frames without blocking valid
   multiple operands in one statement. Typed/date-looking syntax is not role truth.
3. Evaluate an extractor/prompt change only with fixed answer-generator controls and
   explicit extraction costs. Gate query requirements before spending on all source
   frames; keep the full source/evaluation objective intact. Stronger models must be
   separate measured factors, with no assumed semantic improvement.
4. Integrate the restored ID/year and BM25 name paths into bounded API evidence.
   Retain the changed tie policy, unknown identities, snapshot time restrictions and
   source-only controls. Actual lookup success is not a cross-source benefit result.

Independent labels, fresh entity/event-audited cases, full ablations and final
evidence-backed reporting remain required.


### Query-only logical requirement implementation

The [unknown-answer schema](QUERY_REQUIREMENTS.md) now preserves explicit known
conditions independently of unknown answer/intermediate variables. The bounded
closed grammar forbids invented copied facts and undeclared references; independent
validation checks local spans, variable roles, operation arity and self-dependencies.
This is implemented infrastructure, not a measured extraction improvement. A separate
query-only GPU protocol and full role/omission audit are next; source requirements,
semantic support and independent evaluation remain open.


### Query-requirement execution submitted

The [query-only protocol](QUERY_REQUIREMENTS.md) is frozen and privately submitted:
fifty questions, at most thirteen batched extraction calls, same pinned Qwen model,
FP32 and seed, changed query prompt/representation. Tokenizer preflight fits every
request; all 219 local tests pass. Version 1 of
`ionrey/ace-requirements-0f48b7f420a648cdbf532361c3fd13a8` was observed RUNNING.
Collect and reconstruct that same job, then review every role/omission before source
support integration. No completed neural quality or semantic improvement is claimed.


### Priorities after the completed query-only diagnostic

All fifty decoded query proposals reconstruct and have bound AI role/omission
reviews; all fifty fail validation. Preserve the failed query model/prompt/grammar
control. Test role-aware local decoding and extractor capacity as separate measured
factors; a stronger model is not assumed to improve semantic completeness. Retain
unknown answers and known numeric constraints without weakening validation.

The real [movie evidence integration](MOVIE_EVIDENCE.md) prepares eighteen requests
from five actual local lookups on three inspected questions. Source fields and full
budgets verify, but two shared union-ranked pools admit no API candidates. Retain
these empty source-only controls and separately measure retrieval changes before
claiming API irrelevance or cross-source benefit. All 224 local tests pass; no new
baseline answers are generated by this probe. The complete roadmap goal remains open.


### Model-variant execution checkpoint

The separately pinned [3B extractor trial](REQUIREMENTS_MODEL_VARIANT.md) has identical
query task/prompt/span/input-token/budget controls and explicitly restores original
decode defaults. It changes the model weights/architecture as one model-variant
factor, not the answer generator. Fifty sequences / thirteen generate calls are the
bounds. Version 1 was submitted and observed RUNNING; completed quality remains
unverified. Preserve the failed 1.5B control and compare actual runtime before
interpreting changes. All 227 local tests pass. Full roadmap completion remains open.


### Priorities from the completed 3B comparison and contract diagnosis

All fifty 3B outputs reconstruct and have bound AI assessments. Five pass structural
checks, but all five have no linked clause roles; semantic improvement is not
established. Actual runtime/input/decode identities match the retained 1.5B control.
Before another model change, align prompt/grammar/validator operation requirements,
separate variable entity/measurement type from per-relation subject/object position,
and distinguish disconnected/all-null clauses from meaningful linked requirements.
Preserve frozen scores; synthetic contract examples are engineering evidence, not
new neural quality. See [the completed model diagnostic](REQUIREMENTS_MODEL_VARIANT.md).

Continue rejected inventory assessment: 71/386 tasks now covered, with all fifty
queries and 21 sources assessed; 315 source tasks remain. Retain coherent partial
facts and metadata context without promoting navigation/examples into assertions.
All 229 local tests pass. These steps do not close independent labels, full source
composition, fresh evaluation, faithful-artifact and evidence-backed final-paper gates.


### Typed query graph v2 implementation

[The new graph contract](QUERY_GRAPH_V2.md) now separates variable types from clause
argument positions and supports dependent typed operations. Fifty development requests
fit the pinned tokenizer budget. GPU extraction completed and reconstructs fifty sequences. All fifty exact-output
AI assessments cover 151 checks: three coherent partial cores and 47 misbound or
incomplete proposals. Structural linking does not certify completeness or enable
answer acceptance.


### Decision after the typed graph v2 diagnostic

Keep the v1 and v2 runs as immutable negative controls. The new grammar enforces
syntactic/type/local-span discipline, but it does not establish complete semantic
requirements. Adding a structure-success label or tightening validation after the
run would conceal the measured failure rather than fix it.

The next extraction trial should separate query interpretation from compilation:
first propose a small set of atomic requested facts, known query conditions and
unknown intermediate values; then compile actor/relation/value/period roles and
operations into a graph. Test this as an explicit multi-call protocol, retaining
the single-call v2 control and charging every pass. Do not call it an improvement
until exact-output comparison demonstrates fewer omissions and wrong associations.

Required cases for that trial include known names versus unresolved descriptions,
query-time anchors versus observed measurement dates, two distinct comparison
operands, negative eligibility, explicit top-N cardinality and result units.
Preserve partial successes such as the copied 17-by-66 product; extra unused dates
must remain observable. Keep extracted requirements out of answer acceptance until
complete source support is separately verified.

Finish the remaining 145 plural-inventory source assessments and source-only
control work in parallel with engineering preparation. The seen fifty-question
cohort is development data. Fresh entity/event-audited cases, independent support
labels, calibrated routing, complete baselines/ablations and original upstream
artifact resolution remain the scientific promotion gates. AI-assisted review
cannot be relabeled as independent human review.
