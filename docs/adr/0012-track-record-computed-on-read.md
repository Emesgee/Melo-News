# 0012. Reporter track record is computed on read; the cohort is hand-vouched for the drill

- **Status:** Accepted
- **Date:** 2026-07-05
- **Deciders:** Project owner + grill session, 2026-07-05
- **Relates to:** ADR-0004, ADR-0005, ADR-0006, ADR-0010

## Context

The reporter chip (ADR-0006) is meant to show a *track record*: "12 reports ·
5 corroborated." The columns exist (`User.reports_count`,
`User.corroborated_count`) but **nothing ever writes them**, so every chip
renders `0 / 0` today. The 2026-07-05 audit flagged this as the reason the trust
display shows a wall of zeros, and ADR-0010 made wiring it the *first* task of
the T4P sandbox drill (milestone (a)) — the drill is a comprehension test of the
trust display, and a display that always says zero tests nothing.

Two sub-decisions were open:

1. **Where the two numbers come from** — a stored counter maintained on writes,
   or a value derived from current rows at read time.
2. **Whether reporters climb the rung ladder automatically** as they accrue a
   record, or are placed by hand for the drill (the ADR-0005 auto-climb gap).

### Definitions (agreed)

- **`reports_count`** = the reporter's **published** reports only
  (`verification_status == 'VERIFIED'`). Counting PENDING/REJECTED submissions
  would let unvetted or rejected spam inflate a public trust number.
- **`corroborated_count`** = the reporter's **VERIFIED reports** whose Event is
  live-status `CORROBORATED`. A lone reporter with a singleton event scores 0 —
  corroboration means *others independently backed the same incident*.
  **Refined 2026-07-06:** originally this counted *distinct corroborated events*;
  it now counts *reports* so the chip's "X of Y **reports** corroborated" ratio
  compares like-with-like. The old event-based numerator produced a misleading
  "1 of 2" when a reporter filed twice into one corroborated event (both reports
  corroborated, but the event counted once). Now always `<= reports_count`.

## Decision

**1. Compute both numbers on read, from current state — do not maintain stored
counters.**

`serialize_reporter` computes the two counts with direct queries at chip-build
time, mirroring how `events/service.py:recompute_event` derives an Event's
corroboration fresh rather than tallying it. Consequences:

- **Correct by construction, cannot drift.** `corroborated_count` is *volatile*:
  an Event can *leave* CORROBORATED when a member is rejected, a dispute is
  filed, or it is closed. A stored counter would need a correct decrement on
  every such reversal path (and `recompute_event` recomputes status from scratch,
  so it does not even know the prior status to diff). Deriving on read has no
  reversal paths to forget — the next render already reflects the truth.
- The `User.reports_count` / `User.corroborated_count` **columns are left in
  place but unused** by the read path. They may later become a refreshed cache
  *if* read cost ever justifies it — a pure optimization, not a correctness
  dependency. No migration.
- **Read cost** is two small indexed counts per chip. At pilot scale (dozens of
  reporters, hundreds of reports) this is invisible. A feed renders one chip per
  report, so the naïve form is N+1; if that ever matters the fix is a single
  batched aggregate keyed by `user_id`, still computed-on-read. If such a cap or
  batching is added, `log`/comment it — a silent cap reads as "counted
  everything" when it didn't.

**2. No automatic rung-climbing in this task; hand-vouch the cohort.**

Auto-promotion (bump a reporter to rung 2 after N corroborated reports) is a
separate design with real questions — thresholds, demotion, Sybil-gaming — noted
as the ADR-0005 gap. The drill has a small, known tester cohort, so we place them
at rung 2 directly using the **existing steward tool**
`POST /moderation/users/<id>/rung` (`@steward_required`,
`moderation/routes.py:set_rung`), which already re-runs `recompute_event` on the
vouched user's events. That is enough to exercise the whole trust display
(auto-publish → corroboration → track record) without building or trusting an
auto-climb algorithm the drill does not need. Auto-climbing stays deferred with
the rest of the scaling machinery.

## Consequences

- The chip stops lying: a fresh reporter shows `0 / 0` honestly; a corroborated
  one shows real numbers that track live Event status without any counter
  bookkeeping.
- The only production code that changes is `story/serializers.py`. No write-path
  hooks in `apply_rung_gate`, `recompute_event`, or the moderator actions.
- The trust ladder remains **static** for the drill (placed by steward vouch);
  ADR-0005's auto-climb remains unbuilt and out of scope here.
- Scope of this task is exactly: make the two track-record numbers real. Nothing
  else (no dispute mechanism, no rung automation).

## Code state (2026-07-05)

Being implemented in this change. Before: `serialize_reporter`
(`story/serializers.py:40`) read the never-written `User` columns → always
`0 / 0`. After: it derives `reports_count` (VERIFIED reports by the user) and
`corroborated_count` (distinct CORROBORATED events with a VERIFIED report by the
user, honoring `status_override`) at read time. The steward rung-vouch endpoint
(`moderation/routes.py:205`) already exists and already recomputes affected
events — no change needed for the hand-vouch path.
