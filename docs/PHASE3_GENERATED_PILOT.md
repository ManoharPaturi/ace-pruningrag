# Phase 3: executed generated-answer comparison

This report covers an adapted development pilot, separate from the original PruningRAG paper reproduction and publication validation. Final run results will be filled after independent verification of the guarded float32 rerun.

## Frozen execution contract

- Same first 50 file-order questions from the immutable RM3QA 5-web release used in the existing protocol.
- Same Qwen2.5-1.5B-Instruct checkpoint/revision, hash-verified assets, system prompt, chat template, greedy generation, seed 42, and float32 precision for every policy.
- Fixed-web, all-available, and heuristic adaptive routing. Rotate which policy runs first across questions.
- At most 2,048 total model-request tokens, reserving 96 output tokens. Count the actual model chat template, question, timestamp, provenance headers, separators, and selected evidence. No silent truncation.
- Web BM25 pool: 120-word chunks, top 12 candidates, at most 5 selected items. Routing is isolated using the same top-K selection rule across policies. This is not the paper's released retriever or tokenizer pipeline.
- Original CRAG daily-price SQLite is immutable and hash-verified. A bounded executor supports one recognized Apple/AAPL, Microsoft/MSFT, or Tesla/TSLA entity when an actual row matches the question date. Other entities, multiple entities, unavailable dates, and unknown-date market-cap/ticker snapshots cannot silently become usable sources.
- Per-source budgets divide one shared evidence allowance. Selection checks each source allowance and the full final request. Backend lookup counts, shared price preflight lookups, and generation calls are recorded separately.

Inference uses only questions/timestamps/source evidence. Gold answers and alternate answers enter a separate post-generation exact-agreement check. Human review exports do not enter inference.

## Historical data finding

The original price snapshot is 136,196,096 bytes, SHA-256 `05fa78f8d319ae2a7f5990b50f8b6f1d17be1f650bf5fb814721e1fc2d4a56ac`. The three tested tickers have 252 daily rows, from 2023-02-28 through 2024-02-28. Their 2024-03-05 lookups return missing. This proves the limitation for those probes; it is not a proof of all ticker/date coverage or historical Dow membership. The Dow review case remains unresolved.

## Numerical failure and repair

Run version 1 executed 150 calls but every output consisted of 96 repetitions of token 0, decoded as punctuation. Its structural/token/provenance check initially passed; content inspection identified the failed generation. It is retained and explicitly excluded from quality evaluation. Because that run did not save logits, a numerical explanation is suspected rather than directly proven.

An intermediate version 2 was superseded after detecting that a metadata precision edit had not changed the loader. It is not admitted into evaluation. The guarded rerun changes the loader to float32, rejects non-finite model parameters, and checks generation scores on every decoding step. The independent verifier also requires the guarded float32 contract and rejects the all-token-zero failure pattern. Model/prompt/data choices remain fixed; no output-based answer tuning is performed.

## Metrics and boundaries

Exact agreement compares the trimmed, case-insensitive generated string with the supplied primary/alternate answers. It is a literal agreement measure, not semantic accuracy. Recognized "I don't know" responses are recorded as abstentions. Non-exact, non-abstaining answers remain pending semantic review; they are not automatically classified as hallucinations or incorrect answers.

Measure prompt/output tokens, actual source/model calls, retrieval/generation time, and model-loading time. Download/setup time is outside per-request latency. Small timing differences on identical prompts are runtime variation, not demonstrated routing savings. No paid API fees were incurred; Kaggle GPU quota is still a resource cost.

Semantic correctness, evidence completeness, unsupported-claim rates, a learned router's calibration, and cross-source superiority are not established by this pilot. The broader scientific Phase 3 gate remains open until date-compatible sources and independently reviewed evaluation labels support a paired quality/cost study.

## Reproduce

```sh
uv sync --locked --no-editable --extra generation
uv run --locked --no-editable ace-rag fetch-data
uv run --locked --no-editable --extra generation python scripts/generated_preflight.py --output runs/phase3/new-preflight
uv run --locked --no-editable python scripts/prices_smoke.py --output runs/phase3/new-price-smoke.json
uv run --locked --no-editable python scripts/build_kaggle_kernel.py --owner YOUR_KAGGLE_ACCOUNT --mode generation --output runs/kaggle/new-kernel
uv tool run --from kaggle==2.2.4 kaggle kernels push -p runs/kaggle/new-kernel -t 1800
```

The private GPU kernel contains only allowlisted first-party code and pinned configs. Raw human reviews, credentials, raw datasets, and weights are excluded. Inference packages install into an isolated directory in a fresh process; Kaggle's base package versions are checked before/after. Models run on one Tesla T4; the requested machine exposes two.

After downloading outputs, run `scripts/verify_generated.py` with the generation extra. It independently reconstructs selected evidence, checks source spans and budget counts with the pinned tokenizer, decodes generated token IDs, recomputes exact/abstention outcomes and summary statistics, and checks the numerical contract. A local readable review packet can be built with `scripts/build_generated_review.py`; all human decisions begin pending and its browser storage is bound to the trace hash.

Required CI covers unit tests, real-data/routing/selection smoke, all 150 real-tokenizer request preparations, and real dated-price probes. Large model inference runs on Kaggle and is independently verified; it is not silently simulated in CI.

## Sources

- Generator/model license and usage: https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct/tree/989aa7980e4cf806f80c7fef2b1adb7bc71aa306
- Original CRAG price API contract: https://github.com/facebookresearch/CRAG/blob/ad1518887dd4d9ebcd7de95388c7a62751e7705c/mock_api/cragapi/finance.py
- Full asset and prompt contracts: `configs/generated_pilot.json` and `configs/crag_prices.json`.
