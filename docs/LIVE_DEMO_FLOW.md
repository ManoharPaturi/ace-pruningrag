# Verified asynchronous GPU demo flow

Updated 13 October 2026. The browser now submits a real single-question Kaggle GPU job, polls persistent state, and displays its independently reconstructed answer and exact selected evidence. The existing replay/retrieval paths remain available.

## Verified actual flow

**Story:** selected pinned question → browser submission → Next.js proxy → FastAPI/SQLite journal → private Kaggle worker → output reconstruction → answer/evidence display.

Actual browser request `9047acf90406454ba56f8e7f5edfa958` asked who played Harvey Specter in Suits. The completed GPU job returned `Gabriel Macht`: one model call, 1,355 input tokens, five output tokens, 1,451 reserved tokens. Reported generation took 1.84 seconds; request creation to verified completion took 160.21 seconds, including queue/download/setup, API recovery and output verification. This aggregate interval is not a separately measured breakdown or a latency guarantee.

The API was restarted while the provider reported RUNNING. The persistent journal recovered the same job; page refresh displayed the same completed answer and source excerpts. Only one request is present in the live-service journal. [Compact verification](../results/version1/live_demo_verification.json) binds the result, prompt and selected evidence IDs. Private browser proof: `runs/version1/demo/live-gpu-result.png`.

AI source inspection found explicit actor-role support. This is an already inspected development question, not held-out accuracy or independent human validation. Multiple chunks/pages sharing the same source are not independent confirmation. General claim-level support remains labeled unverified.

## Persistence and limits

- SQLite stores identity, state and timestamps before submission. A request key cannot change its question; repeating a key returns the existing job.
- One active job is allowed, with three total requests per persistent journal by default (`configs/live_service.json`). Restarting does not reset the cap.
- A persisted submission boundary is never automatically resubmitted after timeout or restart. Observation/transfer failures poll the same kernel; they do not imply a failed generation.
- A per-job filesystem lease prevents concurrent service instances from handling the same job. Snapshot verification uses the submitted source, even if the working tree later changes.
- Each transfer has a fresh directory; failed/partial downloads are preserved. Explicit provider terminal failures and invalid results remain visible.
- Responses allowlist answer/evidence/cost fields; raw output IDs, local paths and evaluation labels are not returned.

Tests cover unknown submission, temporary observation/transfer failures, restart recovery, persistent caps, one active job, request-key conflicts, disabled live mode and HTTP identity recovery. Unit providers are explicitly fixtures. The real browser/GPU run above supplies execution evidence. All 156 local tests pass; production build and Ruff lint/format/diff checks pass.

## Local setup

Credentials stay in the operator's normal Kaggle configuration, outside Git. Confirm read-only Kaggle access first. The owner field is an account identifier, not a credential; contributors must configure their own authorized account.

```bash
uv sync --locked --no-editable --extra demo --extra generation --python 3.12
uv run --locked --no-editable ace-rag fetch-data
ACE_ENABLE_LIVE=1 uv run --locked --no-editable --extra demo --extra generation \
  uvicorn ace_pruningrag.demo:create_app --factory --host 127.0.0.1 --port 8060
```

Start the web app as documented in [demo setup](DEMO.md), then open `http://127.0.0.1:3060`. Without `ACE_ENABLE_LIVE=1`, the app explicitly reports live generation unavailable. Local cached generator tokenizer/config sidecars are needed for reconstruction; the large model executes on Kaggle. Every job fetches/validates the pinned weights remotely.

`POST /live/generate/{qid}` requires an `Idempotency-Key` header and a known pinned question. `GET /live/jobs/{id}` recovers state/results. The browser saves submission intent before sending and preserves ambiguous failures; it clears definitive rejected requests. The Next.js proxy compares browser origin with the actual Host header. Its initial localhost-normalized URL mismatch was diagnosed and fixed before any GPU submission.

## Open full-project requirements

The asynchronous pinned-question live path is verified. It is fixed-web, not the full adaptive multi-source system. General entity/date/unit and claim verification, source-only controls, genuine cross-source evaluation, independent annotations, final baseline/ablation matrix and the research report/paper remain open. Preserve frozen experiments and treat newly exposed questions as development data.
