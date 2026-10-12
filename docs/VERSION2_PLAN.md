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
