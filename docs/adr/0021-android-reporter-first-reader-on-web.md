# 0021. Android is reporter-first; the reader surface lives on the web; Android carries only a thin, decoy-gated awareness layer

- **Status:** Proposed
- **Date:** 2026-07-07
- **Deciders:** Project owner + design discussion, 2026-07-07
- **Relates to:** ADR-0001, ADR-0007, ADR-0010, ADR-0011, ADR-0013, ADR-0018, ADR-0019
- **Refines:** ADR-0007 (which split web=reader / Android=reporter) by quantifying *how much*
  reader surface the Android app may carry.

## Context

ADR-0007 split the clients: the **web is the reader + moderation surface**, the **Android app is
the signed reporter lane**. ADR-0019 reinforced it — the reader feed is the product's centre of
gravity, and the audience lives on the web/social, not in a native install.

But the Android app has been drifting reader-ward: it grew a map that plots incidents, and it is
tempting to keep adding browse/feed features so reporters can "see their impact." That drift needs
a boundary, because the two roles have *opposite* threat models:

- The **reporter's phone is the single highest-risk object** in the system — seizure at a
  checkpoint/detention is the most likely bad event (UC5). Everything on that device is a liability
  under coercion. A hardened reporter tool should therefore hold the **minimum**.
- The **reader is low-risk and numerous** — served best where the audience already is (the mobile
  web), with no install and no sensitive data pushed onto anyone's phone.

A full reader surface on the reporter's phone is *more to leak under seizure* (a map of where
incidents happened, which pseudonyms reported them) and is *low-leverage* for the reader mission
(a native reader reaches only installers, a tiny set; the UC4 belief question needs the mass web
audience). A second, separate native reader app is redundant with the web and not solo-maintainable.

## Decision

1. **Android is reporter-first.** Its defensible reason to exist (ADR-0013/0019, the premium signed
   "verified-source" lane) is the hardened capture path: on-device signing, EXIF strip, offline
   queue, panic-wipe, decoy mode, mesh relay. That is what the app is *for*; everything else is
   secondary.

2. **The reader + moderation surface is the web** (mobile-responsive). It reaches the mass audience
   with no install, is where the UC4 belief test actually runs, and keeps sensitive reader data off
   reporters' phones. The reader experience is **not** duplicated natively.

3. **No separate native reader app.** Redundant with the mobile web, solo-infeasible to maintain,
   and low-leverage. Two apps is the wrong answer; so is one app trying to be everything.

4. **Android may carry a THIN, reporter-scoped awareness layer — and only behind the security
   model.** A field reporter is also a witness and has legitimate needs that look reader-ish:
   - their own track record ("your reports: N submitted, M corroborated"),
   - a **compromise alert** on their pseudonym (the ADR-0018 revocation signal),
   - light situational awareness of nearby incidents (the event map).

   These are permitted **only** if they are gated by the existing safety model — **decoy mode shows
   nothing, panic wipes them** — and only in a reporter-scoped, minimal form.

5. **Explicit boundary — the Android event map stays as decoy-gated situational awareness, not a
   reader browser.** It must not grow into: full feed browsing, comment/discussion threads, media
   galleries beyond what capture needs, reader-trust explainers, or anything whose purpose is
   *audience consumption* rather than *reporter awareness*. Those belong on the web.

## Consequences

- **Smaller seizure attack surface on the reporter's phone** — a safety property, not just tidiness.
  Less reader data on the device means less to lose under coercion (UC5).
- **Reader/UC4 effort concentrates on the web**, where the audience is and where belief-change can
  actually be measured — consistent with ADR-0019.
- **Solo-feasible:** one hardened reporter app + one web surface, no second native app to maintain.
- **The Android map survives but is bounded.** It is retained (already decoy-gated in
  `MapViewModel`) as reporter awareness; this ADR is the guardrail against it creeping into a full
  reader experience.
- **Accepted trade-off:** reporters get a *leaner* in-app reader experience than a full browse would
  give. That is acceptable — the web serves the rich reader experience, and the phone stays lean for
  safety. If reporters need richer reader access, they use the web like everyone else.
- **Every new Android feature now gets one test:** does it serve *the reporter* (capture, safety,
  their own standing/awareness) and survive the decoy/panic model? If it only serves *audience
  consumption*, it belongs on the web.

## Code state (2026-07-07)

Matches the decision today. Android has the reporter tooling (signing ADR-0013, panic/decoy,
mesh relay, offline submit) plus, as of this session, an **event-based map** (`MapFragment` /
`MapViewModel`) that plots one status-colored mark per incident and is **already blanked in decoy
mode**. There is no full reader/browse surface on Android. The web (`app/frontend`) is the reader +
moderation surface. This ADR does not require code changes; it **bounds future ones** — the map is
the current edge of what Android should carry, and reader-browse features should be declined on the
reporter app and built on the web instead.
