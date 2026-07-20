# Architecture Decision Records

This directory holds the **decision log** for Melo-News: why the system is the way it
is, one decision per file. If you are about to change how identity, trust,
corroboration, moderation, media handling, or reporter safety works — read the
relevant ADR first, and if you overturn it, add a new ADR that supersedes it
rather than editing the old one.

Why this exists: the design of the citizen-journalism trust model was worked out in
long design interviews and lived only in private notes plus a `docs/architecture.md`
that now describes a **deleted** system (Telegram scraping, Kafka, AI summaries).
ADRs put the *current* rationale under version control where it can't silently rot.

## Status legend

- **Accepted** — decided and reflected (fully or partly) in the code.
- **Proposed** — under active discussion; not yet ratified.
- **Superseded by NNNN** — replaced; kept for history.

Each ADR carries a **Code state** section: what is actually built vs. still
designed-only, as of the date noted. That is deliberate — these records double as an
honest map of the gap between the design and the implementation.

## Index

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-north-star-reader-trust.md) | North star: optimize for reader trust | Accepted |
| [0002](0002-first-party-only.md) | First-party citizen journalism only; scrapers and AI-intelligence features removed | Accepted |
| [0003](0003-pseudonymous-identity-device-keypair.md) | Pseudonymous identity anchored to a device keypair; no server credential store | Accepted |
| [0004](0004-event-primary-unit-corroboration.md) | The Event is the primary reader unit; corroboration counts distinct identities | Accepted |
| [0005](0005-rung-gate-and-safety-override.md) | Rung-based publication gate with a safety override | Accepted |
| [0006](0006-reader-trust-display-basis-not-binary.md) | Reader trust display shows the basis of trust, never a binary "verified" | Accepted |
| [0007](0007-web-login-required-anonymity-on-android.md) | Web is a login-required unsigned lane; anonymity is owned by Android | Accepted |
| [0008](0008-signature-scope.md) | A report signature covers the reporter's claims, including the media | Accepted |
| [0009](0009-reader-side-media-verification.md) | Media tamper-evidence is verified reader-side, not by the server | Accepted |
| [0010](0010-android-first-sequencing.md) | Build the Android app first, gated on a safety-hardening milestone | Proposed |
| [0011](0011-security-hardening-release-gate.md) | Encrypted local storage and Keystore-backed secrets are a hard release gate | Proposed |
| [0012](0012-track-record-computed-on-read.md) | Reporter track record is computed on read; the cohort is hand-vouched for the drill | Accepted |
| [0013](0013-signing-key-p256-hardware-backed.md) | The report-signing key is P-256 in the Android Keystore, not software Ed25519 | Accepted |
| [0014](0014-canonical-signing-message.md) | Canonical signing message: every signed value is a string or null; the client is the sole formatter | Accepted |
| [0015](0015-signing-slice-first-cut.md) | Signing-slice first cut: sign the full ADR-0008 envelope now; defer reader-side verification | Accepted |
| [0016](0016-drill-identity-and-rung-bootstrap.md) | Drill identity: signature is the reporter of record behind a JWT turnstile; cohort bootstrapped to rung 2 in setup | Accepted |
| [0017](0017-object-storage-hetzner-s3.md) | Media object storage is S3-compatible (Hetzner), not Azure | Accepted |
| [0018](0018-identity-recovery-account-adoption.md) | Reporter-identity recovery is account-adoption of a rotated device key, not a key backup | Proposed |
| [0019](0019-purpose-reader-side-trust-layer.md) | Melo's purpose is a reader-side trust layer over public conflict content; capture/signing demoted to an optional provenance tier | Proposed |
| [0020](0020-strategy-sequencing-one-engine-three-shapes.md) | Strategy sequencing: one engine, three shapes (trust layer / debunk / archive), the drill is the branch point | Proposed |
| [0021](0021-android-reporter-first-reader-on-web.md) | Android is reporter-first; the reader surface lives on the web; Android carries only a thin, decoy-gated awareness layer | Proposed |
| [0022](0022-volunteer-carrier-network-sealed-relay-only.md) | Non-reporters may carry reporters' data only as sealed, transit-only middle relays — the current plaintext mesh must not ship to volunteers | Proposed |
| [0023](0023-steward-quorum-for-high-impact-governance.md) | High-impact steward actions (mint privileged roles, vouch to rung 2/3) require an M-of-N quorum; the audit log is the substrate, not the safeguard | Proposed |

## Writing a new one

Copy [`0000-template.md`](0000-template.md), take the next number, fill it in, add a
row above. Keep it short — context, the decision, the consequences you accept, and
what the code actually does today.
