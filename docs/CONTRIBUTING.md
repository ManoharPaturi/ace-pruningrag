# Change and review workflow

Implementation changes go through feature branches and pull requests. Do not push project changes directly to `main` or merge before required CI checks pass.

The empty initial `main` commit exists only as the base for the first pull request. It contains no project files. The Phase 1 foundation was submitted from `feat/phase1-reproduction-foundation` and merged through PR #1. Later Kaggle validation artifacts and the repeatability fix use `feat/phase1-kaggle-validation` and a separate PR.

Required checks:

- `test`: locked Python environment, lint, formatting, and unit/integration tests.
- `data-smoke`: hash-verified real RM3QA download, full schema validation, 25-query offline retrieval, and independent trace provenance/budget verification. Also runs the pinned-tokenizer Phase 2 selection smoke and verifies all five methods against original evidence and exact objective search. The same job also audits and independently verifies 8,118 Phase 3 source/budget plans on all 2,706 real questions.
- `finance-smoke`: hash-verified original CRAG finance assets and real loopback HTTP probes.

`data-smoke` does not run an LLM or claim scientific performance. Uploaded CI artifacts contain summaries and bounded traces, not the raw dataset or credentials.

Use a separate run directory for every experiment. Keep upstream untouched. Preserve the source hashes and configuration for every result. Do not commit raw credentials, model weights, datasets, or full research caches.

The repository is now public. Contributors submit PRs from forks; only `ManoharPaturi` currently has repository write access and can merge. PRs and required checks apply to administrators too. No approval count is required because owner-authored PRs cannot be self-approved; the owner must review the change and merge after checks pass. Do not add collaborators with write access without revisiting this access policy.
