# Completed cohort response audit — 13 October 2026

All **250 answers / 50 shared questions / five selectors** have source-bound AI assessments. Eleven private batches validate against trace SHA-256 `f4bdcdcdd6de097ec9ae46ceacf9cc1d1251285bdababac82467d42780003e73`. This completes the AI source audit of the accepted cohort, not independent human evaluation or the five-phase research roadmap.

## Method diagnostics

| Method | Correct under recorded interpretation | Incorrect | Uncertain | Abstained | Reviewed / expected |
| --- | ---: | ---: | ---: | ---: | ---: |
| top_k | 9 | 17 | 11 | 13 | 50 / 50 |
| mmr | 9 | 13 | 10 | 18 | 50 / 50 |
| coverage | 5 | 15 | 11 | 19 | 50 / 50 |
| joint | 9 | 11 | 11 | 19 | 50 / 50 |
| exact | 9 | 12 | 10 | 19 | 50 / 50 |

**Totals:** 41 correct, 68 incorrect, 53 uncertain and 88 abstained. Four prose abstentions were missed by the preserved exact-string metric. Eighteen questions have identical predictions across every method. The 250 responses are repeated measurements of 50 questions; they are not independent samples.

Counts are AI-assisted judgments with case-specific interpretations. Uncertain responses include ambiguous wording, unsupported comparisons and unresolved truth, and remain separate from errors. Abstention is a behavior, not proof that declining was necessary: all Charles Jarrott variants decline despite selected text giving his birth date. Correct answers may still lack complete selected support, as in the Wizard of Oz/Lion King comparison.

Coverage consumes fewer input tokens but has only five AI-correct responses versus nine for each other method. Joint has fewer AI-incorrect responses than top-K, alongside more abstentions; it does not increase the AI-correct count. These observations do not identify a validated winner. Complete support annotations, paired human outcomes and genuine cross-source controls remain missing.

## Findings that drive implementation

1. **Answer shape and relation:** sector weights are not ten stock holdings; an artist is not a song; an older brother identity is not his age. Federation aliases are not distinct bodies, and championship team counts are not federation membership counts.
2. **Aggregation and time:** career wins are not annual wins; all-time championships are not decade counts; artist-wide certified sales are not one album. A generic quote is not a dated opening-price field. Selected source updates can occur after the question.
3. **Arithmetic and complete comparisons:** the rectangular-room calculation fails for every selector; other questions lack the second measurement or a complete qualifying universe. Ranked vacation lists do not establish largest lakes.
4. **Provenance versus content:** four outputs consist entirely of evidence identifiers. Retain raw outputs, but a future acceptance gate should reject identifiers as substantive answers and report why.
5. **Source quality and relevance:** the Louvre question receives dog-breed sources. Navigation text and conflicting informal height claims survive selection. A copied statement can be grounded yet factually wrong.
6. **Premise checks:** the Bananas naming date and an exhibition date do not establish MLB membership. First-for-one-character does not establish first across film history.
7. **Time-sensitive adjudication:** Beijing medals require an original-event versus later-reallocated interpretation. The selected Tokyo gold totals cannot answer Beijing.

The Olympic audit keeps original U.S. eight-gold results separate from the January 2024 figure-skating gold award and China’s nine golds. Thus a March 2024 question can differ from the original closing-day comparison; the coverage answer remains uncertain rather than silently treating an old table as current. Primary review sources: [Team USA original results](https://www.teamusa.com/news/2022/february/20/team-usa-delivers-world-class-performances-to-earn-25-medals-at-tthe-olympics), [Team USA January 2024 award](https://www.teamusa.com/news/2024/january/31/after-two-year-wait-team-usa-figure-skaters-are-awarded-olympic-gold), [Chinese Olympic Committee](https://en.olympic.cn/news/Olympic_News/2022/0221/622291.html). External checks stay outside frozen inference inputs.

## Reproduce aggregation

Obtain the exact private trace and eleven audit batches from the owner. Then run from the repository root, choosing a new output path:

```bash
uv run --locked --no-editable python scripts/summarize_response_audit.py \
  --trace runs/kaggle/cohort-output-v1/cohort-pilot/generated/predictions.jsonl \
  --audits runs/version1/cohort-ai-audit-batch*.json \
  --output runs/version1/cohort-ai-summary-reproduced.json
```

The summarizer validates every binding before counting, rejects tampered or duplicate assessments, retains pending/uncertain/abstained categories, counts distinct questions separately, and records batch hashes. It refuses overwriting an existing output. Compact tracked evidence: [coverage](../results/version1/cohort/ai_review_progress.json), [method summary](../results/version1/cohort/ai_method_summary.json), [GPU verification](../results/version1/cohort/verification.json), [costs and frozen diagnostics](COHORT_SELECTOR_RESULTS.md).

## Accepted-version scope

With 150 legacy records and 44 historical/regeneration records previously audited, all **444 admitted accepted response records** now have AI assessments. Failed/superseded runs remain preserved and excluded. The original human development labels are unchanged. Prospective independent human evidence/answer review, faithful reproduction, complete cross-source evaluation, general reliability, final ablations/report and live inference remain open gates. The [next-version plan](VERSION2_PLAN.md) retains them explicitly.
