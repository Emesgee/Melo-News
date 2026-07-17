# 0007. Web is a login-required unsigned lane; anonymity is owned by Android

- **Status:** Accepted
- **Date:** 2026-07-05
- **Deciders:** Project owner (submit-flow design interview, 2026-06-03)
- **Relates to:** ADR-0001, ADR-0003, ADR-0010

## Context

There are two client lanes with very different assurance. The browser cannot safely
hold a device keypair (browser key storage is fragile), cannot guarantee offline
capture, and a public no-account web ingest is the easiest Sybil/spam vector. The
Android app, by contrast, is offline-first and is where the on-device signing, EXIF
stripping, panic/decoy, and mesh relay live.

The first pilot (a scripted Tech-for-Palestine drill) has no real anonymous reporters
to serve — so a web anonymous path would be pure abuse surface with no upside.

## Decision

- **The web `/upload` page is login-required.** There is **no web anonymous path**
  for the pilot. Logged-out users see honest copy routing them to create an account or
  to the Android app — not a silent bounce to `/login`.
- **The web lane is unsigned** (email/password `registered` accounts). It is
  rung-eligible but never earns the tamper-evidence badge.
- **Anonymity and signing are Android's job.** The hardened, offline, signed tool owns
  the safety case; the `/anonymous-ingest` endpoint stays because Android uses it.
- Web submit contract: required = title + city + country; media, precise GPS pin,
  tags, subject, severity default all optional; severity is a segmented control; no AI
  authoring of the report's title/subject; honest pending-by-default post-submit copy.
- Revisit web anonymity only post-pilot, and only *with* abuse controls.

## Consequences

- Readers can and must distinguish signed (Android) from unsigned (web) reports.
- The web lane is deliberately lower-assurance; that is fine because it is not the
  product for at-risk field reporters.
- The honest logged-out routing depends on there actually being an Android
  distribution to point to (currently a TODO — no download link exists yet).

## Code state (2026-07-05)

**Built:** `/upload` is behind `PrivateRoute`; `UploadForm.js` renders a bilingual
`LoggedOutGate` (account CTA + Android-app section); `handleUploadClick` no longer
bounces to `/login`; post-submit copy reads `verification_status` and only claims
"published" when actually VERIFIED. The Android-app section carries a TODO — there is
no real APK/store link yet.
