# Change and review workflow

Implementation changes go through feature branches and pull requests. Do not push project changes directly to `main` or merge before required CI checks pass.

The empty initial `main` commit exists only as the base for the first pull request. It contains no project files. The Phase 1 implementation is submitted from `feat/phase1-reproduction-foundation`.

Required checks:

- `test`: locked Python environment, lint, formatting, and unit/integration tests.
- `data-smoke`: hash-verified real RM3QA download, full schema validation, 25-query offline retrieval, and independent trace provenance/budget verification.

`data-smoke` does not run an LLM or claim scientific performance. Uploaded CI artifacts contain summaries and bounded traces, not the raw dataset or credentials.

Use a separate run directory for every experiment. Keep upstream untouched. Preserve the source hashes and configuration for every result. Do not commit raw credentials, model weights, datasets, or full research caches.
