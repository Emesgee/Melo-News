# 0020. Strategy sequencing: one engine, three shapes, the drill is the branch point

- **Status:** Proposed
- **Date:** 2026-07-06
- **Deciders:** Project owner + benchmark session, 2026-07-06
- **Relates to:** ADR-0001, ADR-0004, ADR-0006, ADR-0010, ADR-0011, ADR-0013, ADR-0019
- **Builds on:** ADR-0019 (purpose = reader-side trust layer). This ADR sequences *how* to get
  there without betting the whole project on the one unproven hypothesis.

## Context

ADR-0019 set Melo's purpose as a reader-side trust layer over already-public content, gated on a
single **non-technical** existential question (UC4): does a "corroborated · N independent sources"
signal actually move a lay reader's belief, or backfire as bias? That is a real risk to stake the
project on. The 2026-07-06 benchmark (recorded in the `benchmark-use-cases` memory, UC1–UC9)
surfaced **three viable product shapes, and the key finding is that they are not competing choices —
they share one engine and one data model:**

1. **Reader-side trust layer** (ADR-0019; the consumer bet) — corroboration → lay-legible basis of
   trust. Upside large, demand unproven (UC4).
2. **Debunk / independence-integrity engine** (UC8) — the *same* corroboration engine run in reverse
   to flag recycled/miscaptioned media and *fake independence* (astroturf). Skeptic-friendly (defuses
   UC4's backfire), larger market, but a crowded field and a mirror existential risk (false-debunk =
   atrocity denial).
3. **Capture-before-deletion archive** (UC9) — the corroboration graph, byte-preserved, as an enduring
   accountability asset feeding Mnemonic/eyeWitness/courts. A hedge that has value *even if UC4 fails*,
   plus an urgent live need (platforms are deleting Gaza evidence in real time). It also **rehabilitates
   the signing stack ADR-0019 demoted** — court-grade provenance is the archive's *legal tier*.

All three consume the same primitives: an Event, a set of sources with provenance tiers, and the graph
of independent-source relationships between them. Committing now to any *one* shape — before the drill
answers UC4 — would be a guess. Forking into three products would fracture a solo project.

## Decision

**Build one engine and one archive-grade data model first; treat the scripted drill as the branch
point that decides which shape leads; keep all three reachable from the same core.** Concretely, a
four-phase sequence with an explicit branch:

**Phase 0 — the drill, re-scoped to falsify the demand hypothesis (now).**
Run the scripted T4P corroboration drill on the existing Lane-B signing path (owner's phone, dummy
cohort — unchanged from ADR-0016). What changes is the *measured outcome*: the drill must be able to
**falsify** UC4, not just demonstrate comprehension to a friendly audience. Add a belief-change exit
criterion tested on a *skeptical, non-aligned, non-technical* reader (see [[t4p-pilot-test-plan]]).
This phase gates everything after it.

**Phase 1 — the no-regret core (build regardless of the drill result).**
The **archive-grade corroboration data model**: an Event → sources (with provenance tier: verified /
public) → an explicit **corroboration graph** (which sources independently corroborate which event),
designed from day one to be **durable, exportable, provenance-preserving, and byte-capturing (not
link-storing)**. This single model is the substrate all three shapes need, so it is built before the
branch and is wasted under no outcome. The **(B) fake-independence detector** (UC8's only novel-and-
reusable piece — distinct-identity machinery run to detect *non*-independence) is prototyped here too,
because it serves the consumer (debunk signal), the archive (integrity metadata), and Sybil-hardening
(UC3) at once.

**Phase 2 — branch on the Phase-0 result.**
- **If belief-change is strong** → lead with the **reader-side trust layer** (ADR-0019): build Lane A
  ingest (public post → geolocate + timestamp + content-match → "public source") and the graded reader
  feed. The consumer bet is on.
- **If belief-change is weak or backfires** → shift emphasis to the shapes that do **not** depend on
  lay-reader belief: the **archive** (UC9 — capture-before-deletion, feed Mnemonic/eyeWitness/courts)
  and/or the **debunk engine** (UC8 — skeptic-facing independence-scoring). The core built in Phase 1
  already supports both; only the surface changes.

**Phase 3 — harden for the chosen surface's real risks (gates, not afterthoughts).**
- **Any real Lane-B reporter** → the ADR-0011 security-hardening gate (real at-rest encryption,
  Keystore-backed secrets, per-signature auth) remains hard-blocking, unchanged.
- **Any public Lane-A launch** → moderation-at-scale (UC6) and takedown/legal/jurisdiction (UC7) must
  be scoped first; ingesting public content means ingesting misinformation and graphic material at
  volume, and a byte-preserving archive must survive takedown pressure.

**Governing principles (apply to every phase):**
- **One engine, one data model** — never fork into three codebases; build the shared corroboration
  graph once (Phase 1).
- **No-regret before branch** — build only what serves all three shapes until the drill decides.
- **The drill decides, not a guess-now** — the UC4 result picks the leading surface.
- **Keep the signing stack dormant, not deleted** — demoted for the consumer signal (ADR-0019), it is
  the archive's legal tier (UC9).
- **One non-binary spectrum** — corroboration and debunking are two directions of the same
  basis-of-trust axis (ADR-0006), never a binary "verified"/"fake" stamp.
