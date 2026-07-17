# 0015. Signing-slice first cut: sign the full ADR-0008 envelope now; defer reader-side verification

- **Status:** Accepted
- **Date:** 2026-07-05
- **Deciders:** Project owner + grill session, 2026-07-05
- **Relates to:** ADR-0008, ADR-0009, ADR-0010, ADR-0013, ADR-0014
- **Resolves:** the ADR-0010 open item "reader-side media verification (ADR-0009)
  in the drill's first cut or a fast-follow"

## Context

The Android signing slice (ADR-0010) is being built, with the P-256 scheme
(ADR-0013) and the canonical encoding (ADR-0014) already fixed. Two things still
had to be settled, and both share a hard deadline — the **field set freezes the
moment a client ships**, exactly like the scheme:

1. Which fields the signature actually covers (ADR-0008 decided the intent but
   `signing.py` still binds only the old ten).
2. Whether the media hash is merely *signed* now or also *verified reader-side*
   now (ADR-0009), which is real client-crypto work in every reader.

## Decision

**Sign the complete ADR-0008 envelope in the first cut, including the media hash;
defer only the reader-side verification UI.**

### 1. Freeze the full envelope now

The signed field set is locked to the ADR-0008 set and will not change without a
version bump. Per ADR-0014, every value is a string or null, formatted by the
client and signed/stored verbatim:

| Field | Signed form |
|-------|-------------|
| `title`, `body`, `city`, `country`, `subject`, `source_type` | string or null |
| `severity` | string (`LOW`/`MEDIUM`/`HIGH`) |
| `lat`, `lon` | fixed **5-decimal** string (ADR-0014), null if withheld |
| `published_at` | pinned ISO-8601 UTC string, e.g. `2026-07-05T14:03:00Z` |
| `local_id`, `public_key` | string |
| `is_sensitive` | string **`"true"`/`"false"`** (no bool in the doc) |
| `media_sha256` | lowercase **hex** string of the sanitized bytes; **null** when text-only |
| `tags` | **sorted JSON array of strings** (see note) |

**`tags` encoding (amends ADR-0014):** ADR-0014's "string or null" rule existed
to kill cross-language *number/float/bool* formatting. `tags` is signed as a
**sorted array of plain strings** — arrays of strings serialize byte-identically
across Python and Kotlin, so they carry no such hazard. It is the one structured
value in the doc; sorting makes it order-independent. Empty/absent → `null`.

### 2. Sign `media_sha256` in the first cut

The client computes SHA-256 over the **sanitized** bytes — the `File` that exists
right after `MediaSanitizer.sanitizeForUpload()` in `SyncManager.uploadMedia`
(and the anonymous drain) — and includes the hex digest in the signed doc. This
must be first-cut: a report's media hash can only be signed at authoring time, so
skipping it now leaves those reports permanently unverifiable.

### 3. Defer reader-side verification (ADR-0009) to a fast-follow

The reader-side "download, re-hash, verify signature, light a tamper-evident
badge" work is deferred. Everything it needs is signed and **persisted verbatim**
from day one — the signature, `public_key`, the canonical doc (ADR-0014), and
`media_sha256` — so turning it on later breaks no prior signature.

**First-cut badge semantics (temporary):** the 🔏 badge means *"the server
verified this signature at ingest"* (`resolve_signed_reporter` already rejects an
invalid signature), **not** ADR-0009's stronger *"you can verify it yourself."*
This is an accepted, temporary retreat from the anti-honeypot ideal — the sandbox
drill runs on dummy data and tests whether readers *understand* the trust
display, not whether the system resists a compromised server. The reader-side
upgrade lands before any real reporter (ADR-0011 gate territory).

## Consequences

- `_SIGNED_FIELDS` in `app/identity/signing.py` expands to the table above, with
  the string/array encodings, landing with the ADR-0013 rewrite before deploy.
- `IngestRequest` (Android) and the anonymous `@Part` set gain `public_key`,
  `signature`, `is_sensitive`, `source_type`, `subject`, and `media_sha256`; the
  Room entities gain columns for the signature/public_key/hash so they survive
  offline queueing (the send happens later in the sync managers).
- The server must **persist the signed values byte-exactly** (prerequisite for
  the deferred ADR-0009), not just re-parsed floats.
- The shared server+Android **test vector** (ADR-0014) is extended to cover the
  bool-as-string, hex-hash, and sorted-tags-array cases.
- The 🔏 badge is honest-but-weaker until the ADR-0009 fast-follow; documented so
  no trainer/reader over-reads it.

## Code state (2026-07-05)

**Server half done.** `_SIGNED_FIELDS` now binds the full envelope
(incl. `media_sha256`, `is_sensitive` as `"true"/"false"`, sorted-array `tags`);
`ingest_story` parses + stores the signed `is_sensitive` (read by the rung gate's
safety override) and persists the canonical message. The frozen test vector
covers the bool-as-string, hex-hash, and sorted-tags cases. **Client + reader
absent:** no client computes `media_sha256` or signs; no reader does client-side
crypto — the 🔏 badge remains the passive server-attested boolean until the
ADR-0009 fast-follow.
