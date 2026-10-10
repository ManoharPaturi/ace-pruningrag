# Historical routing diagnostic

This bounded development experiment uses the six query IDs frozen by the
previous full-dataset price eligibility audit. Questions ask for a prior-day
closing price and have exact dated rows in the immutable original CRAG snapshot.
The questions were selected for executable source availability, not answers or
model performance. This is not a representative RM3QA benchmark or the original
PruningRAG reproduction.

## Frozen comparison

- Six same questions under fixed-web, all-available, and heuristic adaptive routing.
- Original pinned Qwen2.5-1.5B-Instruct revision, float32 numerical guards, seed 42,
  greedy decoding, system prompt, top-K selector, web pool and chunking unchanged.
- Shared 2,048-token total request cap, with 96 output tokens reserved. Actual
  chat templates, question/time, headers, separators and evidence count toward it.
- API evidence contains the requested earlier closing price, exact original row
  timestamp, immutable snapshot hash, and explicit unspecified currency/basis.
  Missing dates never fall back to a different price. Same-day completed prices
  cannot answer a morning question in this adapter.
- Each policy genuinely executes its allocated sources; record preflight lookup,
  retrieval and generation costs separately. Six inventory SQL reads and six
  price-eligibility reads happen in shared preflight, outside per-policy retrieval
  timing; snapshot-audit/model-download/setup costs are also outside that timing. Rotate execution order per question.
- Keep the adaptive hint rules unchanged: they miss two closing-price phrasings.
  Adaptive requests four API rows; all-available six; fixed-web zero. The different
  source allocations are part of the result, not retuned using generated answers.
- Gold answers enter post-generation literal agreement only. Non-exact answers
  remain pending semantic review; literal disagreement alone is not incorrectness.

The original first-50 configuration remains unchanged. The new configuration is
`configs/historical_routing.json`. CPU preparation verified all 18 prompts:
maximum prompt plus reserved output is 1,657 tokens. Model calls during this
preflight are zero.

## Reproduce

```sh
uv run --locked --no-editable --extra generation python scripts/historical_preflight.py \
  --output runs/new-historical-preflight
uv run --locked --no-editable python scripts/build_kaggle_kernel.py \
  --owner YOUR_ACCOUNT --mode historical --output runs/kaggle/new-historical-kernel
uv tool run --from kaggle==2.2.4 kaggle kernels push \
  -p runs/kaggle/new-historical-kernel -t 1800
```

The historical kernel has a separate private identity and preserves the original
first-50 kernel. Only allowlisted code and pinned configs enter the bundle; human
reviews, credentials, raw datasets and weights stay excluded. Inference uses the
same isolated fresh-process dependency versions and records whether base package
versions changed.

Run `scripts/verify_generated.py --run PATH/phase3-pilot/generated` with the
generation extra after downloading outputs. The verifier independently checks
original web spans and dated SQLite values, reconstructs API identity, prompts,
token/output decoding, per-source/full budgets, source/model counts and summaries.
It also remains compatible with the earlier first-50 trace.

The required finance-smoke CI job prepares all 18 requests with the actual model
tokenizer and original historical prices. Unit tests and real-source preparation
are development checks; GPU execution and recovered-output verification are
separate requirements.

## Prespecified numeric diagnostic

In addition to unchanged literal agreement, inspect pure numeric predictions
against the retrieved closing-price field with absolute tolerance `1e-6` to
allow SQLite floating-point representation noise. This is a price-value
agreement diagnostic, not an independent semantic or complete grounding label.
It must not accept a rounded warrant price with a materially different value.
Predictions containing explanations or currency assumptions require review.

## Completed GPU results

Kaggle version 1 completed all 18 genuine generations on a Tesla T4. All outputs
passed independent provenance, dated-value, prompt/token, budget, numerical,
decoding and summary verification. Submitted/recovered execution source hashes
match the current source, and Kaggle's base package versions were preserved.
The verifier also rejected deliberately changed API values, prompt token counts,
and per-source budget shares even after the modified traces were rehashed.

| Policy | API calls | Abstained | Literal agreement | Mean prompt tokens | Mean generation |
| --- | ---: | ---: | ---: | ---: | ---: |
| Fixed web | 0 | 4/6 | 0/6 | 1,265.17 | 1.609 s |
| All available | 6 | 1/6 | 0/6 | 1,055.83 | 1.584 s |
| Adaptive | 4 | 3/6 | 0/6 | 1,161.67 | 1.492 s |

There were 18 web retrievals and 10 executed price lookups, in addition to six
shared price-eligibility lookups and six inventory SQL reads. Model loading took
7.598 seconds. Download/setup and source-eligibility work are outside the reported
per-policy retrieval/generation timing. Timing over six requests is descriptive,
not evidence of a general speed advantage. All-available used fewer prompt tokens
because splitting the shared budget reduced web context; sources did not each
receive a fresh 2,048-token allowance.

Maximum prompt plus output: 1,567 tokens. Maximum prompt plus reserved output:
1,657 tokens. Zero questions had identical prompts across all policies; one had
identical predictions (the BLACW abstention).

## Assistant-assisted evidence reading

This table is an assistant's diagnostic reading of the actual answers and exact
price rows. It is **not independent human semantic grading** and does not promote
new correctness/grounding labels into the run summary.

| Ticker | Requested-day close in snapshot | Fixed web | All available | Adaptive |
| --- | ---: | --- | --- | --- |
| UBSI | 34.40999984741211 | Answers a July 2024 price, outside the requested February date | Says 34.41 for February 27 | Same as all-available |
| WNW | 1.2400000095367432 | Says 0.10 | Says 1.24 | Same as all-available |
| CSLM | 11.01099967956543 | Abstains | Gives exact stored close | Gives exact stored close |
| BLACW | 0.012500000186264515 | Abstains | Abstains despite price evidence | Abstains despite price evidence |
| AEAE | 11.095800399780273 | Abstains | Gives exact close and requested date | Abstains; price hint missed |
| TBMC | 10.529999732971191 | Abstains | Says 10.53 | Abstains; price hint missed |

The supplied RM3QA references are currency-prefixed, cent-rounded strings.
Generated narratives, omitted currency symbols and retained stored precision
therefore prevent literal matches even when the price value agrees. The snapshot
row itself does not establish currency or adjustment basis; currency claims in
narrative outputs require review. The same model still fails the BLACW case even
with the relevant price row. More evidence does not guarantee a usable answer.

Under the prespecified **pure numeric** diagnostic, two all-available predictions
and one adaptive prediction agree with the price field within `1e-6`; fixed-web
has zero. Narratives and currency-prefixed outputs remain excluded from that
numeric parser, not silently classified as incorrect. The table above provides
the separate diagnostic reading for those cases.

Reproduce that diagnostic with `scripts/historical_numeric_diagnostic.py --run
PATH/phase3-pilot/generated --output NEW_PATH.json`. Full outputs remain local at
`runs/kaggle/historical-output-v1`; compact manifests, results and checks are in
`results/phase3/historical_routing`. A readable six-question/18-answer review page
is at `runs/phase3/historical-review-v1/review.html`, with human decisions pending.

## Outcome and remaining research gate

The executable historical routing diagnostic is complete. Relevant dated API
access changes the prompts and answers, while the unchanged adaptive hints miss
two cases. The next reliability work should address those missed source hints and
the BLACW abstention in separate development ablations, preserving this baseline.

This six-case availability-selected diagnostic does not establish representative
semantic accuracy, calibrated routing, genuine cross-source necessity, or a
publication-level Phase 3 quality/cost result. Independent review and a larger,
frozen source-compatible evaluation remain required for that broader claim.
