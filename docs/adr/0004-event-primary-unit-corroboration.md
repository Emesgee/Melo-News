# 0004. The Event is the primary reader unit; corroboration counts distinct identities

- **Status:** Accepted
- **Date:** 2026-07-05
- **Deciders:** Project owner (design interviews)
- **Relates to:** ADR-0001, ADR-0003, ADR-0005

## Context

A single eyewitness report is weak evidence. What makes citizen journalism credible
is *independent corroboration* — several unconnected people reporting the same
incident. The reader-facing unit therefore should be the **incident**, not the raw
report, and the trust signal should be how many *independent* people attest to it.

The hard part is Sybil resistance: keys are free (ADR-0003), so "5 reports agree"
means nothing if one actor minted 5 keys. We cannot, at MVP, detect that several keys
are one human — so counting must not be the thing that confers trust.

## Decision

- **Every report belongs to exactly one Event.** A new report auto-creates a
  singleton Event; clustering (geo + time, degrading to city + time when a precise
  pin is withheld for safety) grows an Event by adding members. Feed and map are
  feeds of **Events**.
- **Corroboration = `COUNT(DISTINCT user_id)`** over *VERIFIED* members with a
  non-null user_id. Anonymous (user_id NULL) members count **zero** toward the
  threshold and are shown separately as "supporting" context.
- **Sybil backstop — status, not count, confers trust.** An Event auto-promotes to
  `CORROBORATED` only if it meets the count threshold **and** has at least one
  **rung-2+** member. A flood of fresh rung-1 keys raises the count but the status
  stays `DEVELOPING`. Reader display must therefore surface corroborators' *standing*,
  never a raw count as if it were trust.
- Event status (`DEVELOPING`/`CORROBORATED`/`DISPUTED`/`CLOSED`) is a derived pure
  function of members + verifications + a sticky moderator override.

## Consequences

- The count alone is never a trust claim; a Sybil flood must not *look* corroborated.
- Reputation (rung) becomes load-bearing — see ADR-0005.
- The moderation queue needs dedup signals (identical text, tight timing, co-located
  pins) so the human gate on the count is meaningful.

## Code state (2026-07-05)

**Built:** Event model + clustering + singleton fallback (`app/events/service.py`);
`corroboration_count` = distinct non-anonymous VERIFIED identities; `_derive_status`
enforces the rung-2+ backstop; serializers split counted vs supporting. **Gaps:**
(1) `reports_count`/`corroborated_count` on `User` are **never incremented**, so the
reporter track record is always 0/0; (2) `DISPUTED` is unreachable organically — no
dispute mechanism exists, only a manual `status_override`, and the events routes are
read-only (no close/override endpoints wired).
