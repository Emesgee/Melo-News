# 0019. Melo's purpose is a reader-side trust layer over public conflict content; the capture/signing stack is demoted to an optional provenance tier

- **Status:** Proposed
- **Date:** 2026-07-06
- **Deciders:** Project owner + benchmark session, 2026-07-06
- **Relates to:** ADR-0001, ADR-0003, ADR-0004, ADR-0006, ADR-0007, ADR-0010, ADR-0011, ADR-0013
- **Sharpens:** ADR-0001 (north star: reader trust) — this ADR names *where in the pipeline* that north star is the only defensible one, and what follows.

## Context

An exhaustive benchmark (2026-07-06) walked Melo, stage by stage, against the
real competitive field: **Tella**, **eyeWitness to Atrocities**, **Starling/Hala**,
**ProofMode**, **Numbers/Capture**, **Truepic/C2PA**, **Ushahidi**, **Meedan Check**,
**Briar/Bridgefy**, and — decisively — the platforms Gazans actually use for
witnessing: **Telegram, X, Instagram, WhatsApp**. Recorded in full in the
`benchmark-use-cases` memory (UC1–UC5, UC-W, UC-L).

Lay Melo's eight-stage lifecycle (1 capture · 2 strip metadata · 3 at-rest/seizure ·
4 transmit under blackout · 5 prove media unaltered · 6 establish it happened /
corroboration · 7 publish with reader-legible trust · 8 downstream/legal) against
that field and a single pattern emerges: **every stage is already owned by a
better-resourced tool, except stages 6→7.**

- Capture, metadata-strip, blackout transport, at-rest security, and single-item
  provenance are solved — by Tella/eyeWitness (security, chain-of-custody) and by
  ProofMode/C2PA/Truepic (a provenance *standard* Melo's non-standard signing does
  not beat). Melo's own stage 3 (at-rest) is **stubbed** (ADR-0011) — its *worst*
  cell is one incumbents built for.
- Distribution and audience are owned outright by the social platforms. A Gazan
  documenting a strike wants millions to see it tonight, not a private vault or a
  legal file. **The real competitor for the reporter's attention is Telegram/X,
  not Tella** — which also breaks the "fold into Tella" intake, because Gazans are
  not in Tella.
- **Stages 6→7 — corroboration across independent pseudonymous sources, rendered
  as a non-binary "basis of trust" a lay reader can read (ADR-0004/0006) — is the
  one cell no competitor occupies.** Tella/eyeWitness make a *single private item*
  trustworthy for an *expert/court*; social platforms give *reach with no trust
  signal*; OSINT desks (Bellingcat, Meedan) do 6→7 *by hand, slowly, for a few
  items, for experts*. Nobody turns *public* conflict content into *corroborated
  events a lay public can trust, at feed speed*.

The consequence is uncomfortable: **most of what the codebase has built — the
on-device signing / Keystore / capture stack (ADR-0003/0008/0013/0014/0015) — is
on the wrong side of the pipeline.** It is careful engineering aimed at the
*reporter* (stages 1–5, already solved elsewhere) when Melo's only unclaimed
territory is *reader-side* (stages 6→7). The investment and the moat point in
opposite directions.

## Decision

**Melo's purpose is the reader-side trust layer for conflict content that is
*already public*: the thing that lets a lay reader abroad know which of tonight's
many posts is corroborated, by how many independent sources, and how much to
believe it. Cryptographic provenance is an *optional top tier* when a report
arrives from a signing client — not the foundation.**

1. **The unit of value is the reader's "should I believe this?" moment, downstream
   of capture.** Melo optimises stages 6→7 and treats 1–5 as *inputs it consumes*,
   not features it must own. This is ADR-0001's north star, located precisely.

2. **Two input lanes feed one Event, at graded trust tiers (extends ADR-0004/0006).**
   - **Lane A — already-public post.** Content posted to Telegram/X/etc. is ingested
     (reporter-pasted link or monitored public channel), geolocated, timestamped, and
     content-matched into an Event as a **"public source"** at the *lower* tier — no
     cryptographic proof, heuristic corroboration. This lane carries **zero new
     reporter behaviour and no onboarding**, which is how Melo reaches an audience it
     cannot otherwise recruit.
   - **Lane B — signed client report.** The existing on-device signing path
     (ADR-0013/0008) becomes the **"verified source"** *premium* tier: provably
     unaltered, cryptographically distinct identity, track record. It is retained as
     a differentiated tier, **not deleted** — but it is no longer the product's
     centre of gravity.

   A reader sees "N sources: X verified, Y public" — honest about which is which, the
   feed degrading gracefully between tiers (ADR-0006's non-binary philosophy pointed
   at the right target).

