# 0014. The canonical signing message: every signed value is a string or null; the client is the sole formatter

- **Status:** Accepted
- **Date:** 2026-07-05
- **Deciders:** Project owner + grill session, 2026-07-05
- **Relates to:** ADR-0003, ADR-0008, ADR-0009, ADR-0013

## Context

A signature verifies or it does not — there is no "close." So the Android
client (Kotlin) and the server (`app/identity/signing.py`, Python) must build
**byte-identical** canonical bytes before the client signs and the server
verifies. The server's rule today:

```python
json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
```

The dangerous field is numeric. `lat`/`lon` are `Double`, and Python's
float→string (`json.dumps(0.1+0.2)` → `"0.30000000000000004"`) is **not**
reproducible by Kotlin/Gson/Moshi. One differing digit fails verification every
time. `published_at` (a client timestamp) has the same cross-language hazard for
its string form. The other mechanics (key order, null handling, unicode) are
deterministic and just need pinning.

## Decision

**Every value in the signed canonical message is a JSON string or JSON null —
never a JSON number, float, or bool. The authoring client is the single
component that ever formats a value derived from a number or a time, and the
server signs and persists that value verbatim.**

Concrete rules:

- **Coordinates are fixed-precision strings.** `lat`/`lon` are formatted by the
  client to **exactly 5 fractional digits** (≈ 1.1 m) and carried as strings,
  e.g. `"lat":"32.15012"`, `"lon":"-0.10000"`. 5 decimals is finer than
  corroboration needs (clustering uses a 1 km radius, `events/service.py`) and
  deliberately coarsens the exact location — a privacy win, not just a
  correctness one. The **stored and displayed** coordinate equals the signed
  coarsened value, so what a reader sees is exactly what was signed.
- **Timestamps are client-formatted strings** (`published_at` as a single pinned
  ISO-8601 form, UTC, e.g. `2026-07-05T14:03:00Z`), emitted by the client and
  never re-serialized downstream.
- **Canonical form:** compact, sorted-key JSON —
  `sort_keys=True, separators=(",",":"), ensure_ascii=False`, UTF-8 bytes.
- **Null, not absent:** every signed field name is present; a missing value is
  explicit `null` (matches the server's `payload.get(k)`).
- **One structured exception (`tags`):** ADR-0015 signs `tags` as a *sorted array
  of plain strings*. Arrays of strings serialize byte-identically across Python
  and Kotlin, so they carry no number/float/bool hazard — the rule above is about
  killing numeric formatting, which arrays-of-strings do not reintroduce.
- **Server stays a verbatim pass-through.** `canonical_message` continues to take
  each field straight from the payload; because coordinates/timestamps arrive
  pre-formatted as strings, the server never formats a number and cannot diverge
  from the client.

### Why this removes the hazard entirely

With no numeric/float/bool values in the signed doc, **no component ever
performs cross-language float or number formatting on the trust path:**

- Authoring client formats the coordinate once → signs the string.
- Server verifies and **persists the signed values byte-exactly** (the canonical
  message / signed field values, not just a re-parsed float).
- Reader-side verification (ADR-0009) rebuilds the doc from those stored verbatim
  strings — no reformatting, so byte-identical by construction.

The coordinate-rounding rule therefore becomes a purely client-side
precision/privacy choice, **not** a correctness-critical contract that two
languages must reproduce forever.

## Consequences

- `IngestRequest` (Android) carries `lat`/`lon` as **strings**; `ingest_story`
  parses them to floats only for storage/clustering while storing the coarsened
  value, and the exact signed values are persisted for reader-side verification.
- After this change **every signed field is a string or null**, so the JSON
  canonicalization layer has zero numeric ambiguity — the strongest form of the
  guarantee.
- A **shared test vector** (a fixed set of coordinate→string and doc→bytes cases)
  is asserted by both the server unit tests and the Android tests, as the
  regression guard the whole slice leans on.
- Storing signed values verbatim is a prerequisite for ADR-0009 exactness; a
  schema that kept only a re-parsed float would silently break reader-side
  verification. (Feeds ADR-0010's open "0009 in first cut or fast-follow"
  question.)
- The signed **field set** itself is unchanged here — expanding it to the ADR-0008
  set (`media_sha256`, `is_sensitive`, `source_type`, `subject`, `tags`) is the
  next fork; this ADR fixes only the *encoding* of whatever fields are signed.

## Code state (2026-07-05)

**Server half done.** `canonical_message`/`_SIGNED_FIELDS` in
`app/identity/signing.py` now build the all-string envelope verbatim from the
payload; `ingest_story` persists the exact bytes in the new
`file_uploads.signed_message` column (auto-migrated). The encoding is frozen in
`app/identity/signing_test_vectors.json` and asserted by the server tests (the
Android client will assert the same file). **Client half absent:** no client
produces the 5-decimal-string coordinates or signs anything yet (ADR-0010).
