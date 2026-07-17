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

> **Hardened 2026-07-06 by a 5-persona agent red-team** (opposed skeptic,
> everything-is-fake cynic, low-effort scroller, brand-skeptic, non-technical
> elder). Their convergent verdict on the *first* draft of this instrument:
> **it would likely record a RAW→MELO belief bump and misread it as "the signal
> works," when the bump is driven by sober formatting while the trust labels
> themselves partly backfire — and a low score from confusion is
> indistinguishable from a low score from distrust.** That is the exact false
> positive ADR-0020 warns about. The controls below exist to prevent it. (The
> agent pass hardens the *instrument*; it is NOT belief data — only humans run
> Part C.) See Appendix A (backfire) and Appendix B (jargon).

**Panel:** skeptical, non-aligned, non-technical readers — explicitly *not* T4P
insiders. Small N is expected; treat results as directional, and pre-register the
thresholds below *before* running so the result can't be rationalized after.
**Pre-measure each reader's dispositional trust** (general trust in media /
institutions, 2–3 items) so a persona effect can't masquerade as an instrument
effect.

### Stimulus arms — RAW-vs-MELO alone is fatally confounded

The two-up RAW-vs-MELO comparison changes *many* variables at once (layout,
sobriety, metadata, a reporter, badges, AND the trust verdict), so a belief lift
can't be attributed to *corroboration* rather than to *polish*. Run these arms so
each variable is isolated (one claim per reader per arm, **between-subjects** for
the core comparison, order **counterbalanced**):

| Arm | What it is | Isolates |
|---|---|---|
| **RAW** | bare social post, scary clip, no context | floor |
| **MELO-corroborated** | full trust card (status + N independent + signed + confidence) | the headline claim |
| **MELO-styled-uncorroborated** | *same chrome*, but "1 source · uncorroborated" | **polish vs signal** (the key control) |
| **verdict-word-removed** | the evidence ("3 accounts, footage matches across angles") *without* the word "Corroborated" | **the label vs the evidence** |
| **masthead-swap** | same card attributed to a *known* outlet instead of Melo | **the unknown-brand penalty** (platform-trust transfer) |
| **false-corroboration trap** | a "Corroborated" card whose claim is actually thin/planted | **over-trust** — does the badge manufacture misplaced confidence? |

### Measures — separate belief, platform-trust, and attention

Per stimulus, in this order:

1. **Noticing / recall gate (before anything else).** Unprompted: *"What did this
   card tell you?"* and *"Was this event corroborated, disputed, or unconfirmed?"*
   A reader who can't answer never processed the signal — their belief rating is
   noise (the scroller fails this). **Notice-rate is itself a primary result.**
2. **Event belief (about the world), 0–10** — "How likely is it this event
   actually happened?"
3. **Platform-assessment trust (about Melo), 0–10** — "How much do you trust
   *Melo's* assessment of it?" — kept SEPARATE from #2, because a reader can find
   the event plausible on base rates while distrusting Melo entirely (or vice
   versa). Fusing them is the instrument's biggest confound.
4. **Attribution** — "How much of your answer to #2 comes from the labels vs your
   own prior sense of the event vs the footage itself?"
5. **Action intent — split** — "share as true?" and "cite it (name attached)?"
   are different acts; capture both, plus **free-text why-not** ("wouldn't cite —
   unknown platform" is the exact backfire).
6. **Backfire — open first, then options.** Ask open: *"What does 'corroborated'
   tell you here, and who decided it?"* THEN offer ≥4 choices (evidence /
   platform taking a side / an unverifiable assertion from a party I can't hold
   accountable / a machine's guess / didn't notice it). The old binary *planted*
   the "taking a side" frame and hid the real skeptic answers.
7. **Honest-labeling probe (a likely POSITIVE — test it).** After the DISPUTED /
   LONE cards: "Did seeing Melo label some events *Disputed* / *Developing* change
   your trust in the platform? up / down / why?" Every skeptic persona trusted the
   *method* more for its honest uncertainty — the badge-vs-RAW framing misses this
   entirely, so measure it directly.

