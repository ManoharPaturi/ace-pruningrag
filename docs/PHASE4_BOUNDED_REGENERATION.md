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
  --owner ionrey --mode regeneration --output runs/kaggle/regeneration-kernel-v1
uv run --locked --no-editable --extra generation python scripts/verify_regeneration.py \
  --run runs/kaggle/regeneration-output-v1/phase3-pilot \
  --output runs/phase4/regeneration-verification-v1.json
```

Outputs refuse overwriting. Full traces remain ignored; compact summaries and hashes are tracked. The private execution target is https://www.kaggle.com/code/ionrey/ace-pruningrag-bounded-regeneration.

## Research boundary

These previously inspected six cases are development data. Completing the execution and verification does not complete the full Phase 4 research gate: a reviewed held-out extension, genuine comparable cross-source conflicts, and independently reviewed semantic quality remain necessary. Keep costs, supported-price coverage, and abstentions visible together; a verifier that withholds everything is not a successful answerer.
