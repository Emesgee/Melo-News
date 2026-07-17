# 0011. Encrypted local storage and Keystore-backed secrets are a hard release gate

- **Status:** Proposed
- **Date:** 2026-07-05
- **Deciders:** Project owner + grill session, 2026-07-05 (in progress)
- **Relates to:** ADR-0003, ADR-0010

## Context

For a reporter in a hostile environment, **device seizure is a primary threat**, and
seizure can mean physical danger. The Android app presents itself as hardened —
docstrings describe an encrypted (SQLCipher) database, Keystore-backed panic PINs, and
a panic action that "destroys the passphrase, making the database permanently
unreadable."

A code audit (2026-07-05) found these protections are **largely not implemented**:

- `DatabaseKeyManager` is a 14-line stub — no key generation, no SQLCipher, no
  Keystore. The Room database is built **plain and unencrypted** with
  `fallbackToDestructiveMigration()`.
- Panic PINs are stored in **cleartext** `SharedPreferences` (`MODE_PRIVATE`), not the
  `EncryptedSharedPreferences` the docstring claims.
- The JWT is stored in a **plain, unencrypted** DataStore.
- No `AndroidKeyStore` usage exists anywhere in the app.

Consequence: if a device is seized **before** the reporter triggers panic-wipe, the
unencrypted database (PENDING reports, drafts) and the JWT are readable in cleartext.
The panic-wipe "destroy the key" story is hollow because there is no key and the data
was never encrypted. Worse, the docstrings give trainers and reporters a **false
sense of safety**.

## Decision (proposed)

**No real reporter uses the app until the local-storage security is real.** The
release gate for any real-reporter use (ADR-0010 step 2) includes at minimum:

- **Encrypted local database** (e.g. SQLCipher) with the key held in the
  `AndroidKeyStore`, so at-rest data is unreadable without the device unlocked.
- **Keystore-backed secrets** for the JWT and any panic/decoy PIN — no cleartext
  prefs.
- **Panic-wipe that is meaningful** given real encryption (destroying the Keystore key
  renders the DB unrecoverable, as advertised).
- **Docstrings corrected** so no claim outruns the implementation — a false safety
  claim is itself a safety defect.
- Decide the **on-device-sanitizer-only gap**: authenticated Android media is
  SAS-direct and never server-sanitized, so a MediaSanitizer fallback-to-raw leaks
  EXIF GPS. Either fail closed (block upload if sanitization fails) or add a
  verification step.

## Open questions (to resolve before Accepted)

- Full list vs. a minimum viable subset for the *closed* pilot (known, trained
  testers on controlled devices) vs. a wider release.
- Is fail-closed acceptable for media sanitization (drop the report) vs. degrade?
- Threat-model scope: at-rest only, or also duress/coercion (the decoy path already
  exists and is a good foundation).

## Consequences

- Real hardening work (SQLCipher + Keystore integration) lands before any real report,
  which is the correct ordering for an irreversible risk — but it is real effort.
- Until then the app is fine for **sandbox/test use with dummy data only**.
- As of 2026-07-05 the app is installed **only on the project owner's own phone** — no
  reporter is exposed today. This ADR therefore gates *expansion to anyone else*, and
  is not blocking the next milestone (the sandbox T4P drill, ADR-0010).

## Code state (2026-07-05)

As described in Context — stubbed. Real and working today: the panic-wipe *gesture*
and row/file deletion, decoy mode wired into submit+map, on-device `MediaSanitizer`,
and a random 30s–5min transmit delay against timing correlation. The encryption layer
those depend on for their advertised guarantees does not exist yet.
