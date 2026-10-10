# Date-compatible API feasibility audit

The next routing comparison needs relevant API evidence. A full scan of all
2,706 pinned RM3QA questions finds that the current three-company price executor
cannot provide that comparison:

| Check | Questions |
| --- | ---: |
| Price-related keyword hint | 106 |
| One recognized Apple/Microsoft/Tesla entity | 44 |
| Recognized entity with a same-date price row | 2 |
| Same-date price row and a price-related question | **0** |

The two same-date cases concern Microsoft Office languages and the CEO's age.
An all-available policy could retrieve an irrelevant Microsoft price row, while
an adaptive policy would omit it. That is a potential cost/distractor diagnostic,
not a comparison of relevant cross-source answer evidence.

The audit also finds **35 expansion candidates** with a single matching ticker
word of at least three characters, a price keyword hint, and a same-date row in
the original SQLite. This is candidate discovery, not a validated executor or
new benchmark. Exact word matching still produces entity ambiguities such as
`FUND`, `FOUR`, and `BDC`, and shorter tickers are deliberately omitted. A single
candidate does not prove the question mentions only one company.

## Next execution contract

1. Resolve the entity and requested period from the question without gold labels.
   Reject ambiguous company names and multi-company questions until supported.
2. Retrieve the requested historical day/range rather than substituting the
   question's current date. Preserve currency, units, row timestamps, asset hash,
   and any missing-date status.
3. Enforce availability at the question timestamp. Completed daily OHLC rows
   must not reveal a later same-day closing/high/low price to a morning question.
   A daily-price snapshot cannot establish the latest intraday quote.
4. Freeze accepted development query IDs before generation; use the same model,
   selection method, and total token budget across policies. Keep rejected and
   missing-source cases visible, and disclose selection bias.
5. Independently verify API responses, selected provenance, final prompts, token
   budgets, and paired source/model calls, then review actual generated answers.

No new GPU run was launched from these candidates. The source/date preparation
must pass before another run can measure a meaningful routing difference. The
existing first-50 generated run and its human review remain separate.

## Reproduce

```sh
uv run --locked --no-editable ace-rag fetch-data
uv run --locked --no-editable python scripts/prices_smoke.py --output runs/new-prices.json
uv run --locked --no-editable python scripts/price_eligibility_audit.py \
  --output runs/new-price-eligibility.json
```

The scanner receives only `QueryInput` values containing question, timestamp,
ID, and web inputs. Answers, domains, dataset splits, and human verdicts do not
select candidates. Both dataset and price asset hashes are checked first.
The script refuses to overwrite earlier reports. Candidate question text stays
in the local report; the public report retains IDs, ticker candidates, counts,
limitations, and input hashes.

The required finance-smoke CI job now repeats this full pinned-data audit and
uploads its report alongside the original dated-price probes.
