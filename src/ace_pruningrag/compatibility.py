"""Narrow, hash-guarded compatibility copy; never edit the published checkout."""

import ast
import hashlib
import shutil
from pathlib import Path
from typing import Any

from .artifacts import sha256_file, write_json
from .upstream import git, retriever_signature_check


def patch_constructor(source: str, expected_sha256: str) -> str:
    if hashlib.sha256(source.encode()).hexdigest() != expected_sha256:
        raise ValueError("main.py differs from the reviewed source; refusing to patch")
    tree = ast.parse(source)
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Retriever"
    ]
    if len(calls) != 1:
        raise ValueError("expected exactly one Retriever construction")
    call = calls[0]
    if len(call.args) != 11 or call.keywords or call.lineno != call.end_lineno:
        raise ValueError("unrecognized Retriever call shape")
    if not isinstance(call.args[-1], ast.Name) or call.args[-1].id != "noise":
        raise ValueError("unrecognized extra argument")
    original = ast.get_source_segment(source, call)
    call.args.pop()
    replacement = ast.unparse(call)
    lines = source.splitlines(keepends=True)
    index = call.lineno - 1
    line = lines[index]
    indent = line[: len(line) - len(line.lstrip())]
    guard = (
        f"{indent}if noise != 0:\n"
        f"{indent}    raise ValueError('compatibility copy supports noise=0 only')\n"
    )
    lines[index] = guard + line.replace(original, replacement, 1)
    patched = "".join(lines)
    ast.parse(patched)
    return patched


def prepare_compatibility(
    upstream_config: dict[str, Any],
    patch_config: dict[str, Any],
    root: Path,
    output: Path,
) -> dict[str, Any]:
    if patch_config["supported_noise"] != 0 or patch_config["scope"] != (
        "startup_constructor_compatibility_only"
    ):
        raise ValueError("unsupported compatibility protocol")
    source = root / upstream_config["checkout"]
    if git(source, "rev-parse", "HEAD") != upstream_config["commit"]:
        raise ValueError("upstream is not at the pinned commit")
    if git(source, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("upstream is dirty; refusing to derive a compatibility copy")
    if output.exists() or output.resolve().is_relative_to(source.resolve()):
        raise ValueError("compatibility output must be new and outside the upstream checkout")
    text = (source / "main.py").read_text(encoding="utf-8")
    patched = patch_constructor(text, patch_config["main_sha256"])
    shutil.copytree(source, output, ignore=shutil.ignore_patterns(".git", "__pycache__"))
    (output / "main.py").write_text(patched, encoding="utf-8")
    manifest = {
        "status": "compatibility_copy_prepared",
        "upstream_commit": upstream_config["commit"],
        "source_main_sha256": patch_config["main_sha256"],
        "patched_main_sha256": sha256_file(output / "main.py"),
        "supported_noise": 0,
        "upstream_clean_after": not bool(git(source, "status", "--porcelain")),
        "signature_check": retriever_signature_check(output),
        "changes": ["Guard against nonzero noise", "Remove unsupported constructor argument"],
        "limitations": [
            "Startup compatibility only; no model/API pipeline execution is implied.",
            "Nonzero noise experiments remain unsupported rather than silently changing behavior.",
            "Original model/router assets and mock API configuration are still required.",
        ],
    }
    write_json(output / "compatibility_manifest.json", manifest)
    return manifest
