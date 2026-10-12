# Next-version plan — draft pending current-version response audit

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

This is a plan, not a completed experiment or a promised improvement. Finalize priorities and acceptance metrics after all current outputs are available and reviewed.

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

The first-50 AI-assisted review is complete; prospective-selector analysis still remains; historical and regeneration audits are now complete. The observed failures support this implementation order:

1. **Define the requested answer shape.** Query-only requirements must represent one example versus the complete qualifying set, quarterly series versus annual aggregate, both operands of a comparison, and the population behind a count/superlative. Leave ambiguous intent unresolved rather than inventing a singleton answer.
2. **Bind every measurement to its entity, relation and period.** Record instrument versus company, assists versus attempts, per-game versus per-48-minutes, career total versus one-opponent total, and franchise installment or award year. Negative eligibility such as never won is a required fact, not optional context.
3. **Remove boilerplate before ranking while preserving exact source spans.** Navigation numbers and unrelated linked articles should not be treated as evidentiary counts. Compare filtered and original retrieval as a retained ablation; do not assume filtering improves answers before measurement.
4. **Score support and factual correctness separately.** Keep externally correct but unsupported responses visible, and flag source chronology/quality conflicts even when the generator follows its context. Record external review evidence separately from the generation trace.
5. **Measure complete evidence rather than keyword overlap.** Include missing comparison operands and incomplete answer sets as explicit negative cases. A source-only control must show which requirements remain unsatisfied; diverse source IDs alone do not demonstrate complementarity.

Promotion requires fresh reviewed cases with the old inspected questions excluded, fixed generator controls, full cumulative costs, and independent evaluation of both answer quality and evidence support. These priorities do not close the current version's unfinished deliverables.


### Routing/retry decision from the historical audit

Retain direct all-source retrieval as a mandatory cost control: all eight actual retries reproduced its evidence, prompt and answer. On the inspected six-case set, retry adds generation cost without improving the resulting answer over fetching the eligible source initially. Do not generalize this to representative routing performance without a fresh cohort.

Separate three failure states in the next verifier: wrong-date evidence, correct numeric field with missing currency/adjustment metadata, and generator abstention despite sufficient field evidence. Test any structured extraction/rendering path as its own ablation against unchanged generator controls. Never infer missing currency from ticker familiarity or quietly replace an abstaining generator output in reported baseline results.
