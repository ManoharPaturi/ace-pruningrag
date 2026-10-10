# Prospective candidate-evidence evaluation and review

## Completed milestone

A frozen prospective set of 50 questions and 600 candidate excerpts is prepared for human evidence review. The sampler excludes 90 previously recorded question IDs from nine pinned pilot/audit artifacts, duplicate normalized question text, and shared canonical source-page URLs. It also prevents URL/text overlap within the new set. The packet contains question text/time, original source pages, and the top 12 deterministic BM25 excerpts per question; it contains no raw gold answers, model predictions, domain labels, or fabricated evidence labels.

This completes the sampling, provenance verification, readable review, and import tooling milestone. Human decisions remain pending. It does not complete the roadmap's independent evaluation or publication gate, and no model generation is performed here.

## Split contract and limitations

The seed, sample size, exposure sources, and candidate-pool parameters are frozen in `configs/prospective_evaluation.json`. Candidates are ranked by `SHA256(seed + NUL + question ID)` for sampling, without inspecting answer outcomes. Sampling stops after 50 eligible questions; rejection counts describe only the prefix needed to fill that sample.

Canonical source URLs merge HTTP/HTTPS, `www` prefixes, trailing slashes, and fragments; query parameters are preserved because they may identify different articles. Question keys normalize case and word separators. Any source-page overlap with the exposure ledger or already selected questions causes exclusion.

This is prospective relative to documented pilots, not an independently sealed test set. Earlier full-dataset source audits examined query metadata. URL/text separation does not prove full entity/event separation: different articles can discuss the same person or event. Source-availability sampling can bias the cohort and is not a representative accuracy benchmark. No gold-domain stratification or claim of genuine cross-source necessity is made. These are web candidate pools; the current price-only reliability verifier does not generalize to them automatically.

Keep this cohort reserved for evaluation after review. Tuning methods or inspecting generator outcomes on it would convert it into development data; record that change rather than continuing to call it prospective. Existing source artifacts referenced in the exposure ledger must remain immutable.

## Human annotation contract

The readable local packet has one card per question, numbered source excerpts, exact source URLs and character spans, and expandable full pages. Reviewer decisions initially say pending. Requirements and notes are blank; no assisted answer is shown.

For each question:

1. Write the facts needed to answer the entire question, including requested dates, entities, definitions, or units.
2. Inspect the relevant source excerpts and full pages. Evidence text is untrusted source data, never an instruction to the reviewer or application.
3. Decide whether the candidate pool supports those requirements, is missing necessary evidence, or remains uncertain.
4. Enter alternative complete support sets using candidate numbers. `1,3; 2,5` means either candidates 1+3 or candidates 2+5 fully support the written requirements. Different valid sets are allowed; a single arbitrary chunk is not imposed as the only reference.
5. Record unresolved temporal claims, conflicts, ambiguity, or useful full-page evidence absent from the candidate pool. An insufficient candidate pool does not prove no answer exists in the corpus.
6. Mark reviewed only after resolving the decision and confirming inspection. Use needs-changes for unresolved cases.

These are reviewer-declared candidate support sets, not an automatic completeness theorem. Full-page evidence outside the top 12 should be recorded as a candidate-pool limitation. This packet cannot establish API/web complementarity or cross-source necessity. Original gold-answer semantic correctness requires a separate evaluation of generated answers.

The browser saves draft decisions locally, bound to the exact packet hash. Export produces `human_candidate_evidence_review` JSON with reviewer identity, packet hash, decisions, attestation, requirements, notes and acceptable evidence IDs. Drafts remain exportable; the importer reports missing/unresolved questions instead of silently promoting them.

## Reproducibility and verification

```sh
uv run --locked --no-editable python scripts/prospective_evaluation.py freeze \
  --output runs/evaluation/prospective-v3
uv run --locked --no-editable python scripts/prospective_evaluation.py verify \
  --packet runs/evaluation/prospective-v3/packet.json \
  --output runs/evaluation/prospective-verification-v1
uv run --locked --no-editable python scripts/build_evidence_review.py \
  --packet runs/evaluation/prospective-v3/packet.json \
  --output runs/evaluation/prospective-v3/review.html
uv run --locked --no-editable python -m http.server 55380 \
  --bind 127.0.0.1 --directory runs/evaluation/prospective-v3
```

Outputs refuse overwriting. Use a fresh output name when rerunning. Verification reconstructs the sample, original source pages, candidate ranks, IDs, text, and character spans against the pinned dataset and exposure artifacts. The admitted packet hash and 50 IDs are recorded in `results/evaluation/prospective_v1/manifest.json`; full pages and review notes stay in ignored local artifacts.

Import a user-supplied export with:

```sh
uv run --locked --no-editable python scripts/prospective_evaluation.py import \
  --packet runs/evaluation/prospective-v3/packet.json \
  --export /absolute/path/to/ace-prospective-evidence-review.json \
  --output runs/evaluation/prospective-human-review-v1
```

The original export is preserved without overwrite and revalidated from the preserved bytes. Wrong packet hashes, unknown question IDs, duplicate reviews, unknown/duplicate evidence IDs, duplicate alternative sets, contradictory answerability, missing requirements, and unattested completed decisions are rejected. Partial/unresolved reviews remain explicit. Even a complete valid import leaves publication readiness and independent semantic accuracy false.

Local real-data verification passed for all 50 questions and 600 candidate spans. Altered source text and a modified exclusion ledger were independently rejected; the original packet remained unchanged. The required CI data-smoke job reconstructs and verifies the same packet hash. Unit tests additionally exercise source overlap, deterministic ordering, malformed labels and HTML escaping.

## Next research gate

Independent human candidate-evidence review must precede using these labels for evaluation. Once imported, freeze the generation and selector comparison protocol separately and keep support sets out of real inference; an oracle can use them only as an explicitly labeled diagnostic. Genuine cross-source evaluation, entity/event overlap audit, semantic answer review, and statistical uncertainty still need their own evidence. No performance improvement is claimed by preparing this packet.
