# 0016. Drill identity: the signature is the reporter of record behind a JWT turnstile; the cohort is bootstrapped to rung 2 in setup

- **Status:** Accepted
- **Date:** 2026-07-05
- **Deciders:** Project owner + grill session, 2026-07-05
- **Relates to:** ADR-0003, ADR-0005, ADR-0007, ADR-0010, ADR-0011, ADR-0012, ADR-0013

## Context

With the signing scheme (ADR-0013), encoding (ADR-0014), and envelope (ADR-0015)
fixed, the last slice question is *how a device key becomes a trusted reporter*.
Two facts collide:

- `/stories/ingest` and `/stories/ingest/media-token` are `@jwt_required()`
  (`app/story/routes.py:210`, `:163`). The endpoint reads `get_jwt_identity()`
  and passes it into `ingest_story`, where `resolve_signed_reporter` **overrides**
  it with the signed pseudonym. So a reporter would need *both* a JWT login and a
  signature — two identities for one person.
- ADR-0003 says the pseudonym self-registers with **no signup and no server
  credential store** — a JWT (email/password account) is exactly the honeypot it
  rejects.

And a bootstrap chicken-and-egg: a fresh key self-registers at **rung 1**, so its
first signed report is **PENDING** (ADR-0005 gate) until a steward vouches it —
but the `User` to vouch does not exist until that first signed report.

## Decision

### (a) The signature is the reporter of record; JWT stays a turnstile for the drill

- **First cut:** keep the `@jwt_required()` gate on the signed lane. Testers
  authenticate with a throwaway login only to reach the endpoint; `ingest_story`
  already attributes the report to the **signed pseudonym** (`k-xxxx`), so readers
  only ever see the pseudonym and its track record. The JWT account is an
  invisible turnstile, not the identity.
- **Deferred to real-reporter hardening (ADR-0011):** make the **signature the
  sole auth** — drop `@jwt_required()`, remove the credential store (ADR-0003),
  and authenticate the media-token request with a small signed challenge from the
  device key. This is real endpoint-auth surface and removes a honeypot, but it is
  not needed for a dummy-data sandbox and belongs with the same gate as
  reader-side verification (ADR-0015 / ADR-0009).

Rationale: the drill's job is to prove signing + the trust display, which this
reaches without an auth rewrite. Removing the credential honeypot is important but
is a real-reporter concern, not a comprehension-drill concern.

### (b) Bootstrap the cohort to rung 2 during setup, not during the drill

- In **setup**, each tester files one throwaway "hello" signed report. That
  self-registers their pseudonym at **rung 1** (reusing
  `register_or_get_pseudonym`; **zero new endpoints**).
- The **steward vouches** each resulting `k-xxxx` to **rung 2** via the existing
  ADR-0012 endpoint `POST /moderation/users/<id>/rung`, which already recomputes
  the user's events.
- When the **drill proper** starts, every tester is rung 2, so reports
  auto-publish (ADR-0005) and corroboration + track record (ADR-0012) light up
  immediately — what the comprehension test needs to show.
- The **PENDING → approve → vouch** moderation path is still exercised, but
  **deliberately** (an anonymous or intentionally-unvouched submission), never by
  accidentally gating every tester's first real report.

## Consequences

- No auth rewrite in the slice; the JWT turnstile is reused as-is. The
  double-identity (JWT account vs pseudonym `User`) exists in the DB but is
  invisible to readers and harmless for the drill.
- No new server code for the bootstrap — the throwaway-report path plus the
  existing steward vouch cover it.
- A tracked debt: **remove the JWT/credential honeypot and move to
  signature-only auth before any real reporter** (folds into ADR-0011's gate).
- The trust ladder stays static/hand-vouched (ADR-0012); auto-climb (ADR-0005)
  remains out of scope.

## Code state (2026-07-05)

**Current:** both ingest endpoints are `@jwt_required()`; `resolve_signed_reporter`
overrides the JWT identity with the pseudonym when a report is signed; the steward
rung-vouch endpoint exists and recomputes events. **Not yet built:** any client
that signs (so no pseudonym is ever created in practice), and the deferred
signature-only auth. This ADR fixes the drill's identity + bootstrap approach; it
lands with the ADR-0010 signing slice.
