"""Bounded movie lookup proposals and provenance-bound field candidates, never answers."""

import json

from .claim_extraction import digest
from .evidence import Evidence
from .unicode_claims import permitted_spans


def retrieve_movie_evidence(
    query, requests, search, config, *, max_records=2, max_field_chars=4096
):
    """Caller supplies query-copied name spans; no router or identity truth is implied."""
    if not isinstance(requests, list) or len(requests) > 2:
        raise ValueError("at most two movie name requests are permitted")
    if type(max_records) is not int or not 1 <= max_records <= 10:
        raise ValueError("movie record cap must be 1–10")
    if type(max_field_chars) is not int or not 1 <= max_field_chars <= 16384:
        raise ValueError("movie field character cap must be 1–16384")
    allowed, seen = set(permitted_spans(query.query)), set()
    for request in requests:
        if (
            not isinstance(request, dict)
            or set(request) != {"kind", "span"}
            or request["kind"] not in ("movie", "person")
            or not isinstance(request["span"], str)
            or request["span"] not in allowed
        ):
            raise ValueError("movie requests need a known kind and exact query name span")
        identity = (request["kind"], request["span"])
        if identity in seen:
            raise ValueError("duplicate movie request")
        seen.add(identity)
    assets = {
        "movie" if a["local_path"].endswith("movie_db.json") else "person": a
        for a in config["assets"]
        if a["local_path"].endswith(("movie_db.json", "person_db.json"))
    }
    if set(assets) != {"movie", "person"} or any(not a.get("url") for a in assets.values()):
        raise ValueError("movie evidence needs both original asset URLs")
    evidence, provenance, calls, excluded = {}, {}, [], []
    for request in requests:
        kind = request["kind"]
        rows = search.search(kind, request["span"], limit=max_records)
        calls.append(
            {
                "endpoint": "/movie/get_movie_info"
                if kind == "movie"
                else "/movie/get_person_info",
                "query_span": request["span"],
                "lookup_implementation": "local_disk_name_search",
                "record_limit": max_records,
                "returned_source_rowids": [r["source_rowid"] for r in rows],
                "candidate_search_complete": False,
                "semantic_identity_verified": False,
            }
        )
        for row in rows:
            record = row["record"]
            if not isinstance(record, dict) or len(record) > 64:
                excluded.append({"source_rowid": row["source_rowid"], "reason": "record_shape_cap"})
                continue
            for field, value in sorted(record.items()):
                content = json.dumps(
                    {
                        "entity_kind": kind,
                        "source_name": row["name"],
                        "record_id": record.get("id"),
                        "field": field,
                        "value": value,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                    allow_nan=False,
                )
                if len(content) > max_field_chars:
                    excluded.append(
                        {
                            "source_rowid": row["source_rowid"],
                            "field": field,
                            "reason": "field_character_cap",
                            "canonical_chars": len(content),
                        }
                    )
                    continue  # Never truncate a list or invent a smaller complete source value.
                binding = {
                    "revision": config["revision"],
                    "asset_sha256": assets[kind]["sha256"],
                    "asset_url": assets[kind]["url"],
                    "source_rowid": row["source_rowid"],
                    "source_name": row["name"],
                    "entity_kind": kind,
                    "record_field": field,
                    "record_sha256": digest(record),
                    "field_value_sha256": digest(value),
                }
                identity = digest({"interaction_id": query.interaction_id, **binding})
                if identity in evidence:
                    provenance[identity]["request_spans"].append(request["span"])
                    continue  # The same source field through two requests is one candidate.
                evidence[identity] = Evidence(
                    identity,
                    query.interaction_id,
                    "api",
                    -1,
                    assets[kind]["url"],
                    f"{row['name']} / {field}",
                    "",
                    "canonical_record_field",
                    0,
                    len(content),
                    content,
                    len(content.split()),
                )
                provenance[identity] = {
                    **binding,
                    "canonical_content_sha256": digest(content),
                    "snapshot_observation_time": None,
                    "semantic_identity_verified": False,
                    "semantic_support_verified": False,
                    "request_spans": [request["span"]],
                }
    return list(evidence.values()), {
        "scope": "Bounded query-copied movie/person candidates; no identity/support acceptance",
        "interaction_id": query.interaction_id,
        "source_calls": len(calls),
        "calls": calls,
        "candidate_fields": len(evidence),
        "excluded_fields": excluded,
        "provenance": provenance,
        "source_index_sha256": search.metadata["source_index_sha256"],
        "tie_policy": search.metadata["parameters"]["tie_break"],
        "answer_acceptance_enabled": False,
    }
