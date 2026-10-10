# Bounded answer regeneration after evidence retry

## Frozen development protocol

PR #12 established that fetching missing dated evidence after generation did not change the already generated answer. This experiment explicitly generates a new answer after that lookup, while retaining an initial-round control in the same GPU job.

The protocol is frozen in `configs/bounded_regeneration.json`. It uses the same six development queries, source snapshot, Qwen revision, float32 guards, greedy decoding, prompt, selector, routing policies, and per-round 2,048-token cap as the historical diagnostic. There are 18 initial policy/query generations. The trigger is missing sufficient structured evidence for the requested entity/date; it does not inspect gold answers or choose retries based on correctness. Existing abstentions with missing evidence remain eligible.

Exactly eight frozen requests qualify: all six fixed-web requests and adaptive AEAE/TBMC. All-source requests already have the required price and receive no retry; BLACW's existing abstention with adequate structured evidence also receives no retry. This is a development ablation of evidence-triggered regeneration, not an attempt to fix every abstention.

A retry switches that request to the already provisioned all-available source policy and rebuilds the context. It executes another web retrieval, one routed price lookup, and one genuine model generation. Each round reserves at most 2,048 tokens, and the cumulative request reserves at most 4,096 tokens over two rounds. Thus the method pays more than the single-round baseline; this is an explicit quality/cost comparison, not a matched cumulative-budget improvement. Maximum generator calls are 26, with no judge calls. No route or prompt is silently tuned.

The reliability verifier from PR #12 checks final answers. Its conservative price-field acceptance is not independent human semantic correctness. Currency remains unknown; dollar prose can be withheld even when its number looks plausible. Strict sentence support was developed from the earlier AEAE example and therefore cannot count as unseen-case success.

## Verification

Local real-tokenizer preparation verifies all 18 initial requests and the eight retry requests, including actual source calls and cumulative reserved-token caps. CI repeats this check against original SQLite and the pinned dataset.

The independent output verifier first runs the existing initial-generation verifier. It then reconstructs retry eligibility from initial evidence, reconstructs all eight retry prompts and dated SQLite evidence, decodes output IDs, checks per-round/cumulative token caps, verifies decisions, binds the submitted execution bundle, and recomputes call and token totals.

```sh
uv run --locked --no-editable --extra generation python scripts/historical_preflight.py \
  --retry --output runs/phase4/regeneration-preflight-v1
uv run --locked --no-editable python scripts/build_kaggle_kernel.py \
  --owner ionrey --mode regeneration --output runs/kaggle/regeneration-kernel-v2
uv run --locked --no-editable --extra generation python scripts/verify_regeneration.py \
  --run runs/kaggle/regeneration-output-v2/phase3-pilot \
  --output runs/phase4/regeneration-verification-v2.json
```

Outputs refuse overwriting. Full traces remain ignored; compact summaries and hashes are tracked. The private execution target is https://www.kaggle.com/code/ionrey/ace-pruningrag-bounded-regeneration.

## Research boundary

These previously inspected six cases are development data. Completing the execution and verification does not complete the full Phase 4 research gate: a reviewed held-out extension, genuine comparable cross-source conflicts, and independently reviewed semantic quality remain necessary. Keep costs, supported-price coverage, and abstentions visible together; a verifier that withholds everything is not a successful answerer.

## Measured development comparison

| Initial routing | Model calls without retry | Extra model calls | Verified price-field answers before → after |
| --- | ---: | ---: | ---: |
| fixed web | 6 | 6 | 0/6 → 3/6 |
| all available | 6 | 0 | 3/6 → 3/6 |
| adaptive | 6 | 2 | 1/6 → 3/6 |

All 18 initial prompts and predictions match the previous historical GPU run. All eight retry prompts and predictions match their corresponding all-source control. This makes direct all-source retrieval the cheaper option on these six cases; the bounded retry repairs a missed-source first round, but it does not demonstrate an advantage over the direct all-source control.

Raw generator abstentions fall from 4/6 to 1/6 for fixed-web requests and from 3/6 to 1/6 for adaptive requests. Three price-field answers per policy survive the strict verifier. UBSI and WNW dollar-denominated prose remains withheld because currency is not established; BLACW remains an abstention. Withheld/unparsed prose is not automatically factually wrong.

The admitted run's total cost is 26 model calls, eight additional web retrievals, eight routed price lookups, eight retry eligibility price reads, and 26 additional inventory reads. Initial-round costs remain separately recorded: 18 web retrievals, ten routed finance calls, six eligibility price reads and six inventory reads. The initial three-ticker price audit makes six further price reads. Total request inputs and outputs, per-call timings, and token reserves are recorded in the compact summaries; verifier/review-building work is separate from inference cost.

A readable packet contains the last actual model answer and exact prompt evidence for all 18 policy/query pairs, with generation round marked. It shows raw generated answers **before** conservative verification filtering, so reviewers can judge both meaning and grounding. Reviewer decisions start pending. It does not manufacture human labels or rewrite model predictions.

The admitted private kernel is version 2, which checks the total call limit before an extra generation. Version 1 also completed 26 calls; version 2 repeats the experiment with the earlier stop guard. Total GPU generations across both jobs are 52, rather than 26. Both runs are preserved, and only version 2 is admitted as the current implementation result. The final run uses 29,568 input tokens and 465 output tokens across all 26 calls; maximum cumulative reserved tokens are 2,872. The eight retry generations take about 13.53 seconds together, excluding model loading and asset download.
