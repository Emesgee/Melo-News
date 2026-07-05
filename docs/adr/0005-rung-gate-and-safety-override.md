# 0005. Rung-based publication gate with a safety override

- **Status:** Accepted
- **Date:** 2026-07-05
- **Deciders:** Project owner (design interviews)
- **Relates to:** ADR-0004

## Context

Moderation cannot scale if every report is pre-moderated, but auto-publishing
everything destroys trust and safety. We need to separate *whether/when* a report is
published from *what order* moderators look at things.

A 4-rung trust ladder drives this: (0) anonymous, (1) new pseudonym — treated the same
as anonymous so a fresh key earns nothing, (2) pseudonym with corroborated history —
lighter review, (3) moderator-vouched/known org — fast-track.

## Decision

- **Publication gate by rung.** Rung 0–1 → mandatory pre-moderation (`PENDING`,
  hidden). Rung 2–3 → auto-publish (`VERIFIED`) into a low-priority audit queue. This
  is what lets moderators scale: they audit trusted reporters instead of gating them.
- **Safety override forces pre-moderation** regardless of rung when a report is HIGH
  severity, marked `is_sensitive`, or is the first media on a brand-new Event. Safety
  beats throughput.
- **Attention order is a priority score**, not FIFO: severity + sensitivity + has-media
  + low-rung boost + would-tip-to-CORROBORATED boost + anti-starvation aging.
- Rungs are **reputation, not roles**. Moderator/steward powers are a separate `role`
  axis.

## Consequences

- A closed pilot cohort is hand-vouched to rung 2–3 so their reports flow while
  still being audited; untrusted/new reporters are safely pre-moderated.
- Self-reported severity is gameable but **fails safe** — inflation just means more
  review.
- The ladder only works if reporters can actually *climb* it. If rung is static,
  everyone is stuck at pre-moderation forever unless hand-vouched (see Code state).

## Code state (2026-07-05)

**Built:** `app/moderation/gate.py` (`apply_rung_gate`, `safety_override`,
`compute_priority`), invoked on all ingest paths; `verification_status`
(`PENDING`/`VERIFIED`/`REJECTED`) is the published-vs-pending field; public feeds
filter to VERIFIED; moderator queue + verify/reject + role/rung setters exist. **Gap:**
**automatic rung climbing is not implemented** — `trust_rung` is only set to 1 at
registration or changed by a manual moderator/steward action. The "earn your way up
through corroborated history" half of the ladder is designed but unbuilt.
