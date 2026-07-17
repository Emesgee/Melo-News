# 0010. Build the Android app first, gated on a safety-hardening milestone

- **Status:** Accepted
- **Date:** 2026-07-05
- **Deciders:** Project owner + grill session, 2026-07-05
- **Relates to:** ADR-0003, ADR-0007, ADR-0011; supersedes the web-first note in the
  `build-sequence-to-pilot` plan if accepted

## Context

The earlier build sequence deliberately ordered the work **web-first** (A → B → D → E
→ F → web T4P test → C signing → real pilot), on the logic that the first pilot is a
scripted, mostly-web corroboration drill and corroboration runs on distinct `user_id`,
not signing keys — so the demoable trust slice doesn't need the Android signing lane.

The project owner now judges the **Android app the most important thing to build**,
because it is the actual product: no at-risk field reporter files from a browser. The
entire safety and anonymity case (offline capture, on-device signing, EXIF stripping,
panic/decoy, mesh relay) lives on Android. Web is explicitly the lower-assurance lane
(ADR-0007).

This is defensible on *importance*. The risk it introduces is *irreversibility*: the
Android lane is the one place where a defect can physically endanger a reporter, and
the current app's safety layer is substantially stubbed (ADR-0011).

## Decision (proposed)

Build Android-first, but treat the safety-hardening milestone — not the fun
plumbing — as the gate:

1. **Prove the thin signing slice** end-to-end in a walled sandbox (test devices,
   dummy data only): device keypair → canonical message matching the server contract
   (with the ADR-0008 field set) → signed `/stories/ingest` → server verifies → 🔏
   badge, with reader-side media verification (ADR-0009).
2. **Then harden safety (ADR-0011)** — encrypted local storage, Keystore-backed
   secrets, and closing the on-device-sanitizer-only gap — as the hard release gate.
3. **Only then** put the app in the hands of a single real reporter.

Tripwire: the thin slice must have **no path to a real reporter's real report** until
step 2 passes. Enforced by not distributing the app outside the test group.

## Resolved (2026-07-05)

- **Next milestone = (a) the scripted T4P sandbox drill** — test devices, dummy data,
  known testers. **Real-reporter use is hard-gated behind ADR-0011** (security
  hardening). The app is currently installed only on the owner's own phone, so no one
  is at risk today; the gate governs *expansion*, not the drill.
- Because the drill is low-stakes, the stubbed security does **not** block it. The
  thin signing/trust slice is safe to build and exercise in the sandbox now, with
  ADR-0011 running as a parallel must-finish-before-(b) track.

## Resolved — priority within milestone (a) (2026-07-05)

**Build the trust-model payoff before the Android signing slice.** The drill is a
comprehension test of the trust display, and today that display shows a wall of zeros
(track record 0/0, no rung climbing, DISPUTED unreachable — ADR-0004/0005 gaps). First
work is therefore **wiring corroboration + reporter track record so they actually show
up** (see ADR-0012); the Android signing slice (ADR-0008/0009) follows. Named tension
accepted: milestone (a)'s first task is backend/web, not Android, even though Android
is the priority *product*.

## Resolved — signing-slice first-cut scope (2026-07-05)

- **Reader-side media verification (ADR-0009) is a fast-follow, not first cut** — the
  full ADR-0008 envelope (incl. `media_sha256`) is *signed* and stored from day one,
  but the reader-side re-hash/verify UI is deferred; the first-cut 🔏 badge is
  server-attested. See ADR-0015.

## Resolved — track record + rung placement (2026-07-05)

- **Auto rung-climbing (ADR-0005) is out of scope for the drill; the cohort is
  hand-vouched** to rung 2 via the existing steward tool. See ADR-0012.
- **Reporter track record is computed on read**, not maintained as stored counters,
  so the trust display stops showing `0 / 0`. See ADR-0012.

## Consequences

- First real validation happens on the high-stakes lane, so the safety gate stops
  being deferrable and becomes front-loaded.
- Larger, slower first deliverable than the web-first slice.
- Signing (ADR-0008/0009) becomes near-term work, not post-pilot.

## Code state (2026-07-05)

Android has real offline/panic/decoy/sanitizer/mesh foundations but **no signing** and
**stubbed local-storage security** (ADR-0011). The server signing contract exists but
has no client. Nothing in the pilot flow depends on Android signing today.
