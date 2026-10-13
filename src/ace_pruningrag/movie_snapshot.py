"""Disk-indexed original movie/person/year records; exact ID/year lookup only."""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote

from .artifacts import sha256_file
from .assets import verify_asset

KINDS = {"movie_db.json": "movie", "person_db.json": "person", "year_db.json": "year"}


def object_records(path, chunk_size=1024 * 1024, max_record_chars=32 * 1024 * 1024):
    """Stream a root JSON object without loading the full snapshot into memory."""
    decoder = json.JSONDecoder(parse_constant=lambda value: _invalid_constant(value))
    with path.open(encoding="utf-8") as stream:
        buffer, position, ended = "", 0, False

        def more():
            nonlocal buffer, position, ended
            piece = stream.read(chunk_size)
            buffer, position = buffer[position:] + piece, 0
            ended = not piece

        def whitespace():
            nonlocal position
            while True:
                while position < len(buffer) and buffer[position].isspace():
                    position += 1
                if position < len(buffer) or ended:
                    return
                more()

        def punctuation(expected):
            nonlocal position
            whitespace()
            if position == len(buffer) or buffer[position] != expected:
                raise ValueError("movie snapshot JSON delimiter differs")
            position += 1

        def value():
            nonlocal position
            whitespace()
            while True:
                try:
                    result, end = decoder.raw_decode(buffer, position)
                except json.JSONDecodeError as exc:
                    if ended:
                        raise ValueError("incomplete or invalid movie snapshot JSON") from exc
                    if len(buffer) - position > max_record_chars:
                        raise ValueError("movie snapshot record exceeds explicit size cap") from exc
                    more()
                else:
                    if end - position > max_record_chars:
                        raise ValueError("movie snapshot record exceeds explicit size cap")
                    position = end
                    return result

        punctuation("{")
        whitespace()
        if position < len(buffer) and buffer[position] == "}":
            position += 1
        else:
            while True:
                key = value()
                if not isinstance(key, str):
                    raise ValueError("movie snapshot key must be a string")
                punctuation(":")
                item = value()
                if not isinstance(item, dict):
                    raise ValueError("movie snapshot records must be objects")
                # Also reject numeric overflow; preserve all other values/fields exactly.
                json.dumps(item, allow_nan=False)
                yield key, item
                whitespace()
                if position < len(buffer) and buffer[position] == "}":
                    position += 1
                    break
                punctuation(",")
        whitespace()
        if position != len(buffer):
            raise ValueError("trailing movie snapshot content")


def _invalid_constant(value):
    raise ValueError("nonfinite movie snapshot constant: " + value)


def build_index(config, root, output):
    """Atomic local index; original ID collisions retain last-record-wins semantics."""
    assets = config["assets"]
    if {Path(a["local_path"]).name for a in assets} != set(KINDS) or len(assets) != 3:
        raise ValueError("complete three-file movie snapshot required")
    for asset in assets:
        verify_asset(asset, root)
    if output.exists() or output.with_suffix(output.suffix + ".part").exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_suffix(output.suffix + ".part")
    counts, collisions = {}, {}
    with sqlite3.connect(partial) as db:
        db.execute(
            "CREATE TABLE records (kind TEXT, name TEXT, entity_id INTEGER, payload TEXT, "
            "PRIMARY KEY(kind,name))"
        )
        db.execute("CREATE INDEX records_by_id ON records(kind,entity_id)")
        db.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY,value TEXT)")
        for asset in assets:
            kind = KINDS[Path(asset["local_path"]).name]
            count, duplicates = 0, 0
            for name, record in object_records(root / asset["local_path"]):
                entity_id = record.get("id")
                if entity_id is not None and type(entity_id) is not int:
                    raise ValueError("snapshot entity ID must be an integer or absent")
                if entity_id is not None:
                    duplicates += int(
                        db.execute(
                            "SELECT 1 FROM records WHERE kind=? AND entity_id=? LIMIT 1",
                            (kind, entity_id),
                        ).fetchone()
                        is not None
                    )
                db.execute(
                    "INSERT INTO records VALUES (?,?,?,?)",
                    (
                        kind,
                        name,
                        entity_id,
                        json.dumps(record, ensure_ascii=False, allow_nan=False),
                    ),
                )
                count += 1
            counts[kind], collisions[kind] = count, duplicates
        for asset in assets:
            verify_asset(asset, root)
        metadata = {
            "revision": config["revision"],
            "source_assets": [{k: a[k] for k in ("local_path", "bytes", "sha256")} for a in assets],
            "record_counts": counts,
            "repeated_id_records": collisions,
            "id_collision_policy": "last_record_wins_as_in_original_lookup",
            "name_search_implemented": False,
            "external_truth_verified": False,
        }
        db.execute("INSERT INTO metadata VALUES (?,?)", ("manifest", json.dumps(metadata)))
    partial.rename(output)
    return {**metadata, "index_sha256": sha256_file(output), "index_bytes": output.stat().st_size}


class MovieSnapshot:
    def __init__(self, config, root, index, expected_index_sha256):
        for asset in config["assets"]:
            verify_asset(asset, root)
        if sha256_file(index) != expected_index_sha256:
            raise ValueError("movie index checksum differs")
        self.index = index
        with self.connection() as db:
            metadata = json.loads(
                db.execute("SELECT value FROM metadata WHERE key='manifest'").fetchone()[0]
            )
        expected = [{k: a[k] for k in ("local_path", "bytes", "sha256")} for a in config["assets"]]
        if metadata["revision"] != config["revision"] or metadata["source_assets"] != expected:
            raise ValueError("movie index source provenance differs")
        self.metadata = metadata

    @contextmanager
    def connection(self):
        db = sqlite3.connect(f"file:{quote(str(self.index.resolve()))}?mode=ro", uri=True)
        try:
            yield db
        finally:
            db.close()

    def lookup(self, endpoint, query):
        if endpoint == "/movie/get_year_info":
            if (
                not isinstance(query, str)
                or not query.isdecimal()
                or not 1990 <= int(query) <= 2021
            ):
                raise ValueError("year must be a string between 1990 and 2021")
            sql, args = "SELECT payload FROM records WHERE kind='year' AND name=?", (query,)
        else:
            kinds = {
                "/movie/get_movie_info_by_id": "movie",
                "/movie/get_person_info_by_id": "person",
            }
            if endpoint not in kinds:
                raise KeyError(endpoint)
            if type(query) is not int:
                raise ValueError("entity ID must be an integer")
            if not -(1 << 63) <= query < (1 << 63):
                # No restored ID exceeds SQLite's integer range; preserve unknown-ID nulls.
                return None
            sql = (
                "SELECT payload FROM records WHERE kind=? AND entity_id=? "
                "ORDER BY rowid DESC LIMIT 1"
            )
            args = (kinds[endpoint], query)
        with self.connection() as db:
            row = db.execute(sql, args).fetchone()
        return json.loads(row[0]) if row else None


def handler_for(snapshot):
    from http.server import BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass

        def respond(self, status, value):
            body = json.dumps(value, allow_nan=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 16384:
                    raise ValueError("invalid request size")
                value = json.loads(self.rfile.read(size))
                if not isinstance(value, dict) or set(value) != {"query"}:
                    raise ValueError("request must contain only query")
                result = snapshot.lookup(self.path, value["query"])
            except KeyError:
                self.respond(404, {"error": "endpoint outside restored movie slice"})
            except ValueError as exc:
                self.respond(400, {"error": str(exc)})
            else:
                self.respond(200, {"result": result})

    return Handler
