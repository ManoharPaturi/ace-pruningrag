# Phase 1: compatibility and structured evidence

Prepared 9 October 2026. This is a continuation of the approved roadmap, not a claim that the published result is reproduced.

## Startup compatibility

`ace-rag prepare-upstream` derives a new compatibility copy from the clean pinned checkout. It requires the reviewed `main.py` SHA-256 and refuses changed source, a dirty checkout, an existing destination, or an unknown constructor shape.

The released main script passes `noise` into a constructor that has no such parameter. The copy guards `noise != 0` and removes the unsupported argument for `noise=0`. All ten supported arguments remain intact. Tests execute the patched call against a matching lightweight constructor and verify that nonzero noise fails before construction. No original dependency or model pipeline is executed by that test.

The original checkout stays unchanged. The generated copy is ignored, and its source/modified hashes and static signature result are recorded in `results/phase1/compatibility_manifest.json`. Only startup compatibility is resolved; other runtime/artifact blockers remain.

```bash
uv run --no-editable ace-rag prepare-upstream --output .cache/compat/PruningRAG-v1
```

## Restored CRAG finance slice

The original CRAG repository publishes its knowledge graph files through Git LFS. The project now pins repository commit `ad1518887dd4d9ebcd7de95388c7a62751e7705c` and verifies two small files (917,893 bytes total) against their published LFS SHA-256 values:

- Company-name CSV dictionary: 7,306 unique names after the original last-row-wins mapping behavior.
- Market-cap SQLite snapshot: 6,379 records, all decoded and checked for finite numeric values.

The independent read-only adapter supports exactly two original wire formats: POST `/finance/get_ticker_by_name` and POST `/finance/get_market_capitalization`, with `{"query": "..."}` input and `{"result": ...}` output. SQLite opens in read-only mode, queries are parameterized, and the scalar pickle decoder rejects global-object construction.

Real loopback HTTP probes verify Apple's exact snapshot name mapping, AAPL/MSFT snapshot values, and an unknown ticker returning null. `Apple Inc.` alone does not match the snapshot's exact `Apple Inc. Common Stock` name; the earlier null probe is retained in ignored local artifacts. Fuzzy matching is not silently introduced.

This is a limited finance slice, not the full original CRAG service. It omits fuzzy company matching, prices, dividends, other finance data, and movie/music/sports/open APIs. The snapshots contain historical benchmark values and do not supply current market information or prove alignment with every RM3QA query timestamp.

```bash
uv run --no-editable ace-rag fetch-finance
uv run --no-editable ace-rag finance-smoke --output runs/phase1/finance_smoke.json
```

## Learned web retrieval pilot

A separate private Kaggle pilot bundles the same first-party code and explicit public-asset configurations. It restores the finance slice, verifies compatibility, and downloads pinned BGE-M3 and BGE reranker weights into temporary storage (about 4.6 GB). The kernel is capped at 1,800 seconds and five real queries.

The encoder uses normalized CLS embeddings and cosine similarity; the reranker scores the dense top ten query/evidence pairs. Both use float32 and inference/evaluation mode. Each BM25, dense, and dense+reranker method sees the same original evidence pool and a three-chunk/600-word context limit. Oversized model inputs fail rather than silently truncating evidence. No generator or judge runs.

This is explicitly an adapted retrieval smoke: 200-word chunks differ from released token/Markdown chunking, and the five questions have no gold supporting-evidence labels. Context counts, timings, and successful inference are not answer-quality or evidence-completeness claims. Actual completion will be recorded only after downloading and verifying output artifacts.

```bash
uv run --no-editable python scripts/build_kaggle_kernel.py --mode retrieval --owner ionrey --output runs/kaggle/retrieval-kernel-v1
uv tool run --from kaggle==2.2.4 kaggle kernels push -p runs/kaggle/retrieval-kernel-v1 --accelerator NvidiaTeslaT4 -t 1800
```

## Artifact discovery

The authors' earlier competition repository and `fishsure/bge-m3-router` provide leads for a BGE-based router. They do not establish availability of the paper's fine-tuned Llama-3.1 source selector/domain adapter, so they are not substituted. The main PruningRAG release has no attached release assets, and the original router checkpoint is still unresolved.

The paper's table for 5 web pages with Llama-3.1-8B and pruning is a possible reproduction target. Before freezing that target, exact router/model assets, prompts, dataset split semantics, token chunking, all API snapshots, and the original judge must be resolved. The current adapted smoke does not claim to replicate that table.

Primary sources: [PruningRAG paper](https://arxiv.org/html/2409.13694v4), [original CRAG API](https://github.com/facebookresearch/CRAG/tree/ad1518887dd4d9ebcd7de95388c7a62751e7705c/mock_api), [competition solution](https://github.com/USTCAGI/CRAG-in-KDD-Cup2024), [BGE-M3](https://huggingface.co/BAAI/bge-m3), and [BGE reranker](https://huggingface.co/BAAI/bge-reranker-v2-m3).
