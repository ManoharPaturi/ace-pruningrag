# Phase 3: routing and shared budget engineering

Status: engineering layer implemented and audited. The roadmap's scientific completion gate is open: no quality/cost trade-off has been measured. Phase 1 original reproduction and Phase 2 held-out evidence/answer evaluation also remain incomplete.

## What changed

The router accepts only `QueryInput`: question identity, text, time, and web search results. Gold answers, release domain/split fields, reviewed annotations, and model correctness labels are absent. Its source scores are deterministic keyword counts, not trained classifications, calibrated probabilities, or verified source-necessity labels.

Three policies share one total token allowance:

- `fixed_web` assigns the usable evidence allowance to web, if available.
- `all_available` divides that allowance equally across eligible capabilities.
- `adaptive` selects eligible capabilities suggested by query keywords and divides the allowance in proportion to keyword-match counts. Web always receives a request hint.

Allocation uses integer largest-remainder rounding with source-name tie breaks. A 1,536-token total with a 256-token reserve leaves 1,280 evidence tokens across all selected sources, rather than 1,280 for each source. This reserve is a planning parameter; no generator prompt is fixed, so it does not establish that a real complete model request fits. Zero-budget sources are removed. A plan records at most one planned call per allocated source; actual API/LLM call counts remain separate. This planner has no execution or re-retrieval loop.

Keyword hints include market capitalization, tickers, prices, sports statistics, movies, and company history. Historical market-capitalization requests are routed toward time-series capability rather than the single-value market-cap slice. The vocabulary is intentionally narrow and unvalidated; missing a keyword can miss a relevant source. A blocked hint does not prove web evidence cannot answer a question or that that API is necessary.

## Availability and dates

Capabilities are an explicit configured inventory, not a live service-health check. The existing finance slice is backed by verified historical assets, but those assets do not establish an as-of date matching a question. A capability requiring temporal alignment is excluded when its date is unknown or differs from the question date. Date agreement is a necessary planner check, not certification of intraday alignment, source correctness, or comprehensive historical coverage. Web's availability does not establish temporal validity of every retrieved page.

The current inventory declares web plus the two original finance lookup capabilities. Both finance dates are unknown. Daily historical prices, finance time series, sports statistics, movie knowledge, and company history APIs are not provisioned. These omissions are explicit blocked hints; no substituted source or invented response is used.

## Genuine-input audit

Configuration: `configs/routing_smoke.json`. Input: all 2,706 questions from the same immutable RM3QA 5-web dataset, in release order. This is a planning audit, not a held-out model evaluation or training pass.

The runner produced 8,118 plans. An independent verifier reconstructed query identities/time/text from the pinned file, verified all budgets and source eligibility, checked actual execution counters remained zero, and checked trace integrity and summary counts.

All three policies had equivalent usable allocations for all 2,706 queries: only web was eligible under the current inventory/time requirements. **No adaptive advantage or savings were observed or inferred.** Actual source calls: 0; actual LLM calls: 0. Accuracy is unset.

Blocked keyword hints included: 106 finance-price requests; 50 market-cap requests with unknown snapshot date; 4 finance time-series requests; 2 ticker requests with unknown snapshot date; 318 movie-knowledge requests; 7 company-history requests; and 5 sports-statistics requests. These overlap across questions and are not validated domain counts or recall measurements.

Full traces and the complete ID list stay in ignored `runs/phase3/routing-v1`. `results/phase3/` contains compact summaries, source/config/data hashes, and a hash of the ordered query-ID list. CI's required `data-smoke` job reproduces the audit and independently verifies it.

## Review import

`ace-rag import-review` validates a user-exported review file against the genuine pinned dataset. It checks unique query identities, draft questions, explicit decision/validation consistency, inspection flags, required attestations for approved drafts, source URLs, and exact text spans. It preserves the original bytes in a new directory and refuses overwriting an existing import.

The real five-question export passed: three drafts marked reviewed, two needing changes, and 20 verified source references. The original notes and raw export remain in ignored local artifacts. A compact validation report records the export hash and decisions. This is validation of the supplied review records and their provenance; it is not identity authentication or proof of independent blind review.

Human approval of these AI-assisted drafts does not supply complete requirement-to-evidence labels or acceptable alternative support sets. The importer explicitly reports those labels unavailable and leaves the evaluation gate open. Review files are never inputs to routing or selection.

## Reproduce

```sh
uv sync --locked --no-editable
uv run --locked --no-editable ace-rag fetch-data
uv run --locked --no-editable ace-rag routing-smoke --output runs/phase3/new-routing-run
uv run --locked --no-editable python scripts/verify_routing.py --run runs/phase3/new-routing-run
uv run --locked --no-editable ace-rag import-review --export /absolute/path/to/export.json --output runs/phase3/new-review-import
```

No new model weights, GPU runs, API credentials, or paid experiments were needed. Tests cover fixed/adaptive allocations, shared budget conservation, deterministic rounding, unknown/mismatched dates, unavailable sources, gold-field isolation, provenance tampering, missing attestations, contradictory flags, and immutable review import.

## Completion gates still required

Before declaring scientific Phase 3 complete, provide date-compatible source services and labels, freeze a generator and complete request-token accounting, finish a sufficiently reviewed development/held-out evidence protocol, and execute paired fixed/all-source/adaptive runs at matched total budgets. Report generated-answer quality, unsupported claims, abstention/coverage, actual source/model calls, and costs together. Keep neutral and negative results.

The two reviewed missing-evidence cases remain unresolved: the movie query needs an explicit character/device/film relation, and the Dow query needs historical daily prices and constituent membership. A planning hint is not a successful retrieval for either question. Phase 4 sufficiency/conflict/verification research depends on these evaluated inputs; this PR makes no claims about that phase.
