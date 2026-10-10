import hashlib
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "review_builder", Path(__file__).parents[1] / "scripts/build_generated_review.py"
)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def test_untrusted_output_and_evidence_are_escaped_and_storage_bound_to_run(tmp_path):
    payload = '</script><script>alert("fixture")</script>'
    row = {
        "interaction_id": "fixture",
        "query": "</h2>fixture",
        "query_time": "fixture",
        "policy": "fixed_web",
        "prediction": payload,
        "input_tokens": 1,
        "output_tokens": 1,
        "generation_seconds": 1.0,
        "evaluation": {"outcome": "needs_semantic_review"},
        "selected": [{"source_url": "https://example.invalid", "content": payload}],
    }
    run = tmp_path / "run"
    run.mkdir()
    trace = run / "predictions.jsonl"
    trace.write_text(json.dumps(row) + "\n")
    output = tmp_path / "review.html"
    builder.build(run, output)
    page = output.read_text()
    assert payload not in page
    assert "&lt;/script&gt;" in page and "\\u003c/script>" in page
    assert hashlib.sha256(trace.read_bytes()).hexdigest() in page
    assert '<option value="pending">Pending</option>' in page
    assert "__RUN_HASH__" not in page
