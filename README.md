# ACE-PruningRAG

Adaptive cross-source evidence selection for multi-source retrieval-augmented generation.

The research hypothesis is that selecting complementary web/API evidence jointly can improve complete evidence coverage and grounded answers under a fixed token budget. This repository begins with a pinned PruningRAG setup audit and real RM3QA data validation. No research improvement or full baseline reproduction is claimed yet.

The revised roadmap was approved on 9 October 2026. See [the review](ROADMAP_REVIEW.md), [original roadmap](ACE_PruningRAG_5_Phase_Research_Roadmap.pdf), [evaluation protocol](docs/EVALUATION_PROTOCOL.md), and [reproduction report](docs/REPRODUCTION_REPORT.md).

Phase 1 status: 26 tests pass; the pinned 2,706-record dataset validates; the 25-query retrieval smoke passes locally and on dual T4 Kaggle GPUs. Full PruningRAG reproduction remains blocked. Implementation changes go through PRs with required `test` and `data-smoke` checks.

## Quick start

Install Python 3.12 and [uv](https://docs.astral.sh/uv/). Run from the repository root:

```bash
uv sync --locked --no-editable
uv run --no-editable ace-rag fetch-upstream
uv run --no-editable ace-rag fetch-data
uv run --no-editable ace-rag profile-data --output runs/phase1/dataset_profile.json
uv run --no-editable ace-rag audit-upstream --output runs/phase1/upstream_audit.json
uv run --no-editable ace-rag smoke --output runs/phase1/bm25-smoke
```

The audit intentionally exits 2 when reproduction is blocked or unverified, and writes its findings before exiting. The smoke refuses to overwrite an existing run directory. Dataset downloads are approximately 65 MB and verified against a pinned SHA-256. No API key or model-weight download is required for these commands.

Use a non-editable package install on this Mac: Python skips `.pth` files carrying inherited Finder hidden flags. The source cache key causes uv to rebuild after Python source changes. This avoids changing system Python settings.

## Checks

```bash
uv run --no-editable ruff check src tests scripts
uv run --no-editable ruff format --check src tests scripts
uv run --no-editable pytest -q
```

## Implementation

- Strict JSONL/bz2 loader with numeric/text answer normalization and no silent row skipping.
- Separate inference inputs exclude gold labels and answers.
- Immutable evidence records preserve URL, title, time, original field, and exact character spans.
- Independent BM25 retrieval smoke with deterministic ties and bounded context.
- Pinned upstream checkout and static audit without importing large model dependencies.
- Configuration, source/data hashes, query IDs, and per-query trace artifacts.
- [Private Kaggle bootstrap](docs/KAGGLE.md) for remote GPU readiness.

Raw datasets, model weights, credentials, caches, and full traces are ignored. Compact result artifacts live under `results/phase1`. The untouched upstream checkout lives under `.cache/upstream/PruningRAG` and is not vendored.

## Research sequence

1. Reproduction feasibility, evaluation protocol, and baseline.
2. Joint evidence selection against independent top-K, MMR, and coverage-only selection.
3. Adaptive routing and retrieval budgets.
4. Conflict handling, sufficiency, claim verification, and reviewed hard evaluation.
5. Full ablations, research package, and FastAPI/Next.js demo.

Original resources: [PruningRAG code](https://github.com/USTCAGI/PruningRAG), [paper](https://arxiv.org/abs/2409.13694), and [RM3QA dataset](https://huggingface.co/datasets/fishsure/RM3QA). Upstream code reuse terms are unresolved; this repository currently contains an independent implementation and references to the original work.
