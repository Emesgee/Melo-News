# 0009. Media tamper-evidence is verified reader-side, not by the server

- **Status:** Accepted
- **Date:** 2026-07-05
- **Deciders:** Project owner + grill session, 2026-07-05
- **Relates to:** ADR-0003, ADR-0006, ADR-0008

## Context

We want a report's media to be provably the media the reporter signed (ADR-0008). The
obvious design — "the server re-hashes the uploaded photo and rejects a mismatch" —
**does not fit the architecture** for the lane that matters:

- **Authenticated Android** uploads media **phone → Azure directly** via a SAS URL.
  The server issues a short-lived write URL and only stores the resulting `media_url`
  string; it **never receives the bytes**, so it cannot re-hash them.
- The whole threat model (ADR-0003) assumes the server itself may be compromised or
  coerced. A tamper-evidence claim that only the server can vouch for is exactly the
  honeypot we are avoiding.

(Note the split: web and *anonymous* Android media transit the server and are EXIF-
stripped server-side; authenticated Android media is SAS-direct and sanitized only
on-device.)

## Decision

- **The consuming client verifies the media, not the server.** The signed report
  carries `media_sha256`; the reader's app/browser downloads the media, hashes it, and
  compares to the signed hash. Match → tamper-evident badge. Mismatch → the media is
  shown as **"unverified / possibly altered"**, a display state, not a server-side
  rejection (the server can't reject bytes it never saw).
- **The server just stores** the signed hash and signature. It may *optionally* fetch
  and check as a convenience backstop, but it is never the trust anchor.
- The "🔏 signed / tamper-evident" badge means **"cryptographically verifiable by
  you,"** not "the server says so."

## Consequences

- Not even a compromised server can forge the tamper-evidence badge — the math is the
  voucher.
- Reader clients (Android map viewer, and ideally web) must implement hashing and
  Ed25519 verification. Today neither does any client-side crypto.
- For large media on the web, hashing a downloaded blob has a cost; acceptable, and
  can be lazy (only when a reader inspects a report).
- Because on-device sanitization is authoritative for the Android lane, the bytes that
  are hashed/signed are the *sanitized* bytes; the server storing them verbatim keeps
  the hash stable.

## Staging (ADR-0015)

This reader-side verification is a **fast-follow, not the signing-slice first
cut.** In the first cut the `media_sha256` and signature are *signed and stored
verbatim* (so nothing here is foreclosed), but the 🔏 badge is temporarily
**server-attested** ("verified at ingest"), not the "verify it yourself" meaning
below. The reader-side upgrade lands before any real reporter (ADR-0011 gate).

## Code state (2026-07-05)

**Not implemented on any client.** No reader-side hashing or signature verification
exists in the web frontend or Android; the "🔏 signed" badge is currently a passive
server-provided boolean (`is_signed = bool(report_signature)`), and no report is ever
signed in the first place (ADR-0008 / ADR-0010). This ADR records the target design.
