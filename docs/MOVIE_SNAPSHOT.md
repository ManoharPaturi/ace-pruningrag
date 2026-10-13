# Original movie snapshot restoration and exact lookup

The pinned CRAG release publishes movie, person and year records via Git LFS.
The [asset configuration](../configs/crag_movie.json) records each immutable URL,
published LFS size and SHA-256, with a 250 MB download ceiling. All three files
are restored and verified: **235,448,639 bytes** total. Original files remain intact.
The sources are the [pinned movie data directory](https://github.com/facebookresearch/CRAG/tree/ad1518887dd4d9ebcd7de95388c7a62751e7705c/mock_api/cragkg/movie)
and [original lookup contract](https://github.com/facebookresearch/CRAG/blob/ad1518887dd4d9ebcd7de95388c7a62751e7705c/mock_api/cragapi/movie.py).

The first-party adapter streams each root JSON object into a disk-backed SQLite
index instead of loading the full snapshot into memory. It preserves all decoded
record fields, nulls, nomination/winner booleans and original numeric IDs. Nonfinite
values, oversized records and unexpected record/ID shapes fail instead of being
silently skipped. Original assets are checksum-verified before and after indexing.
Existing indexes or partial destinations are not overwritten.

[Index manifest](../results/phase1/movie_index.json) records **64,283 movie records,
373,608 person records and 35 year records**, with a 301,989,888-byte local index.
There are 11 repeated person-ID records. ID lookups retain the original last-record-wins
behavior; repetition is not independent confirmation and does not establish that
the last record is externally correct. Original names and records remain in the index.

The implemented valid-request wire formats are:

| Endpoint | Query | Result |
| --- | --- | --- |
| `/movie/get_movie_info_by_id` | Integer movie ID | Full original record or null |
| `/movie/get_person_info_by_id` | Integer person ID | Full original record or null |
| `/movie/get_year_info` | Year string in 1990–2021 | Full original year record or null |

Each POST body is `{"query": ...}` and each successful response is `{"result": ...}`.
The adapter rejects boolean IDs and additional request keys. Connections open
SQLite in read-only mode; queries are parameterized. The initial ID/year adapter rejects name routes. The separate BM25 wrapper below
now restores those routes with a disclosed score-tie policy. Complete original
ranking and semantic identity are not asserted.

The snapshot stores 1990–2024, but the released year method accepts only 1990–2021.
That restriction is preserved. A later range expansion must be explicitly versioned
and measured as a behavior change; historical results must not be silently migrated.
Snapshot facts and release dates are not current observations or externally verified
truth. Missing fields and lookup results remain missing; no currency, date or entity
identity is inferred from familiarity.

[Real HTTP smoke](../results/phase1/movie_snapshot_smoke.json) checks movie ID 769,
person ID 19384, year 1990 and an unknown ID against the original source records.
The movie/person expected records are obtained by a separate source scan retaining
the original ID-collision order; the small year file uses the standard full JSON
reader. Year 2024, name-search and boolean-ID probes verify the explicit errors.
Four unit tests cover streamed Unicode/escaped fields, record caps, nonfinite values,
original collision semantics, nomination flags, read-only connections, provenance
tampering and the valid HTTP shapes. All 208 local tests pass.

Reproduce in fresh output paths:

```sh
uv run --locked --no-editable python scripts/fetch_movie_assets.py \
  --output runs/movie-v2/assets.json
uv run --locked --no-editable python scripts/build_movie_index.py \
  --output data/crag/movie/snapshot-v2.sqlite \
  --manifest runs/movie-v2/index.json
uv run --locked --no-editable python scripts/movie_snapshot_smoke.py \
  --index data/crag/movie/snapshot-v2.sqlite \
  --manifest runs/movie-v2/index.json \
  --output runs/movie-v2/http.json
```

The required `data-smoke` CI job now downloads/verifies the real assets, builds the
index and executes the HTTP probes. Raw files and the large index remain ignored;
compact provenance manifests and probe hashes are committed.

Next, add explicit entity lookup/routing, render bounded API evidence with field-level
provenance, and test it with web evidence using reviewed requirements and source-only
controls. This restoration makes no generator/judge calls and establishes no joint
selection improvement. Music, sports, open-domain backing, the original router/model
contract and full scientific gates remain open.


## Movie/person name search

`movie_search.py` adds a separate 79,896,576-byte postings index over all 64,283 movie
and 373,608 person keys. The original record index stays unchanged. Query normalization
retains lowercase, underscore-to-space, ASCII punctuation removal and whitespace
collapse. Stored corpus keys are split as published. BM25Okapi parameters are
k1=1.5, b=0.75 and epsilon=0.25; negative IDFs use the vocabulary-average floor.
The implementation follows the [primary BM25 reference](https://github.com/dorianbrown/rank_bm25/blob/master/rank_bm25.py);
`rank-bm25==0.2.2` is a pinned development/reference dependency, not the runtime
search engine. Its locked source hash is recorded in the actual score checks.

The wrapper adds `/movie/get_movie_info` and `/movie/get_person_info`, with string
queries and `{"result": [records]}` responses. It forwards the three ID/year routes.
Up to 10 source records are returned. The original ranks before removing zero scores;
that rule is retained even when negative scores would otherwise be displaced by
zero-scored documents. Query scores are relevance values, not calibrated confidence
or proof of entity identity. No first candidate is automatically accepted as the
requested entity.

Score ties use source-row descending order. The original NumPy ordering is not
guaranteed stable across ties; this is an explicit adaptation. [Seven real probes](../results/phase1/movie_name_smoke.json)
have exact returned-score agreement and source-matching HTTP responses. Five have
different ranked IDs. The [ranked-score sequence check](../results/phase1/movie_name_score_sequences.json)
confirms matching score sequences; differences occur among equal-score candidates.
This is not proof of complete original ranking, retrieval recall or semantic support.
Probe terms are inspected development examples, not unseen evaluation cases.

Four tests compare numeric scores against the reference, including repeated terms,
negative IDFs, zero filtering, explicit ties, integrity/read-only checks and limits.
The full 208-test suite passes. Required data-smoke CI now rebuilds the name index
and repeats the actual reference/HTTP checks.

```sh
uv run --locked --no-editable python scripts/build_movie_search.py \
  --records data/crag/movie/snapshot.sqlite \
  --records-manifest results/phase1/movie_index.json \
  --output data/crag/movie/names-v2.sqlite \
  --manifest runs/movie-v2/names.json
uv run --locked --no-editable python scripts/movie_name_smoke.py \
  --records data/crag/movie/snapshot.sqlite \
  --records-manifest results/phase1/movie_index.json \
  --names data/crag/movie/names-v2.sqlite \
  --names-manifest runs/movie-v2/names.json \
  --output runs/movie-v2/name-http.json
```
