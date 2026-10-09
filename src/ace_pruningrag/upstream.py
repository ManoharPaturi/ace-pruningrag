"""Pin and statically audit the published implementation without executing it."""

import ast
import importlib.metadata
import platform
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any


def git(checkout: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(checkout), *args], text=True).strip()


def checkout_upstream(config: dict[str, Any], root: Path) -> Path:
    destination = root / config["checkout"]
    if not destination.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", config["repository_url"], str(destination)], check=True)
    if git(destination, "remote", "get-url", "origin") != config["repository_url"]:
        raise ValueError("existing checkout has a different origin; refusing to modify it")
    if git(destination, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("upstream checkout has local changes; refusing to modify it")
    if git(destination, "rev-parse", "HEAD") != config["commit"]:
        subprocess.run(
            ["git", "-C", str(destination), "fetch", "origin", config["commit"]], check=True
        )
        subprocess.run(
            ["git", "-C", str(destination), "checkout", "--detach", config["commit"]], check=True
        )
    return destination


def retriever_signature_check(checkout: Path) -> dict[str, Any]:
    main = ast.parse((checkout / "main.py").read_text(encoding="utf-8"))
    retriever = ast.parse((checkout / "models/retrieve/retriever.py").read_text(encoding="utf-8"))
    cls = next(
        node
        for node in retriever.body
        if isinstance(node, ast.ClassDef) and node.name == "Retriever"
    )
    constructor = next(
        node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    maximum = len(constructor.args.posonlyargs) + len(constructor.args.args) - 1
    minimum = maximum - len(constructor.args.defaults)
    calls = [
        node
        for node in ast.walk(main)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Retriever"
    ]
    if not calls:
        raise ValueError("could not locate upstream Retriever call")
    call = calls[0]
    invalid = (len(call.args) > maximum and constructor.args.vararg is None) or (
        len(call.args) < minimum and not call.keywords
    )
    return {
        "id": "retriever_constructor",
        "status": "blocked" if invalid else "pass",
        "main_line": call.lineno,
        "constructor_line": constructor.lineno,
        "passed_positional": len(call.args),
        "accepted_positional": maximum,
        "detail": "Static signature check; heavy upstream dependencies are not imported.",
    }


def audit_upstream(config: dict[str, Any], root: Path) -> dict[str, Any]:
    checkout = root / config["checkout"]
    checks: list[dict[str, Any]] = []
    commit = git(checkout, "rev-parse", "HEAD")
    dirty = git(checkout, "status", "--porcelain", "--untracked-files=all")
    checks.append(
        {
            "id": "upstream_integrity",
            "status": "pass" if commit == config["commit"] and not dirty else "blocked",
            "commit": commit,
            "clean": not bool(dirty),
        }
    )
    syntax_errors = []
    for path in sorted(checkout.rglob("*.py")):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            syntax_errors.append(
                {"path": str(path.relative_to(checkout)), "line": exc.lineno, "message": exc.msg}
            )
    checks.append(
        {
            "id": "python_syntax",
            "status": "blocked" if syntax_errors else "pass",
            "errors": syntax_errors,
        }
    )
    checks.append(retriever_signature_check(checkout))
    missing_imports = []
    for path in sorted(checkout.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or not node.module:
                continue
            if node.module.split(".")[0] not in {"models", "prompts", "utils"}:
                continue
            target = checkout.joinpath(*node.module.split("."))
            if not target.with_suffix(".py").is_file() and not target.is_dir():
                missing_imports.append(
                    {
                        "path": str(path.relative_to(checkout)),
                        "line": node.lineno,
                        "module": node.module,
                    }
                )
    checks.append(
        {
            "id": "local_imports",
            "status": "blocked" if missing_imports else "pass",
            "missing": missing_imports,
        }
    )
    for asset in config["required_assets"]:
        present = (checkout / asset).exists()
        checks.append(
            {
                "id": f"asset:{asset}",
                "status": "pass" if present else "blocked",
                "detail": "Local presence only; checkpoint integrity is not verified.",
            }
        )
    for service in config["services"]:
        try:
            with socket.create_connection((service["host"], service["port"]), timeout=0.5):
                listening = True
        except OSError:
            listening = False
        checks.append(
            {
                "id": f"service:{service['role']}",
                "status": "unverified",
                "port": service["port"],
                "listening": listening,
                "detail": "TCP reachability is not a model/API compatibility test.",
            }
        )
    dependencies = {}
    for line in (checkout / "requirements.txt").read_text().splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            name = line.split("==")[0].split("[")[0].strip()
            try:
                dependencies[name] = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                dependencies[name] = None
    checks.append(
        {
            "id": "upstream_environment",
            "status": "unverified",
            "detail": "Versions in audit process only; remote GPU environment not provisioned.",
            "packages": dependencies,
        }
    )
    checks.append(
        {
            "id": "mock_api_backing_data",
            "status": "unverified",
            "detail": "Client code exists; compatible server and backing data remain to validate.",
        }
    )
    checks.append(
        {
            "id": "paper_configuration",
            "status": "unverified",
            "detail": "Released defaults differ from README; exact target experiment not locked.",
        }
    )
    return {
        "status": "blocked" if any(c["status"] == "blocked" for c in checks) else "not_ready",
        "upstream_commit": commit,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "checks": checks,
        "limitations": [
            "No generator, embedding, reranker, router, or judge was executed.",
            "No paid inference or model-weight download was performed.",
            "A passing static audit alone would not establish reproduction readiness.",
        ],
    }
