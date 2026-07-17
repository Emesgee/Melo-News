# Design note — limits of the fake-independence detector

- **Date:** 2026-07-17
- **Relates to:** ADR-0006, ADR-0009, ADR-0019, ADR-0020 (Phase 1), UC3/UC8
- **Status:** Known-limits note (not a decision). Prompted by an external model
  (Thaura) independently naming this hole when asked about competitors — worth a
  durable record so we don't mistake "byte-dedup shipped" for "independence solved."

## What the detector actually does today

`app/events/service.py :: _independent_origins()` is a **union-find over people**.
Nodes are distinct `user_id`s among VERIFIED members. Two identities are merged into
one origin **only when they share a byte-identical `media_sha256`.** The count of
connected components is `independent_source_count`.

A second, separate gate protects **status**: `_derive_status()` promotes an Event to
CORROBORATED only when `independent_source_count >= threshold` **AND** at least one
member is a **rung-2+** identity (`_has_established_member`). A pure fresh-key flood
raises the *count* but cannot self-promote — the Sybil backstop is on status, not count.

## What it catches

Exactly one thing: **the literal reshare** — the same file (identical bytes) posted
under many pseudonyms collapses to a single origin. Good against lazy amplification
bots reposting one viral clip. This is real and worth having.

## What it misses (the hole Thaura named)

1. **Re-encoded / cropped / recompressed copies of the same clip.** Different bytes →
   different SHA-256 → counted as independent. A perceptual/near-duplicate hash would
   catch this, but it is **deferred, not half-built**: the server never sees media
   bytes (ADR-0009), so it needs an on-device perceptual hash in the signed envelope
   (a client-contract change, ADR-0008).
2. **Text-only reports.** `media_sha256` is NULL → the union-find `continue`s past
   them → every text-only pseudonym is a free independent origin. This is the
   **cheapest bypass** and requires no media at all.
3. **A coordinated network each posting *distinct* media of a *staged* scene.**
   Genuinely different bytes by construction → indistinguishable from real
   corroboration by **any** media-fingerprint scheme, perceptual or not.