3. **The competitor set and partnership posture change accordingly.** Melo sits
   *over public social content* and alongside the OSINT/verification world (Meedan
   Check, Bellingcat), not over private vaults. The earlier "fold into Tella +
   Ushahidi" framing is corrected: Tella is a *provenance supplier for Lane B*, not
   the intake for the mass case.

4. **The pilot tests the demand question first, not the code.** The single
   existential unknown is **not** "can we build it?" but "does a *corroborated · N
   independent sources* signal actually move a lay reader's belief versus a raw,
   fast, visceral social post — or does a predisposed reader read *corroborated* as
   bias?" (UC4). The T4P drill's comprehension gate ([[t4p-pilot-test-plan]]) is
   re-scoped to measure **belief-change in a skeptical, non-aligned lay reader**,
   before further capture-side engineering.

**Rejected:** continuing to build Melo as a capture/signing app competing on stages
1–5 (redundant with better-funded, field-proven tools, and losing on distribution to
the social platforms); and deleting the signing stack outright (it is the credible
*top tier* for Lane B and the seed of the distinct-identity guarantee — demote, do
not discard).

## Consequences

- **Product centre of gravity moves from the Android capture client to the reader
  feed + moderation tools.** That is *not* where the codebase's investment currently
  sits, so this ADR implies a real re-prioritisation, not a tweak.
- **Adoption/cold-start (UC2) eases:** Lane A inherits the social platforms' content
  firehose instead of recruiting a reporter population from scratch. Melo's value no
  longer requires reporter density it cannot manufacture.
- **The differentiator becomes reachable but softer.** Heuristic corroboration over
  public posts is *OSINT*, a space where Bellingcat/Meedan are strong; Melo's claim
  is **lay-legible + fast + automated + graded**, not cryptographic. Lane B keeps a
  hard-proof tier for when it exists.
- **A large new failure surface appears: ingesting public content means ingesting
  misinformation and graphic material at scale.** Moderation-at-scale (UC6, still
  unrun) and takedown/legal exposure (UC7) move from side-questions to core risks.
  The moderator remains the linchpin and the likeliest thing to break under volume.
- **The at-rest/coercion security debt (ADR-0011) is de-risked for the mass case**
  (Lane A reporters never install a Melo capture client, so there is no hijackable
  on-device identity or cleartext store to seize) — but remains a hard gate for any
  Lane B reporter (ADR-0011 unchanged for the premium tier).
- **The demand hypothesis (UC4) is now the whole company.** If a lay reader's belief
  does not move, no amount of corroboration engineering saves the product; the pilot
  must be able to *falsify* the thesis, not just demonstrate comprehension to a
  friendly audience.
- **ADR-0007 (web is a login-required unsigned lane) generalises:** the web/reader
  surface is the primary product, not a secondary one to the Android app.

## Code state (2026-07-06)

**Not built — Proposed. The codebase today is the *opposite* shape of this decision:**
its weight is the reporter-side signing/capture stack (ADR-0003/0008/0013/0014/0015,
built and working on real hardware), while the reader feed exists (`EventsFeed`,
`EventDetail`, `TrustUI`, the Event/corroboration model) but is thin relative to where
this ADR puts the centre of gravity. **No Lane A ingest exists at all** — there is no
path to pull a public Telegram/X post into an Event, no geolocation/content-matching,
and no "public vs verified" source-tier distinction in the trust display. Lane B (the
signing path) is the mature part and is retained as the premium tier.

**For the drill, nothing changes yet:** the scripted T4P corroboration exercise still
runs on Lane B (owner's phone, dummy cohort). What changes is the *pilot's measured
outcome* — re-scoped to the UC4 belief-change question — and the *build order after
the drill*, which now leads with Lane A ingest + the graded reader feed, not more
capture hardening. This ADR records the direction; the Lane A build is deferred until
the belief hypothesis survives the drill.
