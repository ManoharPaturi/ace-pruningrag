# Phase 4: bounded historical reliability implementation

## Status and scope

The engineering milestone is implemented and measured on the frozen six historical development questions (18 existing GPU predictions). It includes comparable structured-price conflict detection, a sufficiency-controlled lookup capped at one extra call, and conservative answer verification, with separate component ablations. It does **not** complete the full roadmap's Phase 4 research gate: independent semantic reviewer labels, a reviewed held-out evaluation extension, and a general cross-source claim parser remain missing.

The six questions were already examined in Phase 3. These are development results, not a new held-out benchmark. Baseline routing, prompt, generator, token budgets, and all original outputs remain unchanged. This run executes original SQLite lookups and deterministic checks; it makes **zero new generator or judge calls**. Retry supplies evidence to the verifier and never silently rewrites or regenerates the answer.

## Contract

- The request must name one supported ticker and the previous calendar day's close. Same-day/future rows cannot satisfy it; no backfilling the previous trading day.
- The replay authenticates every selected API field against the pinned original SQLite row, including timestamp, exact value, snapshot, source reference, and limitations. A trace digest alone is insufficient.
- Sufficiency means the requested entity/date has a structured price with no detected comparable conflict. It does not mean the question's entire natural-language answer is supported.
- Conflicts compare entity, date, currency, and adjustment basis. Repeated copies cannot resolve a disagreement by majority vote. Unknown currency/basis are explicit; this experiment uses one snapshot's exact close field. Web prose is not parsed and is never asserted conflict-free.
- One initial evidence round plus at most one extra structured lookup is allowed. Missing results and unresolved conflicts stop after that lookup. All extra calls count, including failed/empty attempts.
- Verification accepts a bare finite numeric value or a strict ticker/date closing-price sentence. Absolute numeric tolerance is `1e-6`, relative tolerance zero, matching the earlier numeric diagnostic. Unsupported currency, other prose, mismatched dates, extra instructions, and values outside that tolerance are withheld. Unparsed prose is not labeled factually incorrect.
- The strict sentence grammar is a development extension motivated by the observed AEAE response. It is not an unbiased estimate of performance on new phrasing. Currency is absent from the original row, so dollar-denominated prose is conservatively withheld even when its number appears plausible.

## Actual replay results

Each cell concerns six distinct questions for the indicated routing policy. Each original answer is reused across the three verifier variants; the resulting 54 decisions are not 54 independent model generations.

| Policy | Dated evidence before retry | After retry | Extra API calls in full variant | Released price-field answers | Withheld answers |
| --- | ---: | ---: | ---: | ---: | ---: |
| fixed web | 0/6 | 6/6 | 6 | 0/6 | 6/6 |
| all available | 6/6 | 6/6 | 0 | 3/6 | 3/6 |
| adaptive | 4/6 | 6/6 | 2 | 1/6 | 5/6 |

The released all-source answers are CSLM, AEAE, and TBMC; adaptive releases CSLM. These are checks against the snapshot's price field, **not independent semantic correctness labels**. BLACW remains a generator abstention. Fetching the missing AEAE/TBMC evidence for adaptive routing does not change their existing generator abstentions.

The full verifier therefore exposes a practical limitation: better evidence availability alone does not repair a completed answer. The next generation experiment must explicitly rerun the model after retry and charge those additional calls and token budgets. This replay does not claim that experiment occurred.

Verification-only and full retry+verification release the same number of answers on these cases. Retry raises dated-evidence sufficiency from 10/18 to 18/18 but buys no answer coverage here. Disabling the conflict guard changes no natural result because this set contains no authenticated comparable structured-price conflicts. Controlled conflict tests demonstrate that removing the guard can accept one supported side of an unresolved disagreement; those tests are not real-data efficacy estimates.

Cost accounting: six shared inventory reads, 12 shared price validation reads, and 16 additional price lookups actually executed across the two retry variants (eight each). These validation reads are outside the per-request retry cap and are explicitly disclosed. Existing Phase 3 costs are recorded separately in its manifest: 18 generator calls and 10 routed API calls plus preflight costs. Adding these replay checks does not retroactively change that baseline.

## Verification and reproducibility

```sh
uv run --locked --no-editable pytest -q
uv run --locked --no-editable python scripts/reliability_replay.py \
  --input runs/kaggle/historical-output-v1/phase3-pilot/generated/predictions.jsonl \
  --output runs/phase4/reliability-replay-v1
```

The output directory must not already exist. The runner verifies frozen pairs, config binding, input trace SHA, pinned dataset and price assets, and selected structured fields against SQLite. Gold answers never enter the reliability method. Two corrupted real-trace copies (altered price and duplicate query/policy pair) were rejected even after recomputing their trace digests. The original trace stayed unchanged. The summary binds the method source files and decisions with SHA-256 hashes. The compact summary is tracked under `results/phase4/reliability/`; full decisions and original predictions remain ignored local artifacts.

CI's required `finance-smoke` job additionally replays real tokenizer-prepared evidence against SQLite, checking all 18 policy preparations without downloading model weights or fabricating predictions. The `test` job covers conflict comparability, duplicate-source majority attacks, missing dates, same-day leakage, empty fetches, retry caps, non-finite numbers, unsupported currency, incorrect rounding, exact date/entity binding, injected prose, and the conflict-guard ablation. The other required real-data smoke job remains enabled.

## Remaining research gate

Keep the general Phase 4 gate open until independent reviewer records and a reviewed evaluation extension exist. General web claim extraction, compatible cross-source conflict evaluation, and fresh bounded regeneration need separate experiments. A verifier that withholds nearly everything must be assessed with answer coverage alongside supported claims; these results do not demonstrate a broad accuracy improvement or publication readiness.
