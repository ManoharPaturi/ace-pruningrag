"""Bundle blinded query/source tasks with isolated pinned GPU inference."""

import argparse
import base64
import hashlib
import json
import re
import uuid
import zlib
from pathlib import Path

from ace_pruningrag.requirements_protocol import requirement_tasks


def build(root, trace, output, owner):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", owner):
        raise ValueError("invalid extraction owner")
    config = json.loads((root / "configs/query_requirements_3b.json").read_text())
    from ace_pruningrag.requirements_3b_protocol import validate_protocol

    validate_protocol(root, config)
    tasks = requirement_tasks([json.loads(x) for x in trace.read_text().splitlines()])
    if not tasks or len(tasks) > config["max_tasks"]:
        raise ValueError("extraction task cap exceeded")
    files = {
        str(p.relative_to(root)): p.read_text()
        for p in sorted((root / "src/ace_pruningrag").glob("*.py"))
    }
    for name in (
        "configs/query_requirements_3b.json",
        "configs/query_requirements.json",
        "configs/requirements_extractor_3b.json",
        "configs/requirements_control_decoding.json",
        "configs/inventory_extraction.json",
        "configs/constrained_extraction.json",
        "configs/unicode_extraction.json",
        "configs/generated_pilot.json",
        "scripts/requirements_3b_driver.py",
    ):
        files[name] = (root / name).read_text()
    from ace_pruningrag.unicode_claims import permitted_spans

    for task in tasks:
        permitted_spans(task["text"])
    files["configs/constrained_tasks.json"] = json.dumps(
        {"source_trace_sha256": hashlib.sha256(trace.read_bytes()).hexdigest(), "tasks": tasks},
        ensure_ascii=False,
    )
    hashes = {name: hashlib.sha256(content.encode()).hexdigest() for name, content in files.items()}
    payload = base64.b64encode(
        zlib.compress(json.dumps({"files": files, "sha256": hashes}).encode())
    ).decode()
    template = (root / "scripts/kaggle_generated_pilot.py").read_text()
    substitutions = {
        'fetch_dataset(read_json(root / "configs/dataset.json"), root)': "",
        'fetch_assets(read_json(root / "configs/crag_prices.json"), root)': "",
        "scripts/generated_driver.py": "scripts/requirements_3b_driver.py",
        'Path("/kaggle/working/phase3-pilot")': 'Path("/kaggle/working/requirements-3b-pilot")',
        "Dataset and original price snapshot verified": "Blinded query-only model tasks bundled",
        'fetch_assets(read_json(root / "configs/generated_pilot.json"), root)': (
            'fetch_assets(read_json(root / "configs/requirements_extractor_3b.json"), root)'
        ),
        'PAYLOAD = "__BUNDLE__"': f"PAYLOAD = {payload!r}",
    }
    for old, new in substitutions.items():
        if template.count(old) != 1:
            raise ValueError(f"extraction template contract differs: {old}")
        template = template.replace(old, new)
    specs = [f"{name}=={version}" for name, version in config["constraints_dependencies"].items()]
    marker = '            "sentencepiece==0.2.1",'
    if template.count(marker) != 1:
        raise ValueError("constrained dependency overlay marker differs")
    template = template.replace(
        marker, marker + "\n" + "\n".join("            " + repr(spec) + "," for spec in specs)
    )
    output.mkdir(parents=True, exist_ok=False)
    (output / "bootstrap.py").write_text(template)
    identity = uuid.uuid4().hex
    metadata = {
        "id": f"{owner}/ace-req3b-{identity}",
        "title": f"ACE Req3B {identity}",
        "code_file": "bootstrap.py",
        "language": "python",
        "kernel_type": "script",
        "is_private": True,
        "enable_gpu": True,
        "machine_shape": "NvidiaTeslaT4",
        "enable_internet": True,
        "dataset_sources": [],
        "competition_sources": [],
        "kernel_sources": [],
        "model_sources": [],
    }
    (output / "kernel-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (output / "bundle-manifest.json").write_text(json.dumps(hashes, indent=2) + "\n")
    (output / "task-manifest.json").write_text(
        json.dumps(
            {
                "protocol_id": config["protocol_id"],
                "span_policy_sha256": config["span_policy_sha256"],
                "tasks": len(tasks),
                "query_tasks": sum(t["kind"] == "query" for t in tasks),
                "source_tasks": sum(t["kind"] == "source" for t in tasks),
                "source_trace_sha256": hashlib.sha256(trace.read_bytes()).hexdigest(),
                "tasks_sha256": hashes["configs/constrained_tasks.json"],
                "kernel_id": metadata["id"],
                "max_generate_invocations": (len(tasks) + 3) // 4,
                "max_total_reserved_tokens": len(tasks) * config["max_input_and_output_tokens"],
                "new_answer_generation_calls": 0,
            },
            indent=2,
        )
        + "\n"
    )
    return metadata


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--trace", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--owner", required=True)
    a = p.parse_args()
    print(json.dumps(build(Path.cwd(), a.trace, a.output, a.owner)))
