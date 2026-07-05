# 0001. North star: optimize for reader trust

- **Status:** Accepted
- **Date:** 2026-07-05
- **Deciders:** Project owner (design interviews, 2026-06-02 onward)
- **Relates to:** all subsequent ADRs

## Context

Melo-News is a citizen-journalism platform whose first use case is reporting from
hostile environments. Two things were already strong: reporter *safety* tooling and
report *intake*. The gap was **credibility** — whether the public will believe and
act on a report from an unknown person.

A platform like this can optimize for many things: volume, engagement, breaking-news
speed, feature breadth. Chasing those tends to erode the one property that makes
citizen journalism worth anything: that a reader can reasonably trust what they see.

## Decision

**Reader trust is the north star.** Every design decision is judged first by whether
it helps a reader correctly calibrate how much to believe a report — not by demo
appeal, feature count, or throughput. When a feature manufactures false precision or
presents unverified claims as authoritative, it is a trust *liability* and is cut or
reworked regardless of its demo value.

## Consequences

- Confidence is shown as a coarse band, never a false-precision decimal (ADR-0006).
- Corroboration across independent identities is the primary trust signal (ADR-0004).
- Features that synthesize authoritative-sounding output from unverified reports were
  removed (ADR-0002).
- We accept slower growth and fewer "wow" features in exchange for a credible product.

## Code state (2026-07-05)

Reflected throughout: `app/story/serializers.py` (band conversion, no raw scores,
no `user_id` leak), the Event-first reader surfaces, and the removal of the
AI-intelligence features. The main *unbuilt* piece of the north star is the reporter
track record (`reports_count`/`corroborated_count` are never incremented — see
ADR-0004 Code state), which currently renders as 0/0 to readers.
