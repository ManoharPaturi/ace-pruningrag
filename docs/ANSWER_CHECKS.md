# Query-only answer checks and arithmetic diagnostics

Updated 13 October 2026. The explorer now displays conservative answer-form warnings beside unchanged recorded outputs. The implementation is [answer_checks.py](../src/ace_pruningrag/answer_checks.py); [replay results](../results/version1/answer_checks_replay.json) cover all 444 admitted accepted response records with zero new model calls. These are post-hoc development diagnostics, not measured improvements in generated-answer accuracy.

## Implemented behavior

- A whole answer matching a selected evidence identifier is flagged when the question does not ask for an identifier/hash. Simple wrapping is tolerated. The original answer is retained.
- A numeral-based `top N` question requires a complete, contiguous, unique numbered list for this narrow parser. Unnumbered prose/comma lists are unresolved, not automatically factually incorrect. Numbered-list structure alone does not establish holdings, rank, or query-date eligibility.
- An explicitly rectangular area request with exactly one compatible positive pair of lengths can be calculated using decimal arithmetic. The result records operands, query span and square unit. Only a bare scalar with a supported square unit is compared; prose, mixed units, negative/zero dimensions, multiple rectangles and unspecified geometry remain unresolved.
- Exact short-form model abstentions stay abstentions. No check claims factual correctness or source support. No gold answer, human support set or AI-review label enters the checker.

The inspected 17-by-66 room query does **not** explicitly state rectangle geometry, so it produces no automatic calculation. Its five observed arithmetic failures remain in the audit. This conservative module has unit-level verification on fresh explicit-geometry cases; it has not demonstrated a geometry or reasoning improvement on the admitted experiment.

## Actual replay

| Run | Responses checked | Flagged responses | Observed flags |
| --- | ---: | ---: | --- |
| Legacy | 150 | 3 | Requested numbered-list form unresolved |
| Historical | 18 | 0 | No form issue detected |
| Regeneration initial | 18 | 0 | No form issue detected |
| Regeneration retry | 8 | 0 | No form issue detected |
| Five-selector cohort | 250 | 9 | Four provenance IDs, four unresolved lists, one list cardinality/numbering mismatch |

Zero flags in a run does not mean its answers are correct, temporally aligned or supported. None of these admitted queries met the explicit rectangle calculation contract. The 12 flags must not be scored as twelve independently proved errors.

Reproduce with the pinned dataset and private traces in `configs/demo.json`, choosing a fresh output:

```bash
uv run --locked --no-editable --extra demo python scripts/answer_checks_replay.py \
  --output runs/version1/answer-checks-reproduced.json
```

## Flow verification

**Story:** choosing a recorded answer → Next.js proxy → FastAPI → hash-admitted trace → query-only checks → unchanged output plus warning.

| Boundary | Evidence |
| --- | --- |
| API/data | HTTP checks compared all 444 predictions, prompt hashes and selected evidence IDs with their original records; all matched |
| Check response | All 444 explicitly retained false factual/citation-verification fields; 12 had form flags |
| Client/API | Browser loaded the cohort/Legally Blonde/coverage record through the existing Next.js proxy |
| Rendering | The original source-ID answer appeared beside “The answer contains a source ID instead of the requested fact” and the unchanged source excerpt |
| Console | No captured browser warnings/errors |
| Build/tests | Next.js production build passed; 141 local tests passed; Ruff lint/format and diff checks passed |

Private screenshot: `runs/version1/demo/answer-checks.png`. API runs on localhost port 8060; UI uses port 3060 and the existing server-only API address. No Vercel deployment or credentials are needed for this flow.

## Open implementation and research requirements

General answer contracts, complete qualifying sets, entity/field/date/unit binding, source factual quality, claim-level citations, live generation, bounded general regeneration and fresh independently reviewed ablations remain open. The current price-field verifier remains separate. Integrate these diagnostics into a future live acceptance path without changing frozen controls; retain unresolved answers and charge all additional operations.