**Comprehension gates belief (run Part B first, per reader).** A low belief score
from someone who misread "🔏 signed" as "Melo endorsed" or "independent sources"
as "three newsrooms" measures a *misunderstanding*, not the signal — you cannot
tell a backfire from a comprehension failure otherwise. Treat any Part-C rating
built on a failed comprehension item as a **jargon finding, not a trust finding.**

**Realism.** Present in a **time-pressured scrolling feed with distractor items**,
not a calm side-by-side — side-by-side induces a comparison real readers never
make and telegraphs the "trust the pretty one" demand effect.

### Pass / fail (pre-register these)

**#6 PASSES only if all of:**
1. **Signal, not polish:** MELO-corroborated belief exceeds **MELO-styled-
   uncorroborated** (same chrome) — not merely RAW — by a pre-set margin
   (suggested ≥ **1.5 pts**/10). Beating RAW alone does not count; that could be
   pure formatting.
2. **Discrimination:** CORROBORATED rated above DISPUTED and LONE — the effect
   tracks the signal, not the brand.
3. **No net backfire:** the "unverifiable assertion / platform taking a side /
   machine's guess" share is below a set ceiling (suggested < **⅓**), and belief
   is not *lower* than the styled-uncorroborated control.
4. **No manufactured over-trust:** the **false-corroboration trap** does not
   raise belief the way a genuine corroboration does — else the badge inflates
   confidence rather than tracking evidence.

**#6 FAILS** if the lift vanishes against the styled control (it was polish), if
CORROBORATED/DISPUTED/LONE move together (blanket trust/distrust), if backfire is
high, or if the trap inflates belief. **A fail is the ADR-0020 branch signal** —
shift emphasis to the archive (UC9) and debunk (UC8) surfaces, which don't depend
on lay-reader belief. Record it plainly; do not re-run with a friendlier audience
to get a pass.

---

## Data capture sheet (per tester)

```
tester id (anon): ____  disposition: skeptical/aligned  media-trust pre(0-10): __  technical: y/n
Part B (comprehension GATE, run first)
  rank CORROB/DEVELOP/DISPUTED: ____   reshare understood: y/n
  term glosses correct? corroborated:_ independent-sources:_ signed:_ rung:_ confidence(automated):_ handle:_
Part C (arm assigned): RAW / MELO-corrob / styled-uncorrob / verdict-removed / masthead-swap / trap
  noticed signal (recall gate): y/n   recalled status correctly: y/n
  event-belief:__/10   platform-trust:__/10   attribution(label/prior/footage): __________
  share-as-true:__/10   cite:__/10   why-not: __________
  backfire (open): __________   then pick: evidence/side/unverifiable/machine-guess/didnt-notice
  honest-labeling effect (after DISPUTED+LONE): up / down / none — why: __________
notes: __________________________________________________
```

---

## Appendix A — Backfire-vector register (from the 5-persona red-team)

Concrete ways a skeptical reader reads the trust display as bias/manipulation,
trusts it *less*, or trusts it for the wrong reason. Ranked by cross-persona
convergence. These are **hypotheses to test on humans**, and a punch-list for the
reader-UI (they are *product* findings, not just instrument findings).

