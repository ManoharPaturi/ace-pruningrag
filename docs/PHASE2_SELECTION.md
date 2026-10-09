# Phase 2: evidence selection implementation

Status: engineering milestone implemented; scientific completion gate remains open.

The original Phase 1 paper reproduction remains blocked on its router, complete API data, and generator/judge contract. This Phase 2 implementation can be developed independently; it does not establish that those blockers are resolved.

## Shared inputs and selectors

`selection.py` accepts web or API evidence with an immutable identity, content, source reference, normalized relevance, and a vector of **predicted** requirement support. Requirements, groups, similarity, and compatible conflict features must come from inference inputs. Gold answers or reviewed support labels belong in a separate evaluation process.

All methods use the identical candidate pool, context renderer, item limit, and context-cost callback:

- Top-K selects the highest relevance that fits.
- MMR balances relevance against the largest similarity to already selected evidence (`lambda=0.7`).
- Coverage-only adds items with positive marginal predicted requirement coverage.
- Joint selection examines both single-item and pair additions and stops when neither has positive marginal objective gain.
- Exact search enumerates every affordable subset up to the item limit, for at most 14 candidates. It is an upper bound for the configured experimental objective, not an oracle for evidence truth or answer quality.

The objective is `F(E) = 0.2 R(E) + 0.6 C(E) + 0.2 J(E) - 0.1 D(E) - 0.5 X(E)`.

`E` is a selected evidence set. `R` is summed relevance divided by the maximum item count. `C` is mean maximum support across predicted atomic requirements. `J` is the fraction of predicted requirement groups fully covered across the set but not covered by any single selected item. Full group coverage currently means support exactly 1 for every atomic requirement; soft scores below 1 do not certify group completion. `D` and `X` sum pair redundancy and compatible conflict scores, divided by the maximum pair count. Features lie in [0,1]; weights are provisional engineering values, not tuned scientific parameters.

Different source kinds alone create no complementarity bonus. The pair mechanism is tested with a web entity lookup and an API value lookup in a synthetic fixture. That fixture validates implementation behavior; it is not a research observation. Adding one item that covers an entire group can remove its complementarity bonus, so the objective need not be monotone. No approximation guarantee is claimed.

Contexts render in evidence-ID order with identity/source headers. The cost function counts that full representation for each proposed subset; it does not sum individual chunk lengths or assume tokenization is additive.

## Real-input smoke and limitations

Configuration: `configs/selection_smoke.json`. Same pinned RM3QA 5-web input as Phase 1; first 25 file-order questions, top 10 BM25 candidates, 200-word chunks, at most 3 evidence items and 1,536 evidence-context tokens. Tokenization uses the hash-verified BGE-M3 tokenizer at the recorded revision. This is an engineering tokenizer contract; generator prompts, chat wrappers, query, special tokens, and output allowance must be budgeted separately once a generator is selected.

The real run uses query terms (minus a fixed stopword list) as lexical proxies. Support is term occurrence; redundancy is word-set Jaccard overlap. **Neither is validated evidence relevance or support.** Genuine requirement groups and conflict features are empty in this real smoke, so complementarity and conflict are disabled. This run therefore exercises shared budgets, selection, and coverage/redundancy proxies on genuine inputs, not the full scientific contribution.

Independent verification reconstructed candidate evidence from the pinned raw pages, checked original character spans, recomputed support and relevance, retokenized every selected context, recomputed objectives, and independently enumerated the exact optimum. It verified 25 questions and 125 contexts. Every method stayed below 1,536 tokens. Maximum observed contexts: top-K 1,518; MMR 1,518; coverage 1,254; joint 1,518; exact 1,518. The maximum observed exact-minus-joint objective gap was 0.0035678879972170785; this heuristic limitation is retained. Maximum budget is shared, but realized context lengths differ. These are not comparisons of answer quality at identical realized token counts.

No LLM calls, answers, accuracy, evidence-completeness labels, or paper metrics were produced. This run is CPU suitable and required no new Kaggle GPU run. Full traces stay in ignored `runs/phase2/selection-v1`; compact summaries/manifests are under `results/phase2/`.

## Reproduce

```sh
uv sync --locked --no-editable --extra selection
uv run --locked --no-editable ace-rag fetch-data
uv run --locked --no-editable --extra selection ace-rag fetch-selection
uv run --locked --no-editable --extra selection ace-rag selection-smoke --output runs/phase2/new-run
uv run --locked --no-editable --extra selection python scripts/verify_selection.py --run runs/phase2/new-run
```

The optional selection dependency adds the tokenizer runtime; large model weights are not required. Existing immutable asset fetching verifies the 17,098,108-byte tokenizer against its pinned SHA-256. New runs refuse to overwrite previous directories. CI's existing `data-smoke` job now includes this real selection run and independent verifier.

## Remaining gates before later phases

1. Independent human review of real questions, requirements, acceptable supporting evidence, alternative sources, temporal compatibility, and source necessity. Start with 50–100; source names and term occurrence cannot replace these labels.
2. Freeze development/held-out query IDs, predictor provenance, a generator/tokenizer/prompt, and separate evaluation records. Keep evaluation labels out of prediction and selection.
3. Implement and evaluate real API candidate retrieval and requirement/group predictions. Compare selected evidence and generated answers on fixed candidates, including negative results.
4. Only then measure adaptive routing/budgets, sufficiency loops, conflict handling, and claim verification as separate ablations. The current framework is a basis for these phases, not evidence that they work.
