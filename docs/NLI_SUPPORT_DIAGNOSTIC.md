# Independent textual-support diagnostic: completed, not promoted

Updated 13 October 2026. A separate DeBERTa classifier was executed over every selected source/answer pairing in the frozen 250-response cohort. This is one component investigation for claim verification; entity/date/unit and full-query requirements still need their own contracts.

## Protocol and provenance

Model: `cross-encoder/nli-deberta-v3-base`, immutable revision `6c749ce3425cd33b46d187e45b92bbf96ee12ec7`. Its [official model card](https://huggingface.co/cross-encoder/nli-deberta-v3-base) specifies contradiction, entailment and neutral scores for text pairs. The pinned model config confirms that label order. [Asset/protocol config](../configs/nli_diagnostic.json) fixes checksums, float32, batch size 16, a 512-token pair cap and at most 1,250 comparisons / 79 forward calls. Declared assets total 748,853,347 bytes under the 760 MB cap.

Inputs are exact selected source text as premise and the actual unchanged answer as hypothesis. Query/time/identity are bound as metadata, but the classifier does **not** receive or evaluate the question. No gold answers, human support sets or AI judgments enter the model. This deliberately tests the limits of unframed support scoring; it does not silently equate copied text with a correct answer.

Kaggle normalized the first submitted title to `ionrey/ace-bounded-nli-source-diagnostics`, version 1, instead of the requested UUID slug. The returned notebook URL was followed without resubmission; [submission record](../results/version1/nli_submission.json) preserves both identities. The builder now emits matching unique titles/IDs, covered by a regression test. Existing kernels were not overwritten.

## Actual execution and verification

| Measure | Recorded value |
| --- | ---: |
| Source/answer comparisons | 1,105 |
| Scored pairs | 1,089 |
| Over-budget, unscored pairs | 16 |
| Classifier forward calls | 69 |
| New answer-generation calls | 0 |
| Unpadded scored pair tokens | 208,761 |
| Padded classifier input tokens | 329,035 |
| Model loading | 4.48 s |
| Classifier execution | 26.26 s |
| Model labels | 78 entailment / 203 contradiction / 808 neutral |

Execution used Tesla T4, torch 2.11.0+cu128, float32, guarded finite parameters/logits and isolated pinned inference packages. Timings exclude queueing, download, installation, tokenization and verification. Long pairs were explicitly unscored; none were silently truncated to produce a label.

[Independent reconstruction](../results/version1/nli_verification.json) checks submitted code/content hashes, all exact source/answer pair bindings, token counts, caps, label mapping/argmax and cost totals. Model logits were **not** independently recomputed. This verifies accounting and provenance, not classifier accuracy or world truth. Raw output remains private in `runs/version1/nli-output-v1/nli-pilot/`.

## Why raw entailment cannot accept an answer

At least one source pair received an entailment label for 57 of the 250 responses. Of these, prior AI source review classified 21 correct under its recorded interpretation, 27 incorrect and nine uncertain. Another 20 AI-correct responses had no entailment label. These are different targets, shared questions and AI assessments; this is not a precision/recall estimate or independently validated accuracy.

The 27 AI-incorrect responses with raw entailment span seven distinct questions, including:

- A supported Gunna transfer rumor substitutes for the founder's latest album.
- Artist/annual-chart text substitutes for the requested song/daily-chart result.
- Historical playoff format substitutes for current qualifying team identities.
- A portfolio percentage and three names substitute for ten dated holdings; sector weights also receive raw entailment.
- An explicitly later generic quote substitutes for a historical opening-price field.
- An all-time championship total substitutes for the requested decade count.
- An unrelated song title appears in source text but is outside the requested comparison pair.

[Development comparison](../results/version1/nli_review_comparison.json) binds the examples to their exact method/evidence identities. These findings leave semantic answer acceptance disabled. Calibration alone cannot supply missing query requirements: the hypothesis must represent the requested entity, relation, period, unit, comparison operands and completeness, with uncertainty retained when extraction or support is incomplete.

## Reproduce reconstruction

Obtain the submitted private bundle, outputs and exact cohort trace, then use the submitted source version and locally cached NLI tokenizer/config sidecars:

```bash
uv run --locked --no-editable --extra generation python scripts/verify_nli_diagnostic.py \
  --bundle runs/version1/nli-kernel-v1 \
  --run runs/version1/nli-output-v1/nli-pilot \
  --source-trace runs/kaggle/cohort-output-v1/cohort-pilot/generated/predictions.jsonl \
  --output runs/version1/nli-reconstruction-reproduced.json
```

The tokenizer sidecars total approximately 11 MB; large weights execute on Kaggle. Originals, accepted generator outputs and human labels remain unchanged. Unit tests cover label exclusion, input binding, finite logits, token caps, non-promotion and the title/slug regression. There are 159 passing local tests; Ruff lint/format and diff checks pass.

## Next implementation gate

Implement query-only requirements and explicit structured entity/field/date/unit bindings before using a support model in acceptance. Frame concise answers into auditable claims without importing answer keys; retain raw outputs and count every extraction/classifier/retrieval call. Evaluate the combined path with fresh reviewed cases, source-only controls and separately stated human/AI labels. General claim verification, cross-source scientific validation and final research packaging remain open.
