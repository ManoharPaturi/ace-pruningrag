# Evidence explorer: verified local replay/retrieval demo

This app lets a reader choose a real recorded question, compare actual policy answers and inspect exact selected evidence. It also performs fresh BM25 retrieval against that question's pinned web snapshots. It is a read-only research explorer; recorded answers are explicitly labeled replays. Live generator inference, end-to-end adaptive retrieval and a production deployment remain unfinished roadmap work.

## Setup

From the repository root:

```bash
uv sync --locked --no-editable --extra demo --python 3.12
uv run --locked --no-editable ace-rag fetch-data
uv run --locked --no-editable --extra demo uvicorn ace_pruningrag.demo:create_app \
  --factory --host 127.0.0.1 --port 8060
```

In another terminal:

```bash
cd apps/web
npm ci --ignore-scripts
npm run dev -- --port 3060
```

Open `http://127.0.0.1:3060`. The frontend forwards read-only requests to the API at port 8060. Set the server-only `ACE_API_URL` environment variable if the API uses another address; it contains no credential. Both services bind localhost by default.

A fresh clone needs the five private trace files named in `configs/demo.json`, obtained from the owner or reproduced under the admitted protocol. Missing artifacts appear as unavailable runs; altered trace hashes fail startup. The API exposes explicit answer/evidence fields, not gold answers, domain/split labels, local paths or raw output token IDs.

## Actual behavior

- `/runs`: admitted run/question/policy catalog and artifact availability.
- `/answers/{run}/{question_id}/{policy}`: recorded output, trace/prompt identity, token counts and selected input evidence. No new generation occurs.
- `/retrieve/{question_id}`: one fresh BM25 operation over exact snapshot chunks, at most five excerpts / 600 words. This preview uses a word cap, not the experiment's tokenizer budget.
- `/health`: service readiness after pinned dataset and admitted traces load.

Web source links and character offsets identify the supplied text; API evidence exposes dated row provenance and known metadata limitations. Showing selected input evidence is not claim-level citation support. Do not relabel replay as live inference or availability checks as semantic validation.

## Verification checkpoint

The backend HTTP path was exercised across all 444 admitted records, comparing each response with its actual hash-admitted trace. Fresh retrieval content was checked against the pinned page's character spans. Tests cover changed trace rejection, visible missing artifacts, reference-field exclusion and unknown-record errors. The Next.js production build passed. Browser verification selected the historical UBSI/all-available answer, expanded its dated API row and ran fresh retrieval (558 words). The browser showed the expected answer, provenance and metadata limitation, with no captured console warnings/errors. This verifies the replay/retrieval flow, not live model inference.

Implementation follows [FastAPI lifespan documentation](https://fastapi.tiangolo.com/advanced/events/) and [Next.js route handlers](https://nextjs.org/docs/app/getting-started/route-handlers). No Vercel deployment is configured.

The completed five-selector cohort is admitted after full trace reconstruction. Browser verification also displayed the Real Sociedad/top-K prose abstention and its exact selected source excerpts; source review of the complete cohort is still pending.
