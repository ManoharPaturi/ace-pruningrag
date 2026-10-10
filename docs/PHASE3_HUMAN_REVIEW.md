# Phase 3 generated-answer human review

The submitted review export covers all 150 generated answers: 50 development
questions under three policies. Every prediction and prompt hash matches the
verified float32 Kaggle v3 trace. The import preserves the original export and
notes locally; the public validation artifact contains counts and hashes only.

| Verdict | Fixed web | All available | Adaptive | Fraction per policy |
| --- | ---: | ---: | ---: | ---: |
| Correct | 13 | 13 | 13 | 26% |
| Incorrect | 23 | 23 | 23 | 46% |
| Abstained | 12 | 12 | 12 | 24% |
| Uncertain | 2 | 2 | 2 | 4% |

These are **50 distinct questions**, not 150 independent samples. All three
policies produced identical answers and received identical verdicts. Only web
sources were eligible in this pilot, so these results do not establish a routing
advantage.

The confirmed correct fraction is 26%. If both uncertain answers are ultimately
correct, it becomes 30%; unresolved answers remain uncertain rather than being
counted as incorrect. The earlier 8% literal-match result is a separate automatic
measure and is preserved in the original run summary.

The reviewer marked 15 answers supported, 23 unsupported, and 12 abstentions
not applicable per policy. Among the 38 non-abstaining answers, 23/38 (60.5%) were
marked unsupported. Correctness and evidence support are separate judgments.

## Uncertain questions

| Question | Review issue |
| --- | --- |
| Which player took home Grand Slam championship in 2017? | The question does not specify which tournament; the supplied Australian Open page supports Serena Williams, but other majors had other winners. |
| What were 3 of the most watched Halloween movies of all time? | The titles occur in the supplied lists, but the evidence does not establish comparative viewing counts. |

Both remain unresolved in the imported record. This is a reviewed development
pilot, not a held-out publication result or an original PruningRAG reproduction.
The broader Phase 3 gate still requires a date-compatible API evaluation and a
comparison in which policies can choose genuinely different source combinations.

## Reproduce the import

Run from the repository root, using a new output directory each time:

```sh
uv run --locked --no-editable python scripts/import_generated_review.py \
  --export /path/to/ace-generated-answer-review-2026-10-10.json \
  --predictions runs/kaggle/generated-output-v3/phase3-pilot/generated/predictions.jsonl \
  --output runs/phase3/generated-human-review-import-v1
```

The importer rejects unknown or duplicate query-policy pairs, changed answers or
prompt hashes, missing attestation, invalid verdicts, and false abstentions. It
reports missing reviews and uncertainty explicitly and refuses to overwrite an
existing import directory. The prediction trace must already have passed the
independent generated-run verifier; this importer checks the review binding.

The original export SHA-256 is
`43095c2af919cc272194841875597fef9e28794f1c79dbcdb0adccc7f0d47863`.
The prediction trace SHA-256 is
`6858c1e0a46cbe7acc4d7306ee0a29706aa2afa52cc89892bd5f54f9c6ef4827`.

Local preserved records: `runs/phase3/generated-human-review-import-v1/`.
Public compact results: `results/phase3/generated_pilot/human_review_validation.json`.