Point 3 is the epistemic ceiling and the important one: **no media hash can
distinguish "10 independent witnesses of a real event" from "10 coordinated actors
each filming a staged one."** Both produce distinct media. Beyond byte/perceptual
dedup, independence stops being a media problem and becomes a **network/behavioral**
problem (device/IP/timing/social-graph correlation — what X/Meta throw ML fleets at,
and which is in tension with our pseudonymity promise, ADR-0003) or a **human-OSINT**
problem (geolocation, chronolocation — Bellingcat's actual craft). This is precisely
why ADR-0019 called the differentiator "softer" and "OSINT-adjacent." It is a wall,
not a backlog item.

## What still contains the attack (partially)

- The **rung-2+ gate** means a distinct-media/text-only ring of *fresh* keys inflates
  the reader-visible **count** but cannot reach the CORROBORATED **badge** without an
  established identity. Getting a rung-2 anchor is a real barrier (age an identity
  through legitimate corroborations, coerce/compromise one, or social-engineer a
  steward vouch) — breachable by a patient adversary, but not free.
- So the exposure splits: the **count** is gameable cheaply; the **badge** needs a
  rung-2 anchor. A false CORROBORATED is the catastrophic case (manufactured atrocity
  / atrocity-denial), so the rung gate is doing the load-bearing work, not the media
  dedup.

## Concrete, cheap fixes available now (UI/logic, no infra)

- **[bug] `TrustBlock` bypasses the detector on the map popup.** `components/trust/
  TrustUI.js` `TrustBlock` renders `<CorroborationCount counted={ev.corroboration_count}
  status=... />` — it passes the **raw account count** and never passes `independent`
  or `supporting`, so `ind` falls back to `counted` and `reshared` is 0. The popup
  therefore shows the *un-collapsed* number and never surfaces a detected reshare,
  even though the engine computed it. Pass `independent` + `supporting` here.
- **Don't wear the green ✓ before CORROBORATED.** `CorroborationCount` shows
  `✓ N independent sources` in affirmative green whenever `ind > 0`, gated to neutral
  only on DISPUTED. On a DEVELOPING event a coordinated ring can thus display a green
  "✓ 3 independent sources" — an endorsement the event has not earned. Gate the
  affirmative styling on `status === 'CORROBORATED'`; neutral otherwise (mirror the
  DISPUTED treatment).
- **Tighten the copy — this is the highest-leverage, near-zero-cost fix.** The label
  "independent **sources**" overclaims: the number is really "distinct **accounts**,
  minus exact-byte reshares." Calling it "sources" invites exactly the over-trust the
  attack exploits. Prefer "independent accounts (deduplicated)" or similar; reserve
  "independent witnesses/sources" for when there is stronger evidence than
  account-distinctness.
- **Consider a media floor for text-only.** Optionally require ≥1 media-bearing source
  before independence counts toward the threshold, or weight text-only as
  *supporting*. (Design decision; tie to UC8.)
- **Make moderator skepticism scale with count.** The advisory `coordination_flags`
  (text near-duplication, synchronized submission) already exist in
  `app/events/independence.py` — surface them prominently to the moderator on
  high-independent-count Events, which is where a coordinated ring would show up.

## Rejected generic heuristics & constraint violations

General-purpose trust-and-safety advice (from tools, consultants, or LLMs) tends to
recommend mainstream platform anti-abuse patterns that are actively **wrong** for a
citizen-journalism-under-repression tool. Recorded here so they are not re-proposed
every few months.

- **Account-age / post-count filters** ("ignore accounts <30 days old or with <10
  prior posts"). **Rejected:** the most important witness in a conflict zone is often
  a *first-time* poster; suppressing new accounts silences exactly the person the
  product exists for. The **rung ladder** is the humane substitute — a fresh key still
  contributes to the count and can be corroborated *by* an established identity; it
  just cannot self-promote an Event to CORROBORATED.
- **Cross-platform identity weighting** (link/downweight the same handle across
  X/Telegram/Instagram). **Rejected twice over:** it requires **de-anonymizing**
  pseudonymous reporters (violates ADR-0003 and reporter safety), and it is backwards —
  a consistent persistent identity is a *credibility* signal, not a bot tell.
- **Auto-flagging temporal bursts as "suspicious coordination."** **Rejected as a
  count-affecting signal:** a tight burst is also the signature of a *real*
  mass-casualty event — flagging it would fire during the exact moments the tool
  matters most. Kept **advisory-only** (already implemented that way in
  `independence.py`); it must never reduce the corroboration count.
- **Server-side media processing** (server hashes/thumbnails the raw bytes to catch
  crops). **Rejected:** it turns the server into a **honeypot of sensitive footage**,
  violating ADR-0009. All media hashing is **on-device, in the signed envelope**
  (Lane B), or not at all. Note this leaves the crop/recompress vector open on Lane A
  public posts, which have no on-device hash — a scope limit, not a thing to fix by
  moving processing server-side.

**Common thread:** privacy-first / pseudonymous / server-blind are load-bearing
*ethical* constraints, not obstacles to engineer around. A mitigation that improves
detection by breaking one of them is a net loss — it trades the property that
distinguishes Melo from Big-Tech surveillance for a marginal, still-bypassable gain.

## Bottom line

Byte-identical dedup is the floor, not the solution. Keep the **automated claim
modest and the copy honest** (accounts deduplicated, not witnesses verified), lean on
the **rung gate** for the catastrophic CORROBORATED case, keep the moderator in the
loop for high-count Events, and treat perceptual hashing + network/behavioral Sybil
analysis as the (expensive, partly deferred, partly ceiling-bound) next tiers — not
as things the current detector already does.
