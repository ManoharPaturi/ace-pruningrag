import threading
import time

import pytest

from ace_pruningrag.live_jobs import LiveJobs, ObservationUnavailable


class ProviderFixture:
    def __init__(self, submission_unknown=False):
        self.submits = 0
        self.observations = 0
        self.transfers = 0
        self.submission_unknown = submission_unknown
        self.ready = threading.Event()

    def build(self, job, directory):
        directory.mkdir()
        return "fixture/" + job["id"]

    def submit(self, directory):
        self.submits += 1
        if self.submission_unknown:
            raise TimeoutError("accepted remotely, response lost")

    def status(self, kernel):
        self.observations += 1
        if self.observations == 1:
            raise ConnectionError("temporary observation failure")
        return "complete" if self.ready.is_set() else "running"

    def collect(self, kernel, bundle, directory):
        self.transfers += 1
        if self.transfers == 1:
            raise ObservationUnavailable("temporary transfer failure")
        return {"prediction": "Fixture only", "actual_llm_calls": 1}


def wait_complete(manager, job_id):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        job = manager.get(job_id)
        if job["state"] == "complete":
            return job
        time.sleep(0.01)
    pytest.fail(f"fixture did not complete: {manager.get(job_id)}")


def test_unknown_submission_and_transient_observations_never_resubmit(tmp_path):
    provider = ProviderFixture(submission_unknown=True)
    manager = LiveJobs(tmp_path, ["q"], provider, poll_seconds=0.01)
    try:
        job = manager.create("q", "a" * 32)
        assert manager.create("q", "a" * 32)["id"] == job["id"]
        provider.ready.set()
        assert wait_complete(manager, job["id"])["result"]["actual_llm_calls"] == 1
        assert provider.submits == 1 and provider.transfers == 2
    finally:
        manager.close()


def test_restart_observes_existing_job_and_session_caps_persist(tmp_path):
    provider = ProviderFixture()
    manager = LiveJobs(tmp_path, ["q"], provider, max_jobs=1, poll_seconds=0.01)
    with manager.connect() as c:
        c.execute(
            "INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?)",
            ("b" * 32, "q", "a" * 32, "submitting", "fixture/existing", 1, 1, "", None),
        )
    provider.ready.set()
    manager.resume()
    try:
        wait_complete(manager, "b" * 32)
        assert provider.submits == 0
        assert manager.create("q", "a" * 32)["id"] == "b" * 32
        with pytest.raises(RuntimeError, match="request cap"):
            manager.create("q", "c" * 32)
    finally:
        manager.close()


def test_single_active_job_and_key_cannot_change_question(tmp_path):
    provider = ProviderFixture()
    manager = LiveJobs(tmp_path, ["q", "other"], provider, poll_seconds=0.01)
    try:
        job = manager.create("q", "a" * 32)
        with pytest.raises(RuntimeError, match="still active"):
            manager.create("other", "c" * 32)
        with pytest.raises(ValueError, match="another question"):
            manager.create("other", "a" * 32)
        with pytest.raises(KeyError):
            manager.create("unknown", "d" * 32)
        provider.ready.set()
        wait_complete(manager, job["id"])
    finally:
        manager.close()
