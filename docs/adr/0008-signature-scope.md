# 0008. A report signature covers the reporter's claims, including the media

- **Status:** Accepted
- **Date:** 2026-07-05
- **Deciders:** Project owner + grill session, 2026-07-05
- **Relates to:** ADR-0003, ADR-0006, ADR-0009

## Context

On-device signing (ADR-0003) exists to make a report tamper-evident — provably
unaltered from what the reporter attested, even after passing through relays or a
compromised server. That guarantee is only as good as *what the signature covers*.

The initial server contract (`app/identity/signing.py`) signs ten text fields:
`body, city, country, lat, local_id, lon, public_key, published_at, severity, title`.
It does **not** cover the attached photo/video, nor `is_sensitive`, `source_type`,
`subject`, or `tags`. So a relay or a compromised server could **swap the photo** or
**flip off the `is_sensitive` safety flag** and the signature would still verify —
defeating the entire point on the two fields (evidence, safety) that matter most.

There are zero signing clients today, so the contract is still free to change without
breaking anyone. Once an app ships and signs a report, changing the covered set breaks
every prior signature.

## Decision

**The signature covers everything the reader treats as the reporter's claim; it
leaves out only what the server assigns.** Concretely:

- **Signed:** title, body, city, country, lat, lon, severity, **a hash of the media
  bytes** (`media_sha256`, null when text-only), **`is_sensitive`**, `source_type`,
  `subject`, `tags`, plus the client-set `public_key`, `published_at`, `local_id`.
- **Not signed** (server-owned, changes over time): moderation/verification status,
  `event_id`, `trust_rung`, corroboration counts, server timestamps.

This rule is future-proof: any new field a reporter fills in gets signed; anything the
platform computes does not.

## Consequences

- The Android client must hash the (already on-device-sanitized) media bytes before
  signing, and include that hash in the canonical message. Trivial cost.
- The media hash is only meaningful if someone re-hashes the actual bytes and
  compares — and because the server never sees Android media bytes (ADR-0009), that
  verification happens **reader-side** (ADR-0009), not at ingest.
- The canonical-message field set and ordering become a versioned contract; changing
  it later requires a version bump, not a silent edit.
- `is_sensitive` being signed means a relay can't strip a reporter's "hold this"
  safety flag.

## Code state (2026-07-05)

**Not yet implemented.** The current `_SIGNED_FIELDS` in `app/identity/signing.py`
covers only the ten text fields and **not** media/`is_sensitive`/`source_type`/
`subject`/`tags`. No media hashing exists anywhere (backend or Android). This ADR
records the agreed target; the change is safe to make now precisely because there is
no signing client in the field yet.
