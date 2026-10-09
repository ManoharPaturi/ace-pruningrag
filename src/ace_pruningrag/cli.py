"""Research command-line entry points."""

import argparse
import json
import sys
from pathlib import Path

from .artifacts import read_json, write_json
from .assets import fetch_assets
from .compatibility import prepare_compatibility
from .dataset import profile_dataset, verify_dataset
from .experiment import retrieval_smoke
from .fetch import fetch_dataset
from .finance_api import finance_smoke
from .reviews import import_review
from .routing_experiment import routing_smoke
from .selection_experiment import selection_smoke
from .upstream import audit_upstream, checkout_upstream


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ACE-PruningRAG research tools")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in (
        "fetch-data",
        "profile-data",
        "fetch-upstream",
        "audit-upstream",
        "smoke",
        "prepare-upstream",
        "fetch-finance",
        "finance-smoke",
        "fetch-selection",
        "selection-smoke",
        "routing-smoke",
        "import-review",
    ):
        command = sub.add_parser(name)
        default = "configs/dataset.json"
        if name == "routing-smoke":
            default = "configs/routing_smoke.json"
        elif "selection" in name:
            default = "configs/selection_smoke.json"
        elif name == "prepare-upstream":
            default = "configs/compatibility.json"
        elif "finance" in name:
            default = "configs/crag_finance.json"
        elif "upstream" in name:
            default = "configs/upstream.json"
        elif name == "smoke":
            default = "configs/retrieval_smoke.json"
        command.add_argument("--config", type=Path, default=Path(default))
        if name in (
            "profile-data",
            "audit-upstream",
            "smoke",
            "prepare-upstream",
            "finance-smoke",
            "selection-smoke",
            "routing-smoke",
            "import-review",
        ):
            command.add_argument("--output", type=Path, required=True)
        if name == "import-review":
            command.add_argument("--export", type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    config_path = root / args.config
    try:
        config = read_json(config_path)
        if args.command == "fetch-data":
            result = {"dataset": str(fetch_dataset(config, root)), "status": "hash_verified"}
        elif args.command in ("fetch-finance", "fetch-selection"):
            result = fetch_assets(config, root)
        elif args.command == "finance-smoke":
            result = finance_smoke(config, root)
            write_json(root / args.output, result)
        elif args.command == "prepare-upstream":
            result = prepare_compatibility(
                read_json(root / config["upstream_config"]),
                config,
                root,
                root / args.output,
            )
        elif args.command == "fetch-upstream":
            result = {"checkout": str(checkout_upstream(config, root)), "commit": config["commit"]}
        elif args.command == "profile-data":
            result = profile_dataset(verify_dataset(config, root))
            write_json(root / args.output, result)
        elif args.command == "audit-upstream":
            result = audit_upstream(config, root)
            write_json(root / args.output, result)
        elif args.command == "import-review":
            result = import_review(args.export.resolve(), config, root, root / args.output)
        elif args.command == "routing-smoke":
            result = routing_smoke(config_path, root, root / args.output)
        elif args.command == "selection-smoke":
            result = selection_smoke(config_path, root, root / args.output)
        else:
            result = retrieval_smoke(config_path, root, root / args.output)
        # Full profile IDs and dependency inventory belong in the artifact, not the console.
        compact = {
            k: v
            for k, v in result.items()
            if k
            not in (
                "query_ids_in_file_order",
                "checks",
                "distributions",
            )
        }
        print(json.dumps(compact, indent=2))
        return 2 if result.get("status") in ("blocked", "not_ready") else 0
    except (ValueError, OSError, KeyError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
