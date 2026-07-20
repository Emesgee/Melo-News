# 0023. High-impact steward actions require an M-of-N quorum; the audit log is the substrate, not the safeguard

- **Status:** Proposed
- **Date:** 2026-07-20
- **Deciders:** Project owner + design discussion, 2026-07-20
- **Relates to:** ADR-0001, ADR-0004, ADR-0005, ADR-0006, ADR-0016, ADR-0019, ADR-0020
- **Completes:** ADR-0005, which introduced the steward role and explicitly deferred the M-of-N
  governance mechanism ("For the pilot the bootstrap steward acts directly").

## Context

The `steward` role is the only actor that can rewrite the trust graph: set any user's **rung**
(`set_rung`, `set_rung_by_handle`) and any user's **role** (`set_role`), including minting other
moderators and stewards. Five endpoints are `@steward_required` today, and each executes the moment
one steward calls it. `app/moderation/routes.py` says so in as many words: *"High-impact
promotions/revocations are M-of-N in the full governance design; that's deferred. For the pilot the
bootstrap steward acts directly."*

That is acceptable for a solo-operated dummy-cohort drill and unacceptable the instant it is not.
The steward is the one actor who can **defeat the Sybil defence from the inside**: rung-2 is the
scarce credential that lets an Event reach CORROBORATED (ADR-0005 gate), and a steward is the sole
source of rung-2. A single steward — compromised, coerced at a border, phished, or simply turned —
can:

- vouch a ring of sock-puppets to rung 2 and **manufacture a "corroborated" event** (a fabricated
  atrocity, or a fabricated *corroboration of a denial* of a real one — the UC8 atrocity-denial
  risk, run in reverse);
- **demote or silence** a genuine reporter by dropping their rung;
- **mint a second attacker** by granting `steward`/`moderator` to an accomplice.

For a product whose entire value is a *trustworthy* corroboration signal (ADR-0001/0019), a single
unchecked key over the trust graph is the highest-leverage failure in the system. It is strictly
worse than a compromised moderator, whose blast radius is one incident's worth of verify/reject and
is fully reversible (ADR: moderation undo + audit).

An **append-only audit log now exists** (verify/reject/reversal and every rung/role change are
recorded with actor, transition, and reason). That was the necessary precondition — but it is
*observation, not prevention*. A rogue steward is now **visible after the fact**; they are not
**stopped**. Detection that arrives after a fabricated event has already been published, believed,
and screenshotted is not a control.

## Decision

**High-impact steward actions require an M-of-N steward quorum: at least M distinct stewards must
approve before the action takes effect. Low-impact steward actions remain unilateral. The audit log
is the substrate the quorum records into, never a substitute for it.**

1. **High-impact (quorum-gated) actions** — the irreversible or trust-graph-defining ones:
   - `set_role` to or from `steward` or `moderator` (minting/removing privileged actors);
   - `set_rung` / `set_rung_by_handle` to **rung 2 or 3** (granting corroboration-bearing trust).

2. **Low-impact (unilateral) actions** — reversible, non-privilege-granting:
   - `set_rung` **down** to rung 1 (revoking trust is safe to do fast — the failure mode of an
     over-eager demotion is a stalled reporter, not a fabricated event; err toward letting a single
     steward pull the brake);
   - all moderator-level actions (verify/reject/reversal) stay single-actor with undo + audit.

3. **Mechanism.** A high-impact action creates a **pending governance request** rather than
   applying immediately: `{action, target, proposed_value, proposer, reason, created_at}`. Other
   stewards **approve** (or reject) it; on reaching **M distinct approvers (proposer counts as
   one)** it executes and is written to the audit log with the full approver set. Requests expire
   unexecuted after a TTL. The proposer may not be the sole approver — M ≥ 2 by definition.

4. **N and M are configured, with an honest bootstrap exception.** N is the number of active
   stewards; M is the threshold (default **2-of-N**, raised as N grows). **Below N = M there can be
   no quorum**, so a genuine bootstrap (the very first steward, or a cohort with fewer than M
   stewards) runs in an explicit, logged **single-steward mode** — the pilot's current behaviour,
   but *named and flagged as unsafe* rather than silent. Leaving bootstrap mode (reaching M
   stewards) is itself a logged event.

5. **The audit log is load-bearing but subordinate.** Every proposal, approval, rejection, and
   execution is recorded. The log answers "who vouched the Sybil, and who co-signed it"; the quorum
   ensures the answer is never a single name.

**Rejected:** keeping unilateral steward action past the drill (a single key over the trust graph
is the system's highest-leverage compromise); treating the audit log as the safeguard (it detects,
it does not prevent, and detection-after-publication is too late for a trust product); and gating
*every* steward action behind quorum (revoking trust and routine rung-1 housekeeping do not warrant
the friction, and a too-heavy gate pressures operators back toward a single super-steward).

## Consequences

- **The single-steward compromise stops being catastrophic.** Manufacturing a corroborated event
  now requires colluding stewards, not one coerced phone — which is the entire point, and aligns the
  governance model with the Sybil-resistance the product already claims elsewhere.
- **Real friction is added to the drill's most-used bootstrap action.** Vouching a tester to rung 2
  is *the* operation that makes the corroboration machine go (ADR-0016), and it is now quorum-gated.
  This is why single-steward bootstrap mode is retained explicitly: a solo pilot keeps working, but
  the mode is visible, logged, and understood to be pre-safety — not mistaken for the finished
  system.
- **It creates a real build: pending-request storage, an approval flow, a stewards-review surface,
  and TTL/expiry.** Non-trivial, and it depends on the audit log already shipped. It is the natural
  next governance increment after undo + audit.
- **Availability tension.** M-of-N means M stewards must be reachable to grant trust; in a blackout
  or with stewards in hostile conditions, that can stall legitimate promotions. Bootstrap mode and a
  tuned M are the pressure-relief valves; a too-high M recreates the single-super-steward it was
  meant to prevent, from the opposite direction.
- **This is governance, not cryptography.** M-of-N here is an application-level approval flow, not
  threshold signing. A future hardening step could bind approvals to steward device keys (ADR-0013)
  so an approval is itself signed and non-repudiable — noted, not required now.
- **Scope boundary.** This governs *who may change the trust graph*. It does not address a
  compromised *server* (an attacker with DB access bypasses the whole application layer); that is
  ADR-0011 / hosting-jurisdiction territory (UC7), and remains separate.

## Code state (2026-07-20)

**Not built. Single-steward mode is the live behaviour**, and it is now the *only* mode: all five
`@steward_required` endpoints in `app/moderation/routes.py` execute on one steward's call. What
exists as of today is the **precondition, not the control**: the append-only `AuditLog` records
every rung/role change (actor, before→after, reason) and every moderation decision/reversal, and
the steward activity-log surface renders it. There is no pending-request model, no approval flow,
and no M-of-N threshold. For the drill this is fine and intended; this ADR marks the boundary — the
gate to build **before a second steward exists or a real (non-dummy) cohort forms**, whichever comes
first.
