# Movie records in the evidence candidate pool

The separately implemented `movie_evidence.py` adapter connects restored movie/person
name lookups to the existing evidence schema. A caller supplies up to two kind/name
proposals copied from exact Unicode-boundary question spans. This is a retrieval
interface, not automatic question parsing or a trained router.

Each actual local lookup returns at most two records by default, with a maximum of
ten. Each field is serialized separately with its entity kind, source record key,
record ID and original field/value. Provenance binds the snapshot revision, asset
hash/URL, row ID, record hash and field-value hash. These offsets refer to canonical
JSON serialization, not original source-file byte offsets. Repeated source fields
through different proposals have one evidence ID and retain both request links.

Records with more than 64 fields and canonical fields over 4,096 characters are
excluded with reasons; lists are never silently truncated. The source date remains
unknown. All name matches remain identity candidates. Neither a matching name nor
field fidelity proves temporal applicability, external truth or semantic support.

`source_controls.py` ranks a shared union of web chunks and API fields, capped at
twelve candidates under the existing generator configuration. It filters that same
pool for web-only, API-only and combined top-K/joint requests. Full chat/evidence
wrappers and output reserve enter the actual tokenizer cost. Term occurrence remains
the declared proxy; semantic groups/conflicts and automatic acceptance remain off.

## Real development probe

[The retained probe](../results/phase1/movie_evidence_smoke.json) uses three inspected
questions and manual query-copied lookup proposals. Every exported API field compares
to its own verified original record. Five actual local lookups prepare eighteen
requests; no answers are generated. Maximum reserved tokens by question are 1,336,
1,427 and 1,759, within the unchanged 2,048-token answer-request cap.

| Question | Shared pool: web/API | Result |
| --- | --- | --- |
| Director of Snow on tha Bluff | 10 / 2 | Combined selection contains an API field and web chunks |
| Terminator/Fast and Furious sequel comparison | 12 / 0 | API-only context empty; combined selection remains web-only |
| Streep/Jolie movie-role comparison | 12 / 0 | API-only context empty; combined selection remains web-only |

These failures are retained. Lexical ranking of the union can exclude every API
field, even when name lookup produced records. API field absence cannot establish
API irrelevance or source sufficiency. A separately measured retrieval-policy change
is needed before broader source composition. No independent accuracy, cross-source
benefit or complete roadmap evaluation is claimed.

```sh
uv run --locked --no-editable --extra generation \
  python scripts/movie_evidence_smoke.py --output runs/movie-evidence-probe.json
uv run --locked --no-editable --extra demo --extra constraints \
  pytest -q tests/test_movie_evidence.py
```

Required data-smoke CI repeats real snapshot/index/name restoration and this candidate
probe, using the manifests produced by that CI run. Three regression tests cover
field fidelity, complete-list retention/exclusion, repeated lookup deduplication,
invalid proposals, unknown names, shared pool filtering and full request budgets.
General query extraction, structured support, generated source-only comparisons,+fresh independent labels and adaptive live integration remain subsequent work.
