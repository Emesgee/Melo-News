# T4P Drill Protocol (Phase 0)

A runnable package for the scripted corroboration drill with Tech-for-Palestine
testers. It exists to answer two questions, in order of importance:

1. **Does the trust signal move a lay reader's belief?** (the existential question,
   UC4 / ADR-0019 / ADR-0020 exit criterion **#6** — the branch point).
2. **Does the machine work and is the display understood?** (exit criteria #1–#5).

> **Re-scope note (ADR-0020).** Earlier drafts of this drill tested only #1–#5
> (the machine + comprehension). The whole product now rests on #6 — belief-change
> — so this protocol adds a **belief-measurement instrument** designed to *falsify*
> the hypothesis, not just confirm it. A friendly, aligned T4P audience will "get
> it" and produce a **false positive** on comprehension; #6 must be run with a
> **skeptical, non-aligned, non-technical** reader and must be able to come back
> negative. A negative #6 is not a failure of the drill — it is the signal to
> branch toward the archive (UC9) / debunk (UC8) surfaces (ADR-0020 Phase 2).

This drill is **NOT** a live conflict-zone pilot. It runs on a fictional,
sandboxed dataset (`Testoria / Sandboxia`, every handle prefixed `drill:`) and
does **not** trip the ADR-0011 real-reporter security gate — no real reporter is
involved.

---

## Part 0 — Setup

The scenario is codified in `app/drill/scenario.py`:

- `provision(db)` — wipe + create the cohort: a sole steward/moderator (rung 3)
  plus one identity per role card at its assigned rung.
- `simulate(db)` — provision **and** play the whole script through the real
  submission + moderation pipeline; returns the end-state summary. Use it as the
  **dry run / self-test / demo** before a live session.
- `role_cards()` — the per-report briefs (account, rung, pin, exact text, media)
  to hand testers in a live session.
- `reset(db)` — delete only `drill:`-prefixed data.

Bootstrap: the facilitator is the **sole steward + moderator** for round one
(explicit, logged genesis). Run against an **isolated database** that holds no
real reports.

**Dry run first:** run `simulate(db)` and confirm the summary matches Part A
below. If it does, the engine is faithful and you can run the live session (or,
for a belief-only test, use the dry-run output as the stimulus source).

---

## Part 1 — The scripted incidents

Seven elements, each forcing one rule. `role_cards()` prints the live briefs.

| Element | Setup | Forces | Expected end-state |
|---|---|---|---|
| **ALPHA** | 2 rung-2 reporters, distinct text | auto path | auto-**CORROBORATED**, no moderator |
| **BRAVO** | 3 rung-1 reporters | moderator-gated + steward vouch | mod-confirmed → **CORROBORATED** |
| **SYBIL** (on BRAVO) | 1 human's 2 extra accounts | Sybil backstop (status, not count) | 2 accounts **REJECTED**; BRAVO still corroborates on the genuine 3 |
| **CHARLIE** | 2 reporters contradict | dispute path | moderator-pinned **DISPUTED** |
| **DELTA** | 1 lone witness | honest degrade | **DEVELOPING** (verified-but-uncorroborated) |
| **NEARMISS** | ~1.5 km off ALPHA | clustering edge | **separate event**, does not merge |
| **ECHO** | 2 rung-2 reporters post the **same clip** (identical `media_sha256`) | reshare defense (ADR-0020/UC8) | counted 2, **independent 1** → **DEVELOPING** (a reshare cannot corroborate) |

> **ECHO caveat (live vs dry-run).** In the dry run the identical fingerprint is
> set directly, so the reshare collapse is deterministic. In a *live* session the
> two testers must upload a **byte-identical** file for the on-device hashes to
> match; if the device's media sanitizer re-encodes non-deterministically the
> hashes may differ and the collapse won't trigger. Demonstrate ECHO from the dry
> run unless you have confirmed deterministic sanitization on the test devices.

---

## Part A — Machine check (exit criteria #1–#4)

Run `simulate(db)` (or drive the live submissions) and assert:

- **#1 Corroboration fires both ways** — ALPHA auto-corroborates (all rung-2, no
  moderator); BRAVO corroborates only after a steward vouch (rung-1 cohort). The
  distinct-identity `counted` is correct in each.
- **#2 Sybil backstop holds** — the two SYBIL accounts end REJECTED; judged on
  **status**, not count. **ECHO extends this**: even *verified* reshared media
  collapses to 1 independent source and does not corroborate.
- **#3 Deanonymization leak closed** — inspect raw API responses for
  `/api/events/<id>` and `/api/events/<id>/graph`: no `user_id`, only handles.
