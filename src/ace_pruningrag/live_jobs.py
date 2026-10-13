"""Durable, capped single-question Kaggle jobs; observation failures never resubmit."""

import json
import os
import re
import runpy
import sqlite3
import subprocess
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

TERMINAL = {"complete", "failed", "verification_failed"}


class ObservationUnavailable(Exception):
    """A provider observation/transfer failed; it says nothing about remote completion."""


class KaggleProvider:
    def __init__(self, root, owner):
        self.root, self.owner = Path(root), owner

    def command(self, *args):
        result = subprocess.run(
            ["uv", "tool", "run", "--from", "kaggle==2.2.4", "kaggle", "kernels", *args],
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
        return result.stdout

    def build(self, job, directory):
        build = runpy.run_path(str(self.root / "scripts/build_live_kernel.py"))["build"]
        return build(self.root, directory, self.owner, job["id"], job["qid"])["id"]

    def submit(self, directory):
        self.command("push", "-p", str(directory))

    def status(self, kernel):
        text = self.command("status", kernel)
        match = re.search(r"KernelWorkerStatus\.(\w+)", text)
        if not match:
            raise ValueError("unrecognized provider status")
        return match.group(1).lower()

    def collect(self, kernel, bundle, directory):
        download = directory / f"download-{uuid.uuid4().hex}"
        try:
            self.command("output", kernel, "-p", str(download))
        except (OSError, subprocess.SubprocessError) as exc:
            raise ObservationUnavailable from exc
        # Verify with the submitted first-party source snapshot, not a later checkout.
        import ast
        import base64
        import zlib

        tree = ast.parse((bundle / "bootstrap.py").read_text())
        assignment = next(
            n
            for n in tree.body
            if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "PAYLOAD" for t in n.targets)
        )
        payload = json.loads(zlib.decompress(base64.b64decode(ast.literal_eval(assignment.value))))
        snapshot = directory / "snapshot"
        snapshot.mkdir(exist_ok=True)
        for name, content in payload["files"].items():
            path = snapshot / name
            if not path.resolve().is_relative_to(snapshot.resolve()):
                raise ValueError("snapshot path escapes job")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        data = snapshot / "data"
        if not data.exists():
            data.symlink_to(self.root / "data", target_is_directory=True)
        verification = directory / "verification.json"
        if verification.exists():
            verification = directory / f"verification-{uuid.uuid4().hex}.json"
        subprocess.run(
            [
                str(self.root / ".venv/bin/python"),
                str(self.root / "scripts/verify_live_answer.py"),
                "--bundle",
                str(bundle),
                "--run",
                str(download / "live-answer"),
                "--output",
                str(verification),
            ],
            cwd=snapshot,
            env={**os.environ, "PYTHONPATH": str(snapshot / "src")},
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
        result = json.loads((download / "live-answer/result.json").read_text())
        # Explicit allowlist excludes raw output IDs, local paths and evaluator fields.
        return {
            k: result[k]
            for k in (
                "request_id",
                "interaction_id",
                "query",
                "query_time",
                "policy",
                "prediction",
                "selected",
                "input_tokens",
                "output_tokens",
                "maximum_reserved_tokens",
                "actual_llm_calls",
                "actual_source_calls",
                "generation_seconds",
                "runtime",
                "answer_form_checks",
                "citation_status",
                "prompt_sha256",
            )
        }


class LiveJobs:
    def __init__(self, directory, queries, provider, max_jobs=3, poll_seconds=15):
        if type(max_jobs) is not int or not 1 <= max_jobs <= 10:
            raise ValueError("live session request cap must be 1 through 10")
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.db = self.directory / "jobs.sqlite"
        self.queries, self.provider = set(queries), provider
        self.max_jobs, self.poll_seconds = max_jobs, poll_seconds
        self.stop = threading.Event()
        self.thread = None
        self.thread_lock = threading.Lock()
        with self.connect() as c:
            c.execute(
                "CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, qid TEXT, "
                "request_key TEXT UNIQUE, state TEXT, kernel TEXT, created REAL, "
                "updated REAL, message TEXT, result TEXT)"
            )

    @contextmanager
    def connect(self):
        c = sqlite3.connect(self.db, timeout=10)
        c.row_factory = sqlite3.Row
        try:
            with c:
                yield c
        finally:
            c.close()

    def get(self, job_id):
        if not re.fullmatch(r"[a-f0-9]{32}", job_id):
            raise KeyError(job_id)
        with self.connect() as c:
            row = c.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(job_id)
        job = dict(row)
        job["result"] = json.loads(job["result"]) if job["result"] else None
        return job

    def update(self, job_id, state, kernel=None, message="", result=None):
        with self.connect() as c:
            c.execute(
                "UPDATE jobs SET state=?, kernel=COALESCE(?,kernel), updated=?, "
                "message=?, result=COALESCE(?,result) WHERE id=?",
                (
                    state,
                    kernel,
                    time.time(),
                    message,
                    json.dumps(result) if result else None,
                    job_id,
                ),
            )

    def create(self, qid, request_key):
        if qid not in self.queries:
            raise KeyError(qid)
        if not re.fullmatch(r"[a-f0-9-]{32,36}", request_key):
            raise ValueError("valid idempotency key required")
        with self.connect() as c:
            c.execute("BEGIN IMMEDIATE")
            existing = c.execute(
                "SELECT id,qid FROM jobs WHERE request_key=?", (request_key,)
            ).fetchone()
            if existing:
                if existing["qid"] != qid:
                    raise ValueError("idempotency key already belongs to another question")
                job_id = existing["id"]
            else:
                active = c.execute(
                    "SELECT id FROM jobs WHERE state NOT IN (?,?,?)", tuple(sorted(TERMINAL))
                ).fetchone()
                if active:
                    raise RuntimeError("Another GPU request is still active")
                if c.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] >= self.max_jobs:
                    raise RuntimeError("This live session has reached its request cap")
                job_id, now = uuid.uuid4().hex, time.time()
                c.execute(
                    "INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?)",
                    (job_id, qid, request_key, "created", None, now, now, "", None),
                )
        self.resume()
        return self.get(job_id)

    def resume(self):
        with self.thread_lock:
            self._resume()

    def _resume(self):
        if self.thread and self.thread.is_alive():
            return
        with self.connect() as c:
            active = c.execute(
                "SELECT id FROM jobs WHERE state NOT IN (?,?,?)", tuple(sorted(TERMINAL))
            ).fetchone()
        if active:
            self.thread = threading.Thread(target=self.work, args=(active["id"],), daemon=True)
            self.thread.start()

    def work(self, job_id):
        import fcntl

        lease = self.directory / f"{job_id}.lease"
        with lease.open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return
            if self.get(job_id)["state"] in TERMINAL:
                return
            self._work(job_id)

    def _work(self, job_id):
        job = self.get(job_id)
        directory = self.directory / job_id
        directory.mkdir(exist_ok=True)
        bundle = directory / "bundle"
        if job["state"] == "created":
            try:
                kernel = self.provider.build(job, bundle)
                self.update(job_id, "prepared", kernel=kernel)
            except Exception:
                self.update(job_id, "failed", message="Could not prepare the GPU request")
                return
        if self.get(job_id)["state"] == "prepared":
            # Persist the ambiguous boundary BEFORE the network side effect.
            self.update(job_id, "submitting")
            try:
                self.provider.submit(bundle)
                self.update(job_id, "queued")
            except Exception:
                self.update(
                    job_id,
                    "submission_unknown",
                    message="Submission uncertain; observing the same job without resubmitting",
                )
        while not self.stop.is_set():
            job = self.get(job_id)
            try:
                status = self.provider.status(job["kernel"])
            except Exception:
                self.update(
                    job_id, job["state"], message="Provider unavailable; polling the same job"
                )
                self.stop.wait(self.poll_seconds)
                continue
            if status == "complete":
                self.update(job_id, "verifying")
                try:
                    result = self.provider.collect(job["kernel"], bundle, directory)
                except (subprocess.TimeoutExpired, ObservationUnavailable):
                    self.update(
                        job_id,
                        "verifying",
                        message="Result transfer timed out; retrying the same job",
                    )
                    self.stop.wait(self.poll_seconds)
                    continue
                except Exception:
                    self.update(
                        job_id, "verification_failed", message="GPU result could not be validated"
                    )
                    return
                self.update(job_id, "complete", result=result)
                return
            if status in {"error", "failed", "cancelled"}:
                self.update(
                    job_id, "failed", message="The GPU provider reported a terminal failure"
                )
                return
            self.update(job_id, "running" if status == "running" else "queued")
            self.stop.wait(self.poll_seconds)

    def close(self):
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=1)
