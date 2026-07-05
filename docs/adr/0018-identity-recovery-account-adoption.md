# 0018. Reporter-identity recovery is account-adoption of a rotated device key, not a backup of the signing key

- **Status:** Proposed
- **Date:** 2026-07-05
- **Deciders:** Project owner + grill session, 2026-07-05
- **Relates to:** ADR-0003, ADR-0011, ADR-0012, ADR-0013, ADR-0016
- **Deferred to:** the ADR-0011 real-reporter hardening gate (not built for the drill)

## Context

ADR-0013 puts the signing key in the AndroidKeyStore precisely so it is
**hardware-bound and non-extractable** — a seized device cannot yield the key.
ADR-0003 makes the public key *itself* the reporter's identity: there is no
signup and no server credential store, and a fresh key self-registers a
pseudonym at rung 1 (`register_or_get_pseudonym`).

Those two properties have an unavoidable cost, and it surfaced live during
on-device testing on 2026-07-05. Clearing the app's data ("Settings → Apps →
Clear storage") **destroyed the AndroidKeyStore key** on the test device. The app
found no key, minted a **new** P-256 key, and self-registered a **new** pseudonym
(`k-0d241c76ea`, rung 1) — the prior pseudonym `k-e199270332` (rung 2) and its
entire track record were orphaned. Report id=23 landed PENDING because the new
key was rung 1.

The same loss happens on **uninstall/reinstall, factory reset, a lost or broken
phone, or the deliberate panic-wipe** (ADR-0011's volume-down×5 gesture, which
*intends* to burn the identity). Because the key is non-extractable, it **cannot
be backed up** — there is nothing to restore. For a real reporter, "I broke my
phone and lost my entire verified track record" is a serious failure mode, not a
testing curiosity.

Every recovery mechanism trades away some of the seizure-resistance that
ADR-0013 exists to provide:

- **Mnemonic seed (wallet-style).** Derive the key from a written-down phrase, so
  reinstall + re-enter reproduces the same identity. But the key is then
  **software-derivable**, not hardware-locked — a captured phrase, or a coerced
  reporter, reproduces the identity. This directly re-opens the ADR-0013 threat.
- **Proactive rotation certificate** (old key signs "this new key is me"). Clean
  for *planned* device changes, but **useless for recovery**: if the old key is
  already gone (clear-data, dead phone), there is nothing left to sign the
  handoff.
- **Backup of the private key** to cloud/file. Requires an *extractable* key —
  abandons hardware backing entirely.

## Decision

**Recovery is server-side continuity anchored to the reporter's account, not a
backup or seed of the key. The device key stays non-extractable (ADR-0013
unchanged); a new device key is *adopted* under an existing pseudonym after the
reporter re-authenticates.**

Concretely, for the real-reporter build (ADR-0011 gate):

1. **Anchor the durable identity to the account, not the raw key.** Today the
   pseudonym `User` is keyed by `public_key`, and ADR-0016 already notes the
   double-identity (JWT account vs. pseudonym `User`) that exists in the DB but is
   invisible to readers. This ADR promotes that account link from an accident to
   the **recovery anchor**: a pseudonym may, over its life, have **several device
   public keys** — one current, the rest rotated-out — all presenting the *same*
   `k-xxxx` handle and the *same* track record to readers.

2. **Two rotation paths — prefer the cryptographic one; fall back to adoption
   only for true loss.** These are not alternatives to choose between per build;
   both ship, and the app takes whichever the situation allows:

   - **(2a) Key-signed rotation (preferred, zero server trust).** When the
     reporter *still holds* the old device — a planned phone upgrade — the **old
     key signs a continuity statement authorizing the new key** (old pubkey, new
     pubkey, timestamp). The server binds the new key on that cryptographic proof
     alone. The account is not the trust anchor here; the *old key* is. A
     compromised server cannot forge this, because it has no private key. This is
     the ADR-rejected "proactive rotation cert" — rejected as a *recovery*
     mechanism (useless once the key is gone), but adopted here as the *first-
     choice* path whenever the key is still available.

   - **(2b) Account-adoption (last resort, for genuine loss).** When the old key
     is gone (clear-data, dead/seized phone, factory reset), there is nothing left
     to sign a handoff. The app generates a fresh AndroidKeyStore key; the
     reporter logs into their existing account; the server **binds the new key to
     the account's existing pseudonym** instead of self-registering a new one.
     This is the path that rests on account auth, so it carries the trust cost in
     Consequences and is the reason the honeypot-free account auth (ADR-0016
     deferred item) is a hard prerequisite.

   In both paths the new key becomes the *current* signing key; prior keys are
   retained only to verify already-published reports they signed. The app tries
   (2a) automatically when an old key is present and only offers (2b) when it is
   not — so server-trust exposure is confined to real recovery events, never
   incurred on a routine upgrade.

