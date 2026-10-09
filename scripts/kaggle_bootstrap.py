"""Bounded GPU readiness and real-data smoke run; generated bundle contains no credentials."""

import base64
import hashlib
import json
import platform
import sys
import zlib
from pathlib import Path

PAYLOAD = "__BUNDLE__"


def main():
    root = Path("/tmp/ace-pruningrag")
    root.mkdir(parents=True, exist_ok=False)
    output = Path("/kaggle/working/phase1")
    output.mkdir(parents=True, exist_ok=False)
    bundle = json.loads(zlib.decompress(base64.b64decode(PAYLOAD)))
    for name, content in bundle["files"].items():
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("unsafe bundle path")
        if hashlib.sha256(content.encode()).hexdigest() != bundle["sha256"][name]:
            raise ValueError("bundle integrity check failed")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    sys.path.insert(0, str(root / "src"))
    from ace_pruningrag.artifacts import read_json, write_json
    from ace_pruningrag.dataset import profile_dataset
    from ace_pruningrag.experiment import retrieval_smoke
    from ace_pruningrag.fetch import fetch_dataset
    from ace_pruningrag.upstream import audit_upstream, checkout_upstream

    write_json(output / "bundle_manifest.json", bundle["sha256"])
    hardware = {"python": sys.version, "platform": platform.platform(), "cuda_available": False}
    try:
        import torch

        hardware.update(
            torch_version=torch.__version__,
            cuda_version=torch.version.cuda,
            cuda_available=torch.cuda.is_available(),
        )
        hardware["gpus"] = [
            {
                "name": torch.cuda.get_device_name(i),
                "total_memory_bytes": torch.cuda.get_device_properties(i).total_memory,
            }
            for i in range(torch.cuda.device_count())
        ]
        if hardware["cuda_available"]:
            for i in range(torch.cuda.device_count()):
                tensor = torch.ones((8, 8), device=f"cuda:{i}")
                assert (tensor @ tensor).sum().item() == 512
            hardware["cuda_arithmetic_smoke"] = "passed"
    except ImportError:
        hardware["torch_status"] = "not_installed"
    write_json(output / "hardware.json", hardware)
    dataset = fetch_dataset(read_json(root / "configs/dataset.json"), root)
    write_json(output / "dataset_profile.json", profile_dataset(dataset))
    config = read_json(root / "configs/upstream.json")
    checkout_upstream(config, root)
    write_json(output / "upstream_audit.json", audit_upstream(config, root))
    summary = retrieval_smoke(root / "configs/retrieval_smoke.json", root, output / "bm25-smoke")
    completion = {
        "status": "bootstrap_completed",
        "cuda_available": hardware["cuda_available"],
        "retrieval_queries": summary["queries"],
        "published_baseline_reproduced": False,
        "scope": "GPU arithmetic, data validation, upstream audit, offline BM25 retrieval",
        "model_weight_downloads": 0,
        "llm_calls": 0,
    }
    write_json(output / "completion.json", completion)
    print(json.dumps(completion, indent=2))


if __name__ == "__main__":
    main()
