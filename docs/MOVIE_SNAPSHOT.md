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
SQLite in read-only mode; queries are parameterized. Name search/fuzzy BM25 is not
implemented and those routes return 404. This is three restored lookup paths,
not a reproduction of every original server/search behavior.

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
tampering and the valid HTTP shapes. All 204 local tests pass.

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