3. **Every rotation is logged in an append-only, visible record.** Each binding
   (2a or 2b) writes an immutable rotation entry to the pseudonym's history —
   old key, new key, path used (key-signed vs. account-adopted), timestamp — that
   is surfaced to stewards and, in coarse form ("rotated device on \<date\>"), to
   readers. The point is **detectability**: a silent server-side or rogue-steward
   re-bind (the 2b trust risk) cannot happen invisibly; it leaves a permanent mark
   that the reporter and reviewers can see and dispute. Adoptions are additionally
   rate-limited, and a loss-path (2b) binding may require steward review before the
   pseudonym's rung/track record transfers.

4. **Track record follows the pseudonym, not the key.** ADR-0012 counts are
   recomputed against the pseudonym's whole key history, so a rotation does not
   reset `reports_count` / `corroborated_count`. Reports signed by a
   since-rotated key still verify against *that* key (stored per report in
   `signed_message`'s `public_key` + `report_signature`), so history stays
   tamper-evident.

5. **What signing still proves is narrowed, honestly.** A signature proves "the
   holder of *a* key bound to this pseudonym authored this," not "the one
   irreplaceable key." That is the deliberate cost of surviving device loss —
   see Consequences.

**Rejected:** mnemonic-seed and key-backup recovery, because they make the
identity key reproducible off-device and re-open the ADR-0013 seizure threat that
is the whole point of hardware backing. Account-adoption keeps the key
non-extractable and additionally covers the lost/broken-phone case that a seed
does not (a reporter who never wrote the seed down is still recoverable via their
login).

## Consequences

- **Lost/broken/cleared/reinstalled phone is recoverable** without ever making
  the signing key extractable — the reporter re-authenticates and continues under
  the same pseudonym and track record.
- **A new server-trust dependency appears.** Continuity now rests on the account
  auth, not on the key alone — softening ADR-0003's "the key *is* the identity"
  to "the key is the identity; the account is the recovery custodian." This is a
  real trust shift and is why it is gated to ADR-0011, alongside removing the
  JWT/credential honeypot (ADR-0016) — the account model must be hardened in the
  same pass, not bolted on.
- **Compromise blast radius changes — but only on the loss path (2b).** The
  key-signed path (2a) rests on the *old key*, which the server cannot forge, so a
  routine upgrade carries no server-trust cost. Only genuine-loss adoption (2b)
  lets whoever passes the account auth bind a new key and post as the pseudonym.
  Account-auth hardening (signature-backed challenge, not a reusable password
  honeypot — ADR-0016's deferred item) is therefore a prerequisite, not a
  follow-up, and the append-only rotation log makes any 2b re-bind detectable
  after the fact.
- **The panic-wipe stays one-way by design.** Recovery is an *opt-in* account
  action; a panic-wiped device with no re-login simply looks like a reporter who
  never came back. Adoption must never be automatic on key change, or it would
  defeat the panic-wipe.
- **Schema/flow work when built:** a pseudonym→keys one-to-many (a
  `device_keys` table or equivalent); an append-only `key_rotations` log (old key,
  new key, path 2a/2b, timestamp, optional steward sign-off); a device-side
  continuity-statement signer + a server verifier for the 2a path; an
  authenticated "adopt this device key" endpoint for 2b; and ADR-0012's counts
  widened to the key set. None of it is needed for the sandbox drill.
- **Readers see no change:** same `k-xxxx` handle, same track record, across a
  device rotation.

## Code state (2026-07-05)

**Not built — Proposed, deferred to the ADR-0011 gate.** The current code has the
opposite behaviour by construction: `register_or_get_pseudonym`
(`app/identity/signing.py`) is keyed solely on `public_key`, so a new key is
always a new pseudonym at rung 1, and there is no pseudonym→multiple-keys mapping
or adoption endpoint. The double-identity this ADR would promote to the recovery
anchor exists today only as the invisible JWT-account/pseudonym pair noted in
ADR-0016.

**For the drill, no code is needed:** it runs on the owner's phone with dummy
data. The mitigation is operational — **do not clear app data / uninstall during
the drill**, and if identity is lost, re-vouch the new pseudonym to rung 2 via
the ADR-0016 handle endpoint (`POST /moderation/pseudonyms/<handle>/rung`), as was
done for `k-0d241c76ea` on 2026-07-05.
