# 0006. Reader trust display shows the basis of trust, never a binary "verified"

- **Status:** Accepted
- **Date:** 2026-07-05
- **Deciders:** Project owner (design interviews)
- **Relates to:** ADR-0001, ADR-0004, ADR-0009

## Context

A green "Verified ✓" checkmark is a lie waiting to happen: it collapses three very
different claims — "a moderator glanced at this" (weak), "independent people
corroborated it" (strong, falsifiable), and "the media is authentic" (which we should
never assert) — into one badge that readers over-trust.

## Decision

Show the **basis** of trust, kept visually distinct, never a single binary:

- **Event badge:** `DEVELOPING` / `CORROBORATED` / `DISPUTED` / `CLOSED`.
- **Corroboration shown concrete and split:** "✓ N corroborating" (distinct
  identities) vs "+N anonymous" (supporting, explicitly *not counted*). Never merged.
- **Confidence as a Low/Med/High band**, labelled an automated estimate, secondary to
  human corroboration. The raw decimal is never shown (false precision).
- **Reporter chip:** handle + track record; "new reporter" and "anonymous —
  unverifiable" get muted styling; a signed report gets a tamper-evidence badge.
- **DISPUTED is shown prominently**, not hidden.
- The public serializer must **never** leak `author_user_id` — it exposes a `reporter`
  object (handle, rung, counts, is_anonymous, is_signed) instead.

## Consequences

- Readers calibrate instead of blindly trusting a checkmark.
- The "signed / tamper-evident" badge is only honest if it means something
  cryptographic — see ADR-0009. A passive server boolean is not enough.
- The reporter chip is only meaningful once the track record is populated (ADR-0004
  gap).

## Code state (2026-07-05)

**Built:** `app/frontend/src/components/trust/TrustUI.js` (`EventStatusBadge`,
`ConfidenceBadge` band-only, `CorroborationCount` counted/supporting, `ReporterChip`
with a "🔏 signed" pill), rendered on `EventsFeed` and `EventDetail`; serializers
suppress `user_id` and convert confidence to a band. **Gaps:** the `TrustBlock`
composite is defined but never rendered; the map surface shows only a status color +
raw counted number (no chips/band); the "🔏 signed" badge is a **passive server flag**
with no reader-side verification (ADR-0009) and today is always false (no signing
client).