- **#4 Solo moderation workable** — one steward drives every verify/reject/vouch/
  dispute at this volume without contention.

This part is regression-guarded by `app/drill/test_scenario.py`; it should pass
before any live session.

---

## Part B — Comprehension check (exit criterion #5, a gate — necessary, not sufficient)

Show each tester three real event cards from the drill: a **CORROBORATED** one
(ALPHA/BRAVO), the **LONE unverified** one (DELTA), and the **DISPUTED** one
(CHARLIE) — with the reader trust display (status, "N independent sources", the
reporter chip, the confidence band).

Ask, per card, without coaching:
1. "Would you act on this — share it, cite it, believe it? Why?"
2. "Rank these three by how much you'd trust them, and say why."
3. "What does *'2 independent sources'* mean here?" (probe the reshare idea:
   "what if 100 accounts posted the same clip?")

**Pass:** a clear majority correctly rank CORROBORATED > DEVELOPING/LONE, place
DISPUTED as *contested* (not simply false), and can articulate that corroboration
counts **independent** sources, not raw posts. Record verbatim the words they use
— jargon they can't decode ("rung", "🔏", "confidence band") is a UI finding.

---

## Part C — Belief-change instrument (exit criterion #6, THE gate)

**Panel:** skeptical, non-aligned, non-technical readers — explicitly *not* T4P
insiders. Small N is expected; treat results as directional, and pre-register the
thresholds below *before* running so the result can't be rationalized after.

**Design — matched A/B with a within-subjects control.** Two matched claims
(same kind of event, different specifics), each shown in one of two conditions,
counterbalanced across the panel:

- **RAW** — the claim as a bare social post: one unverified clip, no trust context.
- **MELO** — the same claim as a Melo Event card: *"Corroborated · 3 independent
  sources · signed · confidence: medium,"* with the "why" (the source list /
  graph) expandable.

For each stimulus capture, on a 0–10 scale:
- **Belief** — "How likely is it this really happened?"
- **Action intent** — "Would you share or cite this?" (0 = no, 10 = definitely).

**Discrimination controls (run these too — they guard against "Melo = trust"):**
- a **DISPUTED** event card, and a **LONE-unverified** card. A reader who is
  genuinely reading the signal should rate these **lower** than the CORROBORATED
  card — not uniformly high just because it's "in the app".

**Backfire probe (UC4's known failure mode):** after the MELO condition, ask
"Does *'corroborated'* read to you as evidence, or as the platform taking a side?"
(scale + free text).

### Pass / fail (pre-register these)

**#6 PASSES only if all three hold:**
1. **Lift:** MELO belief > RAW belief for the CORROBORATED claim by a
   pre-set margin (suggested ≥ **1.5 points** on 0–10, or a clear majority
   shifting up in the within-subjects pass).
2. **Discrimination:** readers rate CORROBORATED **above** DISPUTED and LONE —
   i.e. the lift tracks the *signal*, not the brand.
3. **No backfire:** the "reads as platform bias" rate is below a set ceiling
   (suggested < **⅓** of the skeptical panel).

**#6 FAILS** if belief doesn't move, if CORROBORATED/DISPUTED/LONE all move
together (blanket trust or blanket distrust), or if backfire is high. **A fail is
the ADR-0020 branch signal** — shift emphasis to the archive (UC9) and debunk
(UC8) surfaces, which don't depend on lay-reader belief. Record it plainly; do
not re-run with a friendlier audience to get a pass.

---

## Data capture sheet (per tester)

```
tester id (anonymous): ____   aligned/skeptical: ____   technical: y/n
Part B  rank(CORROB / DEVELOP / DISPUTED): ____  reshare understood: y/n  jargon misread: __________
Part C  claim1 condition: RAW/MELO   belief:__/10  share:__/10
        claim2 condition: RAW/MELO   belief:__/10  share:__/10
        DISPUTED belief:__/10   LONE belief:__/10   CORROBORATED belief:__/10
        backfire (evidence 0 ── 10 platform-bias): ____   free text: __________
notes: __________________________________________________
```

---

## Summary of exit criteria

| # | Criterion | Type | Where |
|---|---|---|---|
| 1 | Corroboration fires both ways | machine | Part A |
| 2 | Sybil backstop + reshare defense hold | machine | Part A (SYBIL, ECHO) |
| 3 | No deanonymization leak | machine | Part A |
| 4 | Solo moderation workable | machine | Part A |
| 5 | Comprehension | gate | Part B |
| 6 | **Belief-change (falsifiable)** | **gate / branch point** | Part C |

Relates to ADR-0001, ADR-0006, ADR-0019, ADR-0020, and the `t4p-pilot-test-plan`
and `benchmark-use-cases` design notes.