| Trigger | How it backfires | Personas |
|---|---|---|
| **"Corroborated" as a past-tense STATUS** | reads as a verdict handed down → "by whose authority?" → for an unknown/activist platform = *taking a side*. The positive label is the one that backfires. | 4/5 |
| **"(automated)"** | "no accountable human — a machine can't be sued, fired, or shamed"; false precision. Undercuts the whole card. | 4/5 |
| **"🔏 signed"** | misread as *Melo endorsed/approved* (editorial seal) or as *password/lock* — almost nobody read media-integrity; inflates the wrong claim. | 4/5 |
| **"rung 2"** | reads as platform-internal, self-vouching ("our guy, trusted by us") = circular = taking a side; scale ambiguous, "2 sounds low." | 5/5 |
| **pseudonymous handle "k-7f3a"** | reads as a bot/spam serial number, machine-made, impersonal → *less* trust; "a codename is the opposite of a byline." | 4/5 |
| **green ✓ + badge stack** | density of badges on the "good" card pattern-matches to verified-checkmark *advertising* → trust-me chrome, not evidence. | 2/5 |
| **"independent sources"** | unauditable assertion; "asserting independence is exactly what a coordinated source would also do." | 3/5 |
| **the evidence is hidden behind "why?"** | the badge does the persuading, the reasoning is unread → **manufactured / wrong-reason trust** in credulous readers. | 2/5 |
| **✓ on BOTH Corroborated AND Disputed** | for a skimmer the check "closes the question" — *the ✓ cancels the ⚠ warning*; three states collapse to two. (**a real UI bug, not just a test finding**) | 2/5 |
| **unknown brand ("who is Melo?")** | every reassurance routes back to a party the reader can't hold accountable; "corroborated" from an unaccountable source is a *discount* signal. | 2/5 |

## Appendix B — Jargon / comprehension register

What readers *thought* each element meant. A belief rating built on these misreads
measures confusion, not the signal — hence the comprehension gate before Part C.

| Element | Common misread | Fix direction |
|---|---|---|
| **corroborated** | "confirmed/verified TRUE by an authority" (stronger than "multiple similar reports") — over-promises | gloss: "checked against other people who saw the same thing"; attribute it ("Melo's assessment") |
| **independent sources** | ambiguous: independent of *each other* / *the reporter* / *Melo*? Elder pictured **newsrooms**, not 3 people with phones | say "different people, not connected to each other, who each reported it" |
| **rung 2** | game level / rank; "2 sounds low"; no scale | replace with words + scale: "track record: some, not yet well-established" |
| **🔏 signed** | "Melo approved/endorsed" or "secure/password" | gloss: "the reporter proved this post is really theirs and untampered" |
| **Confidence: Medium (automated)** | "Medium = they're not sure, so why should I be?"; "(automated) = no human checked"; referent undefined | reconsider showing "(automated)" to lay readers; state confidence *in what* |
| **k-7f3a** | bot/spam/serial number, not a person | show "a verified reporter (name protected)"; hide the raw code |
| **~9:40pm** (tilde) | auto-generated/templated/typo → faintly bot-like | drop the tilde or say "about 9:40pm" |
| **⚠ accounts conflict — treat with caution** | *understood and liked* — the single most trust-building element | **keep**; it's plain-language and action-guiding |
| **"new reporter"** | understood and liked (plain English) | keep |

## Appendix C — Product findings (beyond the instrument)

Too important to bury in a test doc — surfaced unprompted by every persona:

1. **Honest labeling is the strongest trust-builder; the confident badge is the
   weakest.** Skeptics trusted Melo's *method* more for its DISPUTED/LONE
   uncertainty and *less* for the confident CORROBORATED verdict. Lean the reader
   UI on visible, plain-language uncertainty — not on a green stamp.
2. **The reader UI has a live bug:** a ✓ on both Corroborated and Disputed. The
   status must be carried by a single, instantly-different visual, and the ✓ must
   not appear on Disputed.
3. **The evidence is buried behind "why?".** The one auditable, persuasive line
   ("footage matches across angles") sits behind a tap almost no one takes; the
   unearned badge is what's visible. Consider surfacing a plain-language *reason*
   on the card face.
4. **Machine/impersonal framing (codes, "automated", padlocks) reads as
   bot-generated** next to a human tragedy — actively lowering trust for
   non-technical readers. Humanize the provenance language.

These feed the reader-UI backlog and a future ADR; they are consistent with
ADR-0006 (show the basis, plain-language) and the UC4 backfire risk.

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
