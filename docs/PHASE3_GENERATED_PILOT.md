# Phase 3: executed generated-answer comparison

This report covers an adapted development pilot, separate from the original PruningRAG paper reproduction and publication validation. The guarded float32 run is complete and independently verified. The executable pilot is complete; the broader scientific/publication gate remains open.

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

## Verified results — Kaggle version 3

The genuine run generated 150 answers: 50 questions under each of three policies. All 150 outputs passed independent source-span, prompt-token, decoding, budget, numerical-contract, and summary-statistic checks. All submitted bundle hashes match the recovered bundle and current execution source. Kaggle base package versions were preserved.

| Policy | Exact agreement | Abstained | Semantic review pending | Mean generation | Mean retrieval |
| --- | ---: | ---: | ---: | ---: | ---: |
| Fixed web | 4/50 (8%) | 12/50 (24%) | 34/50 | 2.093 s | 0.237 s |
| All available | 4/50 (8%) | 12/50 (24%) | 34/50 | 2.083 s | 0.239 s |
| Adaptive | 4/50 (8%) | 12/50 (24%) | 34/50 | 2.087 s | 0.240 s |

All 50 questions had identical prompts and predictions across policies because only web was eligible for evidence execution. Therefore this run shows **no measured answer-quality advantage** for adaptive routing under the available-source constraint. The small timing differences are runtime variation. Exact agreement is not an 8% semantic-accuracy claim: punctuation, equivalent names, or valid paraphrases may remain among the 34 pending judgments, as may incorrect or unsupported answers.

Mean prompt tokens: 1,511.46. Mean generated tokens: 15.32. Maximum actual prompt plus output: 1,938 of 2,048. Maximum prompt plus reserved output allowance: 2,028. Actual benchmark calls: 150 web retrievals, 150 generations, zero finance evidence calls. Two shared price-eligibility lookups occurred before policy execution; the price audit also probes historical rows. Model loading took 6.865 seconds, reported separately. The requested machine exposed two Tesla T4 GPUs; this small float32 model ran on cuda:0.

Full predictions and logs remain under ignored `runs/kaggle/generated-output-v3`. Compact reports and immutable contracts are in `results/phase3/generated_pilot`. The earlier failed and superseded submissions remain separate; version 1's failure summary is tracked and its zero-agreement result is excluded from evaluation.

## Prespecified first-five failure analysis

The first five questions were reviewed before generation. The following is AI-assisted analysis against that earlier review, not new human grading of model outputs; the 34 non-exact results remain pending in the formal metrics.

| Question | Generated output | Diagnostic finding |
| --- | --- | --- |
| Nash 3-point attempts | `14.2` | Does not match the previously reviewed seasonal 3PA values; a quantity/statistic mismatch. |
| Movie/person/device | Speculative list of films, cut off at the output cap | Does not establish the requested relation from the inspected evidence; violates the intended concise/abstention behavior. |
| Salesforce CEO's previous employer | `Salesforce previously worked at Informatica.` | Confuses the requested person/employer relation and disagrees with the reviewed Oracle reference. |
| 2021 Visual Effects Oscar | `'Tenet'` | Matches the reviewed ceremony-year answer semantically, but quotes prevent literal agreement; this illustrates why 8% is not semantic accuracy. |
| Dow daily winner | `SPDR Dow Jones Industrial Average ETF (DIA)` | An ETF is not a constituent company, and its mention does not establish historical daily performance. |

Finite numerical inference does not establish grounding. These cases motivate later source sufficiency, entity/type checks, and independently graded verification; they do not support a claim that reliability is solved.

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
