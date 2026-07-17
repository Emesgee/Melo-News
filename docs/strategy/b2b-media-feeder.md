# Strategy note — the B2B "corroboration feeder" as a UC4 hedge

- **Date:** 2026-07-17
- **Relates to:** ADR-0019 (purpose), ADR-0020 (one engine, three shapes; "feeder,
  not rival"), UC4 (the belief-change hypothesis), UC-W (winning layer), UC9 (archive)
- **Status:** Exploratory. **Not** a decision and **not** a pre-drill pivot. Records a
  named destination for the Phase-2 "belief weak/backfires" branch.

## The idea

Sell Melo's corroborated-event output to **organisations** — newsrooms, OSINT desks,
monitoring/compliance/risk teams — as an **API + tamper-evident archive**, rather than
(only) rendering a trust badge to lay readers. The buyer pulls "here is an incident,
here are its N deduplicated independent sources, here is the corroboration graph and a
hash-chained snapshot" and folds it into their own editorial/analyst process.

The angle surfaced when an external model (Thaura) was asked about competitors; it is
worth banking because it is the one strategically useful, non-sycophantic idea in that
thread and it lines up with an ADR principle we already hold.

## Why it matters: it de-risks the one existential unknown

ADR-0019's whole bet rests on **UC4** — *does a "corroborated · N independent sources"
signal actually move a lay reader's belief, or backfire as bias?* That is unproven and
could fail. The B2B feeder **removes the dependency on lay-reader belief**: an editor or
analyst does not need their belief "moved" — they already want speed, deduplication, and
an audit trail they don't want to build themselves. So this shape has value **even in the
Phase-2 branch where belief-change is weak or backfires**, exactly like the archive (UC9).
It is a hedge, not a competing bet.

## Why it's nearly free to reach from where we are

The Phase-1 no-regret core **is** most of the B2B product already:

- `GET /api/events/<id>/graph` — a deterministic, **privacy-preserving** (never a raw
  `user_id`), **hashable** corroboration graph. This is the explainability substrate a
  newsroom will demand ("how do you define an independent source? show me the dedup").
- `EventGraphSnapshot` — durable, content-addressed, exportable capture-before-deletion.
  This is the "audit-grade / tamper-evident archive" a compliance or legal buyer wants.
- The independence detector — the dedup the buyer would otherwise have to build.

So the B2B surface is **an API + explainability + packaging**, not a new engine. The one
cheap pre-commitment — keeping the graph/snapshot exports clean and provenance-preserving
— was already made in Phase 1. No regret.

## The honest caveats (why this is a hedge, not a saviour)

- **It does not escape the Lane A build.** A feeder has nothing to sell until there is
  *volume* of corroborated events, which needs Lane A public-post ingest (Phase 2, still
  unbuilt). B2B changes *who pays*, not *whether the hard ingest work happens*.
- **A newsroom probes the independence claim far harder than a lay reader.** The
  [independence-detector limits](../design/independence-detector-limits.md) are a *direct
  dependency* of this pitch — an editor will find the text-only / distinct-media-of-a-
  staged-scene hole immediately. The B2B story must lead with **honest scope** ("dedup +
  corroboration signal + audit trail; not a witness-verification oracle") or it dies on
  first contact with a real verification desk.
- **The adjacent field is not empty here.** Storyful, Dataminr, and Meedan already sell
  to newsrooms. Melo's wedge is the specific primitive (automated cross-source
  corroboration with reshare-collapse + a hash-chained event archive), not "verification
  for media," which is taken.
- **B2B sales cycles are slow and solo-founder-hostile.** This is a partnership /
  design-partner motion (one newsroom or one OSINT NGO), not a self-serve launch.

## Positioning

**Feeder, not rival** (ADR-0020): sit *upstream* of the newsroom/OSINT/court workflow —
a corroboration API + tamper-evident event archive that *feeds* Bellingcat/Meedan/
Mnemonic/eyeWitness/editors, never claims to replace their judgement. This is the same
"feeder, not rival" line ADR-0020 already draws for the archive shape; the B2B feeder is
that principle applied to the live corroboration stream instead of the historical archive.

## Recommendation

1. **Do not pivot now.** It is not a pre-drill move; Phase 0 (the belief drill) still
   gates. Building B2B before the drill would be guessing, same as building Lane A early.
2. **Adopt it as the named Phase-2 "weak belief" surface, alongside the archive.** If the
   drill shows lay belief doesn't move, the branch is not "kill the project" — it is
   "point the same Phase-1 engine at buyers who don't need their belief moved" (feeder +
   archive). Write this into the Phase-2 branch options.
3. **Keep the two cheap pre-commitments:** (a) graph/snapshot exports stay clean and
   provenance-preserving (already true); (b) fix the honesty gaps in the
   [independence limits note](../design/independence-detector-limits.md) — modest,
   accurate copy is a prerequisite for *both* the lay-reader product and the far more
   demanding B2B buyer.
