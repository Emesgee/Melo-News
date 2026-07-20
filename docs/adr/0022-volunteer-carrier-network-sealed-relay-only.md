# 0022. Non-reporters may carry reporters' data only as sealed, transit-only middle relays — never in the current plaintext form

- **Status:** Proposed
- **Date:** 2026-07-20
- **Deciders:** Project owner + design discussion, 2026-07-20
- **Relates to:** ADR-0003, ADR-0008, ADR-0009, ADR-0011, ADR-0013, ADR-0019, ADR-0021
- **Bounds:** ADR-0021 (Android is reporter-first) — this ADR governs whether a *non-reporter*
  may run the client at all, and what they are permitted to carry.

## Context

Two separate goods pull toward putting the app on ordinary people's phones:

1. **Crowd cover.** If only journalists install Melo, then *having Melo installed is itself
   incriminating*. A large ordinary-user population is a real security property for reporters —
   plausibly a stronger one than any cryptography we could add. This is Tor's "anonymity loves
   company" argument, and it is sound.
2. **Blackout resilience.** The mesh relay already lets an offline phone hand reports to a nearby
   online phone, which uploads them. More carrying devices means reports escape a communications
   blackout more reliably.

Both point at recruiting non-reporters — supporters who install the app but never file a report.

**The blocker is that the relay, as built, would endanger those volunteers.**
`android/.../mesh/MeshRelayManager.kt` serialises a relayed report as **plaintext JSON**:

```kotlin
val json = gson.toJson(relayCopy)
val payload = Payload.fromBytes(json.toByteArray(Charsets.UTF_8))
```

There is no encryption anywhere in that path, and the receiving device **persists it into its local
Room queue** (`LocalStory`: `title`, `body` — the witness statement — and `mediaLocalPath`). A
volunteer running this build holds *readable testimony about atrocities, attributable to a specific
reporter, on their own phone*. Under a checkpoint search, border inspection, or device seizure, the
carrier is holding precisely the material the system exists to protect. That inverts the project's
ethics: civilians would be absorbing risk on journalists' behalf, unknowingly.

Two further asymmetries shape the decision:

- **Middle relay vs. exit.** Tor's operational history is unambiguous: exit nodes attract raids and
  legal action; middle relays almost never do. The distinction is whether the operator is the
  visible origin of content. A carrier that forwards sealed bytes is a middle relay. A carrier that
  decrypts, stores, or publishes is an exit.
- **Crowd cover cuts both ways.** A uniform client helps a reporter disappear into the crowd, but it
  also makes an ordinary user *look like a reporter* to an adversary. Inside hostile territory that
  can convert a civilian into a suspect. The benefit accrues to reporters; the risk lands on whoever
  is standing in the wrong jurisdiction.

## Decision

**We will not ship relay capability to non-reporters in its current form. A non-reporter may carry
another person's data only as a sealed, transit-only middle relay, and only once the conditions
below hold. Until then, any build offered to non-reporters must carry nothing.**

Four hard constraints, in priority order:

1. **Sealed payloads (non-negotiable).** The reporting device encrypts to *Melo's server key* before
   handing anything to a carrier. The carrier holds ciphertext it has no key for and cannot open.
   This is the constraint that does the real work: it converts "possessing footage of a killing"
   into "possessing random bytes," a materially different legal and physical position. Every other
   measure here is secondary.
2. **Transit, not storage.** Short TTL, hard size cap, purge on delivery or expiry. A carrier must
   never accumulate an archive. (Note the deliberate tension with UC9's capture-before-deletion
   archive: the *server* preserves bytes; a *carrier* must not.)
3. **No origin metadata.** A carrier must not learn which pseudonym authored what it carries.
   Otherwise the volunteer becomes a device that can betray reporters under examination.
4. **Middle relay only, never an exit.** A carrier forwards to Melo's infrastructure. It never
   decrypts, never publishes, and is never the visible origin of content.

Plus two rules governing who may carry:

5. **Opt-in, off by default, with specific informed consent** — plain language naming what is
   carried and the risk, not buried in terms of service. Silence is not consent for this.
6. **Geography is a first-class safety input.** Carrier recruitment targets **diaspora and
   supporters outside the hostile jurisdiction**, where personal risk is low and benefit is high.
   We do **not** recruit carriers inside the territory, where the risk is asymmetric and severe,
   absent explicit case-by-case consent.

**Gate:** none of this ships before **ADR-0011** (real at-rest encryption, Keystore-backed secrets)
is satisfied *and* sealed payloads exist. Building a volunteer carrier network on top of an
unencrypted local queue would put civilians at risk in order to protect journalists — the wrong
trade, made in the wrong direction.

**Rejected:** shipping the current plaintext mesh to non-reporters (it endangers them); a carrier
that can read what it carries under any "trusted volunteer" rationale (trust is not a security
control, and it does not survive device seizure); and recruiting in-territory carriers for crowd
cover (it transfers journalist risk onto civilians who gain nothing).

## Consequences

- **Crowd cover is available immediately at zero risk, via a carry-nothing build.** An app that
  relays nothing still makes a reporter's install unremarkable — the primary security benefit —
  without exposing the installer to anything. This is the near-term move.
- **It collides with ADR-0021**, which puts the reader surface on the web precisely to keep data off
  phones. A non-reporter install exists mainly to be *installed*, not used. That is a deliberate
  decision to make, not a drift; ADR-0021 should be revisited if we pursue it.
- **Sealed payloads are a client-contract change**, in the same family as the deferred on-device
  perceptual hash (ADR-0009/0020) — the reporting device gains an encrypt-to-server step, and the
  server gains a decrypt path. Not a small change, and worth batching with other envelope work.
- **The mesh relay is now known-unsafe for third parties and should be treated as reporter-to-
  reporter only** until sealed. Reporters relaying for each other already share the risk class;
  volunteers do not.
- **A legal question is created, not answered.** Whether carrying sealed ciphertext exposes a
  volunteer in their own jurisdiction is a real question (UC7) and varies by country. This ADR
  reduces exposure; it does not eliminate it, and we should not claim otherwise to volunteers.
- **Recruitment becomes geographically scoped**, which shrinks the potential carrier pool but keeps
  the risk where it is survivable.

## Code state (2026-07-20)

**Not built, and the existing mesh is the opposite of this decision.**
`MeshRelayManager.kt` implements CLUSTER-strategy Nearby Connections relay (advertiser +
discoverer), transferring `gson.toJson(relayCopy)` as `Payload.fromBytes(...)` — **plaintext**,
persisted by the receiver into the local Room queue and uploaded by `SyncManager`. There is no
encryption, no TTL, no size cap, and no origin-metadata stripping in that path.

The drill is unaffected: it runs reporter-to-reporter on the signed Lane-B path, and no volunteer
carrier exists. **Immediate implication:** mesh must not be enabled in any build handed to a
non-reporter, and the current build should not be promoted to supporters as a way to help.
