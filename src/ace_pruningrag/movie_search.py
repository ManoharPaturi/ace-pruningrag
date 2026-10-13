"""Disk-backed BM25Okapi name search over preserved movie/person record keys."""

import json
import math
import sqlite3
import string
from collections import Counter, defaultdict
from contextlib import contextmanager
from urllib.parse import quote

from .artifacts import sha256_file

PARAMETERS = {"k1": 1.5, "b": 0.75, "epsilon": 0.25, "tie_break": "source_rowid_desc"}


def normalize_name(value):
    return " ".join(
        value.lower().replace("_", " ").translate(str.maketrans("", "", string.punctuation)).split()
    )


def build_search(snapshot, output):
    """Build separate term postings; never modify the original record index."""
    partial = output.with_suffix(output.suffix + ".part")
    if output.exists() or partial.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    original_hash = sha256_file(snapshot.index)
    with sqlite3.connect(partial) as db, snapshot.connection() as source:
        db.execute(
            "CREATE TABLE documents(docid INTEGER PRIMARY KEY,kind TEXT,name TEXT,length INTEGER)"
        )
        db.execute(
            "CREATE TABLE postings(kind TEXT,term TEXT,docid INTEGER,tf INTEGER,"
            "PRIMARY KEY(kind,term,docid))"
        )
        db.execute(
            "CREATE TABLE terms(kind TEXT,term TEXT,df INTEGER,idf REAL,ordinal INTEGER,"
            "PRIMARY KEY(kind,term))"
        )
        db.execute("CREATE TABLE stats(kind TEXT PRIMARY KEY,n INTEGER,avgdl REAL)")
        db.execute("CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT)")
        vocabulary = {k: {} for k in ("movie", "person")}
        counts, lengths = Counter(), Counter()
        for docid, kind, name in source.execute(
            "SELECT rowid,kind,name FROM records WHERE kind IN ('movie','person') ORDER BY rowid"
        ):
            tokens = name.split()  # Original corpus uses stored keys, not re-normalized titles.
            db.execute("INSERT INTO documents VALUES (?,?,?,?)", (docid, kind, name, len(tokens)))
            counts[kind] += 1
            lengths[kind] += len(tokens)
            for term, frequency in Counter(tokens).items():
                vocabulary[kind][term] = vocabulary[kind].get(term, 0) + 1
                db.execute("INSERT INTO postings VALUES (?,?,?,?)", (kind, term, docid, frequency))
        for kind, frequencies in vocabulary.items():
            if not counts[kind] or not frequencies or not lengths[kind]:
                raise ValueError("BM25 name corpus must have documents and tokens")
            n = counts[kind]
            idfs = {
                term: math.log(n - df + 0.5) - math.log(df + 0.5)
                for term, df in frequencies.items()
            }
            average_idf = sum(idfs.values()) / len(idfs)
            for ordinal, (term, df) in enumerate(frequencies.items()):
                idf = idfs[term] if idfs[term] >= 0 else PARAMETERS["epsilon"] * average_idf
                db.execute("INSERT INTO terms VALUES (?,?,?,?,?)", (kind, term, df, idf, ordinal))
            db.execute("INSERT INTO stats VALUES (?,?,?)", (kind, n, lengths[kind] / n))
        if sha256_file(snapshot.index) != original_hash:
            raise ValueError("source movie index changed during search build")
        metadata = {
            "source_index_sha256": original_hash,
            "parameters": PARAMETERS,
            "document_counts": dict(counts),
            "vocabulary_sizes": {k: len(v) for k, v in vocabulary.items()},
            "ranking_reproduction_verified": False,
            "semantic_identity_verified": False,
        }
        db.execute("INSERT INTO metadata VALUES (?,?)", ("manifest", json.dumps(metadata)))
    partial.rename(output)
    return {
        **metadata,
        "search_index_sha256": sha256_file(output),
        "search_index_bytes": output.stat().st_size,
    }


class MovieNameSearch:
    def __init__(self, snapshot, index, expected_sha256):
        if sha256_file(index) != expected_sha256:
            raise ValueError("movie search index checksum differs")
        self.snapshot, self.index = snapshot, index
        with self.connection() as db:
            metadata = json.loads(
                db.execute("SELECT value FROM metadata WHERE key='manifest'").fetchone()[0]
            )
        if (
            metadata["source_index_sha256"] != sha256_file(snapshot.index)
            or metadata["parameters"] != PARAMETERS
        ):
            raise ValueError("movie name-search source or parameters differ")
        self.metadata = metadata

    @contextmanager
    def connection(self):
        db = sqlite3.connect(f"file:{quote(str(self.index.resolve()))}?mode=ro", uri=True)
        try:
            yield db
        finally:
            db.close()

    def search(self, kind, query, limit=10):
        if kind not in ("movie", "person") or not isinstance(query, str):
            raise ValueError("name search needs a known kind and string query")
        if type(limit) is not int or not 1 <= limit <= 10:
            raise ValueError("name search limit must be 1–10")
        tokens, scores = normalize_name(query).split(), defaultdict(float)
        with self.connection() as db:
            _, avgdl = db.execute("SELECT n,avgdl FROM stats WHERE kind=?", (kind,)).fetchone()
            for term in tokens:
                row = db.execute(
                    "SELECT idf FROM terms WHERE kind=? AND term=?", (kind, term)
                ).fetchone()
                if row is None:
                    continue
                idf = row[0]
                for docid, frequency, length in db.execute(
                    "SELECT p.docid,p.tf,d.length FROM postings p "
                    "JOIN documents d ON d.docid=p.docid "
                    "WHERE p.kind=? AND p.term=? ORDER BY p.docid",
                    (kind, term),
                ):
                    numerator = frequency * (PARAMETERS["k1"] + 1)
                    denominator = frequency + PARAMETERS["k1"] * (
                        1 - PARAMETERS["b"] + PARAMETERS["b"] * length / avgdl
                    )
                    scores[docid] += idf * (numerator / denominator)
            # Preserve ranking before zero filtering, including negative-score corpora.
            candidates, zero_count = list(scores.items()), 0
            for (docid,) in db.execute(
                "SELECT docid FROM documents WHERE kind=? ORDER BY docid DESC", (kind,)
            ):
                if docid not in scores:
                    candidates.append((docid, 0.0))
                    zero_count += 1
                    if zero_count >= limit:
                        break
            ranked = [
                (docid, score)
                for docid, score in sorted(candidates, key=lambda v: (-v[1], -v[0]))[:limit]
                if score != 0
            ]
            results = []
            with self.snapshot.connection() as source:
                for docid, score in ranked:
                    name = db.execute(
                        "SELECT name FROM documents WHERE docid=?", (docid,)
                    ).fetchone()[0]
                    payload = source.execute(
                        "SELECT payload FROM records WHERE rowid=? AND kind=?", (docid, kind)
                    ).fetchone()
                    if payload is None or not math.isfinite(score):
                        raise ValueError("name search record or score differs")
                    results.append(
                        {
                            "source_rowid": docid,
                            "name": name,
                            "score": score,
                            "record": json.loads(payload[0]),
                        }
                    )
        return results

    def lookup(self, endpoint, query):
        kinds = {"/movie/get_movie_info": "movie", "/movie/get_person_info": "person"}
        if endpoint in kinds:
            return [r["record"] for r in self.search(kinds[endpoint], query)]
        return self.snapshot.lookup(endpoint, query)