- **Feeder, not rival** — position upstream of Mnemonic/eyeWitness/Ushahidi/courts, not as a competitor.

**Rejected:** committing to one of the three shapes before the drill falsifies (or fails to falsify)
UC4; forking the project into three parallel products; deleting the signing/capture stack (it is the
archive's admissibility tier); and building Lane A ingest *before* the belief hypothesis is tested
(the most expensive way to discover the thesis is wrong).

## Consequences

- **The project stops being a single all-or-nothing bet on UC4.** Phase 1 has value under every branch,
  so a failed belief-hypothesis pivots the *surface* (to archive/debunk) rather than killing the work.
- **Build order is now explicit and cheap-first:** drill → shared data model + independence detector →
  branch → surface-specific hardening. The most expensive, most-uncertain work (Lane A ingest, public
  moderation, byte-preservation infra) is deferred behind the branch.
- **The data model carries an up-front tax:** it must be archive-grade (durable, exportable,
  byte-capturing, provenance-preserving) from day one even though the archive *product* may ship late —
  because retrofitting durability/provenance onto a consumer-shaped store is far more expensive than
  designing for it once. This is a deliberate cost accepted in Phase 1.
- **Two hard gates stay in force and are named per-surface:** ADR-0011 before any real Lane-B reporter;
  UC6+UC7 scoping before any public Lane-A launch. Neither is optional for its surface.
- **The signing stack's status is clarified, not reversed:** dormant for the consumer signal, live as
  the archive's legal tier — so no code is thrown away, and the ADR-0013 investment is preserved with a
  specific bounded purpose.
- **Byte-preservation reframes hosting/jurisdiction as central (not incidental):** an archive that must
  survive platform deletion and state takedown makes ADR-0017's storage/jurisdiction choices
  load-bearing, and makes UC7 a first-class design input rather than a footnote.
- **Solo-feasible:** by refusing the three-product fork, the sequence keeps one engine one person can
  maintain, and lets partnerships (Mnemonic/eyeWitness) carry the parts Melo should not rebuild.

## Code state (updated 2026-07-06)

**Phase 0 unchanged; Phase 1 no-regret core substantially BUILT (four increments); Phase 2/3 not
started.** The starting point remains the Lane-B signing/capture stack (ADR-0013/0008/0014/0015, proven
on-device) plus the reader feed (`EventsFeed`, `EventDetail`, `TrustUI`) over an Event/corroboration
model with the rung-2 Sybil backstop.

**Phase 1 — built and tested (135 tests green), on branch `citizen-journalism-trust-model`:**

- **Fake-independence detector** (commit `92d8805`). `FileUpload.media_sha256` lifted out of the
  opaque `signed_message` blob into a first-class indexed column; `Event.independent_source_count`
  added. `events.service.recompute_event` collapses byte-identical media (reshares/astroturf) to a
  single origin, and CORROBORATED promotion now gates on independent origins, not raw distinct keys —
  strictly more conservative, so every prior corroboration/drill test still passes. Closes the UC3/UC8
  "distinct keys treated as distinct people" hole. Reader API exposes `counted` vs `independent`.
- **Explicit corroboration graph + archive-grade export** (commit `3a202dd`). `app/events/archive.py`
  `build_event_graph()` emits a deterministic, privacy-preserving (never a raw `user_id`), hashable
  (`graph_sha256`) provenance record — per source: pseudonym, provenance tier (verified/unverified;
  `public` reserved for Lane A), media fingerprint, independence role, plus reshare clusters. Served at
  `GET /api/events/<id>/graph`.
- **Durable, content-addressed snapshots** (commit `f263d14`). New append-only `EventGraphSnapshot`
  table; `recompute_event` captures a snapshot the moment an Event first enters an archival status
  (CORROBORATED/DISPUTED/CLOSED), deduped by hash — capture-before-deletion (UC9). History at
  `GET /api/events/<id>/snapshots[/<sid>]`.
- **Advisory coordination signals** (commit `2de8b14`). `app/events/independence.py` flags text
  near-duplication and synchronized submission in the graph as `coordination_flags` — **advisory
  only**, never reducing the count, because for text/timing the pattern also marks genuine corroboration
  (an honesty-guard test proves similar-text same-time reporters still reach CORROBORATED).

**Phase 1 — still open (deliberate stops):** (1) **byte-capturing, not link-storing** — snapshots
preserve the corroboration state + hashes, but media is still a storage key/presigned URL; full UC9
capture needs the bytes, which is infra-heavy and coupled to the UC7 jurisdiction/liability decision;
(2) **perceptual (near-duplicate) media hashing** — deferred not half-built, since the server never
sees media bytes (ADR-0009); needs an on-device perceptual hash in the signed envelope (a
client-contract change); (3) **provenance-tier `verified/public` as a stored field** — waits for Lane A.

**Not started:** Phase 2 (Lane A public-post ingest + graded reader feed, gated on the drill's
belief-change result) and Phase 3 (per-surface hardening: ADR-0011 for real Lane-B reporters; UC6+UC7
scoping before any public Lane-A launch). **For the drill, still nothing new is required** — Phase 0
runs on the existing Lane-B path; the Phase 1 core above is the no-regret foundation for whichever
shape the drill selects.
