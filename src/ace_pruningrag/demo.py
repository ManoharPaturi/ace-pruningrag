"""Read-only demo over pinned query inputs and explicitly admitted answer traces."""

import json
from pathlib import Path

from .answer_checks import check_answer_form
from .artifacts import read_json, sha256_file
from .dataset import iter_records, verify_dataset
from .evidence import web_chunks
from .retrieval import bm25_rank, select_context


class DemoStore:
    def __init__(self, root: Path):
        self.queries = {
            r.interaction_id: r.inference_input()
            for r in iter_records(verify_dataset(read_json(root / "configs/dataset.json"), root))
        }
        self.runs = {}
        admission = read_json(root / "configs/demo.json")
        for name, entry in admission["runs"].items():
            trace = root / entry["path"]
            if not trace.exists():
                self.runs[name] = {"status": "missing_artifact", "rows": {}}
                continue
            if sha256_file(trace) != entry["sha256"]:
                raise ValueError(f"admitted trace hash differs: {name}")
            rows = {}
            for line in trace.read_text().splitlines():
                row = json.loads(line)
                key = (row["interaction_id"], row["policy"])
                if key in rows or key[0] not in self.queries:
                    raise ValueError("duplicate or unknown demo trace identity")
                q = self.queries[key[0]]
                if row["query"] != q.query or row["query_time"] != q.query_time:
                    raise ValueError("recorded query differs from pinned input")
                # Explicit fields: references, labels, runtime paths and output IDs stay private.
                evidence = []
                for e in row["selected"]:
                    evidence.append(
                        {
                            k: e[k]
                            for k in (
                                "evidence_id",
                                "source_kind",
                                "content",
                                "source_url",
                                "source_title",
                                "source_time",
                                "field",
                                "char_start",
                                "char_end",
                                "source_ref",
                                "requested_date",
                                "ticker",
                                "close",
                                "limitations",
                            )
                            if k in e
                        }
                    )
                rows[key] = {
                    "mode": "recorded_answer",
                    "run": name,
                    "trace_sha256": entry["sha256"],
                    "interaction_id": key[0],
                    "policy": key[1],
                    "query": q.query,
                    "query_time": q.query_time,
                    "prediction": row["prediction"],
                    "prompt_sha256": row["prompt_sha256"],
                    "input_tokens": row["input_tokens"],
                    "output_tokens": row["output_tokens"],
                    "evidence": evidence,
                    "citation_status": "Input evidence; claim-level support is not implied.",
                    "actual_new_llm_calls": 0,
                    "answer_form_checks": check_answer_form(
                        q.query, row["prediction"], [e["evidence_id"] for e in row["selected"]]
                    ),
                }
            if len(rows) != entry["responses"]:
                raise ValueError("admitted response count differs")
            self.runs[name] = {"status": "available", "rows": rows}

    def catalog(self):
        return [
            {
                "name": name,
                "status": run["status"],
                "questions": [
                    {
                        "interaction_id": qid,
                        "query": self.queries[qid].query,
                        "policies": sorted(p for q, p in run["rows"] if q == qid),
                    }
                    for qid in sorted({q for q, _ in run["rows"]})
                ],
            }
            for name, run in self.runs.items()
        ]

    def answer(self, run, qid, policy):
        return self.runs[run]["rows"][(qid, policy)]

    def retrieve(self, qid):
        q = self.queries[qid]
        ranked = bm25_rank(q.query, web_chunks(q, 120))
        selected = select_context(ranked, top_k=5, max_words=600)
        return {
            "mode": "fresh_retrieval",
            "query": q.query,
            "query_time": q.query_time,
            "interaction_id": qid,
            "method": "bm25",
            "budget_unit": "words",
            "max_words": 600,
            "used_words": sum(e.word_count for e, _ in selected),
            "evidence": [dict(e.as_dict(), score=score) for e, score in selected],
            "actual_new_llm_calls": 0,
            "web_retrieval_calls": 1,
            "scope": "Pinned web snapshots; preview uses words, not experiment token budgets.",
        }


def create_app(root=None, live_provider=None, live_enabled=None):
    import os
    from contextlib import asynccontextmanager

    from fastapi import FastAPI, Header, HTTPException

    from .live_jobs import KaggleProvider, LiveJobs

    root = Path(root) if root else Path.cwd()

    @asynccontextmanager
    async def lifespan(app):
        app.state.store = DemoStore(root)
        enabled = os.getenv("ACE_ENABLE_LIVE") == "1" if live_enabled is None else live_enabled
        app.state.jobs = None
        if enabled:
            settings = read_json(root / "configs/live_service.json")
            app.state.jobs = LiveJobs(
                root / "runs/live-service",
                app.state.store.queries,
                live_provider or KaggleProvider(root, settings["owner"]),
                max_jobs=settings["max_jobs"],
            )
            app.state.jobs.resume()
        yield
        if app.state.jobs:
            app.state.jobs.close()

    app = FastAPI(title="ACE-PruningRAG evidence explorer", lifespan=lifespan)

    @app.get("/health")
    def health():
        return {"status": "ready", "mode": "recorded_answers_and_fresh_retrieval"}

    @app.get("/runs")
    def runs():
        return app.state.store.catalog()

    @app.get("/answers/{run}/{qid}/{policy}")
    def answer(run: str, qid: str, policy: str):
        try:
            return app.state.store.answer(run, qid, policy)
        except KeyError as exc:
            raise HTTPException(404, "Recorded answer unavailable") from exc

    @app.get("/retrieve/{qid}")
    def retrieve(qid: str):
        try:
            return app.state.store.retrieve(qid)
        except KeyError as exc:
            raise HTTPException(404, "Unknown pinned question") from exc

    @app.get("/live")
    def live():
        return {
            "enabled": app.state.jobs is not None,
            "scope": "One pinned question per GPU job; generation may wait in the queue.",
        }

    @app.post("/live/generate/{qid}")
    def generate(qid: str, idempotency_key: str = Header()):
        if app.state.jobs is None:
            raise HTTPException(503, "Live GPU generation is not enabled on this service")
        try:
            return app.state.jobs.create(qid, idempotency_key)
        except KeyError as exc:
            raise HTTPException(404, "Unknown pinned question") from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/live/jobs/{job_id}")
    def job(job_id: str):
        if app.state.jobs is None:
            raise HTTPException(503, "Live GPU generation is not enabled on this service")
        try:
            app.state.jobs.resume()
            return app.state.jobs.get(job_id)
        except KeyError as exc:
            raise HTTPException(404, "Unknown GPU request") from exc

    return app
