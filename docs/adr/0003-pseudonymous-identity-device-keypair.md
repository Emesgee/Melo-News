# 0003. Pseudonymous identity anchored to a device keypair; no server credential store

- **Status:** Accepted
- **Date:** 2026-07-05
- **Deciders:** Project owner (design interviews)
- **Relates to:** ADR-0001, ADR-0004, ADR-0007, ADR-0008
- **Refined by:** ADR-0013 (signing algorithm is P-256 in the Android Keystore, not
  software Ed25519 — the device-keypair-as-pseudonym model below is unchanged)

## Context

Readers need to trust reports from people who cannot safely use their real names.
Real-name or KYC-style identity is rejected outright: in this threat model a
server-side store of who-is-who is a honeypot that endangers reporters if seized or
subpoenaed.

We need an identity that (a) carries no real-world name, (b) accrues a visible track
record over time so credibility can be *earned*, and (c) does not create a central
secret the platform could be coerced into surrendering.

## Decision

- **Pseudonymous-first identity.** A reporter is a persistent pseudonym with a track
  record ("14 reports, 11 corroborated"). Fully-anonymous submission remains a
  fallback, visibly marked unverifiable.
- **The credential is a device-held keypair** (algorithm set by ADR-0013:
  ECDSA P-256 in the Android Keystore; originally drafted as Ed25519). The public
  key *is* the pseudonym. Reports are signed on-device (see ADR-0008), so authorship is
  tamper-evident even through relays. There is **no server-side credential store** —
  the server keeps only public keys.
- **Self-registration:** the first valid signed report from a new key creates its
  pseudonymous account (rung 1); no signup step.
- **Recovery is opt-in, not default:** losing the device with no exported (reporter-
  controlled, passphrase-encrypted) key backup means the reputation resets. That cost
  is accepted to avoid a server honeypot.
- The `User` table is the single identity+reputation anchor (no separate table); it
  gains `public_key`, `display_handle`, `identity_type`, reputation fields, and
  nullable `email`/`password`.

## Consequences

- No honeypot: the server cannot deanonymize reporters because it never holds the
  secret.
- Keys are free to mint, so a fresh key earns nothing — the trust ladder and
  corroboration rules (ADR-0004) must assume Sybil abundance.
- The signing client is a hard dependency for this identity to mean anything.

## Code state (2026-07-05)

**Server half built:** `User` has all the fields; `app/identity/signing.py` verifies
signatures and self-registers pseudonyms; wired into `ingest_story`
(`app/story/service.py`). (The verify path is Ed25519 today and must move to
ECDSA-P256 per ADR-0013 before the Hetzner deploy freezes the scheme.) **Client half absent:** the Android app has no keypair, no
signing, and sends no `public_key` — so no pseudonymous identity is ever actually
created in practice yet (see ADR-0008 / ADR-0010). Web accounts use the
`email`/`password` (`registered`) path and are not pseudonymous.
