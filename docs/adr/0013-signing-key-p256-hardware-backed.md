# 0013. The report-signing key is P-256 in the Android Keystore, not software Ed25519

- **Status:** Accepted
- **Date:** 2026-07-05
- **Deciders:** Project owner + grill session, 2026-07-05
- **Relates to:** ADR-0003, ADR-0008, ADR-0009, ADR-0010, ADR-0011
- **Refines:** ADR-0003 (the *algorithm* of the device keypair; the pseudonym-from-
  keypair model is unchanged)

## Context

ADR-0003 anchors a reporter's pseudonym to a device-held keypair, and the server
half (`app/identity/signing.py`) was written to verify **Ed25519** with a
docstring claiming the key is "born on-device (Android Keystore)." Designing the
Android signing slice (ADR-0010's next task) exposed that this pairing is not
buildable as described:

- **AndroidKeyStore cannot hold an Ed25519 key.** It hardware-backs RSA and
  NIST-curve EC only. An Ed25519 key would therefore be an ordinary **software
  key in app storage**, whose at-rest safety depends on the encrypted-storage
  work in ADR-0011 that is currently a stub. It would also require bundling a
  crypto library (Tink/BouncyCastle), because platform Ed25519 exists only from
  API 33 and the app floor is `minSdk 26`.
- The app's own stated primary threat is **device seizure** (ADR-0011). A key
  that can be copied off a seized (even imaged) device is materially weaker than
  one that physically cannot leave the secure element.

There are **zero signing clients today**, and the server is about to be deployed
to a public Hetzner host. A signature scheme cannot be migrated later without
invalidating every pseudonym bound to it, so the deploy is effectively the
freeze point — this is the last moment the choice is free.

## Decision

**The report-signing key is an ECDSA P-256 keypair generated in and held by the
AndroidKeyStore (TEE, or StrongBox where available); the public key is the
pseudonym. The server verifies ECDSA-P256, not Ed25519.**

- **Private key is non-extractable.** It is generated inside the secure element
  (`KeyPairGenerator` with the `AndroidKeyStore` provider) and never exists in
  app memory or storage. A seized device cannot export it. This removes the
  key-at-rest problem entirely, so the signing slice does **not** block on the
  ADR-0011 encrypted-storage work.
- **No new crypto dependency on Android.** Pure platform API, available well
  below `minSdk 26`. (This addresses the ADR-0009 note that no client does
  crypto — the *signing* client uses only the platform; reader-side
  *verification* is still separate.)
- **Server change (must land in the Hetzner deploy).** `app/identity/signing.py`
  swaps `Ed25519PublicKey.verify` for EC P-256 / ECDSA verification via the same
  `cryptography` package. The canonical-message construction and the
  self-registration flow are unchanged. `derive_handle` still hashes the public
  key, so the pseudonym ergonomics are identical (the P-256 key is larger; the
  `k-xxxx` handle is not).
- **Transport is HTTPS on deploy.** The signature protects report integrity only;
  the JWT and payload still travel in the clear without TLS. The Hetzner deploy
  moves the client base URL from `http://<tailscale-ip>:5000` to `https://…` with
  a real certificate. Signed-but-plaintext is out of scope as "secure."

## Consequences

- **Seizure resistance by construction:** stealing the identity key off a device
  is not possible, independent of whether ADR-0011's DB encryption is done yet.
- **One-time, pre-deploy server rewrite** of the verify path, plus the public-key
  encoding change (a P-256 point, not a 32-byte Ed25519 key). Handle derivation,
  storage columns, and the ingest wiring are untouched.
- Hardware backing stops key **theft**, not **coerced signing** on an unlocked
  device; and report data at rest is still ADR-0011's job. This ADR is
  specifically about "can the identity key be stolen" — where hardware wins.
- ECDSA signatures are non-deterministic and DER-encoded (variable length); the
  server verifies DER as produced by AndroidKeyStore. Acceptable.
- ADR-0003's "Ed25519 / Android Keystore" phrasing is corrected by this ADR;
  ADR-0008's signed-field set is unaffected (scheme changes, not the covered
  fields).
- Optional hardening deferred: `setUserAuthenticationRequired` (biometric/PIN per
  signature) is too heavy for the sandbox drill; revisit under ADR-0011.

## Code state (2026-07-05)

**Server half done.** `signing.py` now verifies **ECDSA-P256/SHA-256**: it loads
the public key as base64 SPKI DER (`load_der_public_key`), checks the curve is
SECP256R1, and verifies the DER signature. Tests migrated to P-256 keys
(`test_signing.py`), all green. **Client half absent:** Android still has no
keypair, no keystore usage, and sends no `public_key`/`signature` — that is the
ADR-0010 signing slice. Deploy checklist item still open: HTTPS base URL.
