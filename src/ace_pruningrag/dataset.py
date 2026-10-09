"""Strict streaming RM3QA loading without Arrow's mixed-column inference."""

import bz2
import json
import math
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .artifacts import sha256_file


class DatasetError(ValueError):
    """A malformed row must never silently disappear from evaluation."""


def answer_text(value: Any) -> str:
    """Normalize scalar answer types, retaining the raw record separately."""
    if isinstance(value, str):
        return value
    if type(value) in (int, float) and math.isfinite(value):
        return str(value)
    raise DatasetError("answers must be strings or finite numbers")


@dataclass(frozen=True)
class QueryInput:
    interaction_id: str
    query: str
    query_time: str
    search_results: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class Record:
    raw: dict[str, Any]

    @property
    def interaction_id(self) -> str:
        return self.raw["interaction_id"]

    @property
    def answers(self) -> tuple[str, ...]:
        values = [self.raw["answer"], *self.raw.get("alt_ans", [])]
        return tuple(dict.fromkeys(answer_text(value) for value in values))

    def inference_input(self) -> QueryInput:
        # Gold domain, answers, split, and question type are intentionally absent.
        return QueryInput(
            self.interaction_id,
            self.raw["query"],
            self.raw["query_time"],
            tuple(dict(page) for page in self.raw["search_results"]),
        )


def validate_record(value: Any, location: str = "record") -> Record:
    try:
        if not isinstance(value, dict):
            raise DatasetError("expected an object")
        for key in (
            "interaction_id",
            "query",
            "query_time",
            "domain",
            "question_type",
            "static_or_dynamic",
        ):
            if not isinstance(value.get(key), str) or not value[key].strip():
                raise DatasetError(f"{key} must be a non-empty string")
        if "answer" not in value:
            raise DatasetError("missing answer")
        answer_text(value["answer"])
        if not isinstance(value.get("alt_ans", []), list):
            raise DatasetError("alt_ans must be a list")
        for answer in value.get("alt_ans", []):
            answer_text(answer)
        if not isinstance(value.get("search_results"), list):
            raise DatasetError("search_results must be a list")
        for index, page in enumerate(value["search_results"]):
            if not isinstance(page, dict):
                raise DatasetError(f"search_results[{index}] must be an object")
            for key in (
                "page_name",
                "page_url",
                "page_snippet",
                "page_result",
                "page_last_modified",
            ):
                if not isinstance(page.get(key), str):
                    raise DatasetError(f"search_results[{index}].{key} must be a string")
        return Record(value)
    except DatasetError as exc:
        raise DatasetError(f"{location}: {exc}") from exc


def iter_records(path: Path) -> Iterator[Record]:
    opener = bz2.open if path.suffix == ".bz2" else open
    seen: set[str] = set()
    with opener(path, "rt", encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            location = f"{path}:{number}"
            if not line.strip():
                raise DatasetError(f"{location}: blank JSONL row")
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DatasetError(f"{location}: invalid JSON: {exc.msg}") from exc
            record = validate_record(value, location)
            if record.interaction_id in seen:
                raise DatasetError(f"{location}: duplicate interaction_id {record.interaction_id}")
            seen.add(record.interaction_id)
            yield record


def verify_dataset(config: dict[str, Any], root: Path) -> Path:
    path = root / config["path"]
    if path.stat().st_size != config["bytes"]:
        raise DatasetError(f"{path}: file size does not match pinned release")
    if sha256_file(path) != config["sha256"]:
        raise DatasetError(f"{path}: SHA-256 does not match pinned release")
    return path


def profile_dataset(path: Path) -> dict[str, Any]:
    distributions: dict[str, Counter] = {
        key: Counter()
        for key in (
            "domain",
            "question_type",
            "static_or_dynamic",
            "split",
            "web_pages_per_query",
            "answer_types",
            "alternate_answer_types",
            "row_fields",
        )
    }
    count = 0
    pages = 0
    empty_pages = 0
    numeric_alternates = 0
    api_fields = Counter()
    ids = []
    for record in iter_records(path):
        row = record.raw
        count += 1
        ids.append(record.interaction_id)
        for key in ("domain", "question_type", "static_or_dynamic", "split"):
            distributions[key][str(row.get(key, "absent"))] += 1
        distributions["web_pages_per_query"][str(len(row["search_results"]))] += 1
        distributions["answer_types"][type(row["answer"]).__name__] += 1
        for answer in row.get("alt_ans", []):
            distributions["alternate_answer_types"][type(answer).__name__] += 1
            numeric_alternates += type(answer) in (int, float)
        distributions["row_fields"].update(row.keys())
        for field in ("kg_info", "kg_infos", "api_results", "supporting_facts", "evidence_ids"):
            api_fields[field] += field in row
        for page in row["search_results"]:
            pages += 1
            empty_pages += not (page["page_result"].strip() or page["page_snippet"].strip())
    return {
        "status": "validated",
        "rows": count,
        "web_pages": pages,
        "empty_web_pages": empty_pages,
        "numeric_alternate_answers": numeric_alternates,
        "sha256": sha256_file(path),
        "distributions": {key: dict(sorted(value.items())) for key, value in distributions.items()},
        "optional_field_counts": dict(api_fields),
        "query_ids_in_file_order": ids,
        "limitations": [
            "Observed split values have not been assigned train/dev/test semantics.",
            "Field presence does not establish human-verified supporting-evidence labels.",
            "Raw answers remain unchanged; normalized answer strings are an evaluation view only.",
        ],
    }
