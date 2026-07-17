# Architecture & Technology

> **Scope of this document.** This describes the system as it exists on the
> `citizen-journalism-trust-model` line of work (2026-07-17). It supersedes the
> pre-pivot "news aggregator" architecture, which is archived under
> [`old-architecture/`](old-architecture/). The authoritative decisions behind
> everything here live in the Architecture Decision Records, [`adr/`](adr/) —
> this document is a map of them, not a replacement.
>
> Where a component is **not yet built**, it says so. The ADRs are explicit
> about built-vs-proposed and this document keeps that honesty.

## 1. What Melo-News is

Melo-News is a **reader-side trust layer for conflict content** (ADR-0019). Its
job is the reader's *"should I believe this?"* moment: given many posts about an
incident, show which one is **corroborated**, by **how many independent
sources**, and render that as a **non-binary "basis of trust"** a lay reader can
actually read (ADR-0001, ADR-0006).

It is **not** a scraper, an AI news summariser, or a single-item provenance tool.
The competitive analysis (ADR-0019) found that capture, metadata-stripping,
blackout transport, and single-item cryptographic provenance are already owned by
better-resourced tools (Tella, eyeWitness, ProofMode, C2PA), and distribution is
owned by the social platforms. The one unclaimed cell is **stages 6→7**: turning
already-public content into *corroborated events a lay public can trust, at feed
speed*. That is the whole product.

### One engine, three shapes (ADR-0020)

The same corroboration engine and data model support three product shapes; the
pilot decides which leads:

1. **Reader-side trust layer** — corroboration → lay-legible basis of trust (the consumer bet, ADR-0019).
2. **Debunk / independence-integrity engine** — the same engine run in reverse to flag *fake independence* (reshares/astroturf).
3. **Capture-before-deletion archive** — the corroboration graph, byte-preserved, as an accountability asset for courts/Mnemonic/eyeWitness.

They share one Event, one set of sources-with-provenance-tiers, and one graph of
independent-source relationships. The codebase builds that shared core **once**
(Phase 1) and defers the shape-specific surfaces behind the pilot.

## 2. System overview

```
                          READERS (the mass audience)
                                    │  HTTPS
                                    ▼
   ┌──────────────────────────────────────────────────────────────┐
   │                     Web surface (React SPA)                    │
   │   Map / List of EVENTS · Event detail · Moderation queue       │
   │   Reader = login-free browse · Reporter/mod = login (ADR-0007) │
   └──────────────────────────────────────────────────────────────┘
                                    │  REST /api/*
                                    ▼
   ┌──────────────────────────────────────────────────────────────┐
   │                    Flask backend (app factory)                 │
   │  Blueprints: auth · profile · file_upload · search · story     │
   │  · moderation · events · ai · templates · output               │
   │                                                                │
   │   ┌────────────────────────────────────────────────────────┐  │
   │   │        TRUST ENGINE  (app/events/, app/story/)          │  │
   │   │  cluster reports → Event · recompute_event              │  │
   │   │  independence (union-find over identities)              │  │
   │   │  corroboration graph · archive-grade snapshots          │  │
   │   └────────────────────────────────────────────────────────┘  │
   └──────────────────────────────────────────────────────────────┘
            │                      │                       │
            ▼                      ▼                       ▼
   ┌────────────────┐    ┌──────────────────┐    ┌──────────────────┐
   │  PostgreSQL    │    │ Object storage   │    │  Android client  │
   │  (SQLAlchemy)  │    │ Hetzner S3 /     │    │  (Kotlin)        │
   │  users, events,│    │ Azure (ADR-0017) │    │  SIGNED reporter │
   │  file_uploads, │    │ private bucket,  │    │  lane (Lane B)   │
   │  snapshots     │    │ presigned PUT/GET│    │  ADR-0013/0021   │
   └────────────────┘    └──────────────────┘    └──────────────────┘
```

### Two input lanes, one Event (ADR-0019 §2)

- **Lane B — signed client report (BUILT).** The Android app captures a report,
  signs it on-device (ECDSA P-256, AndroidKeyStore — ADR-0013), and uploads media
  directly to object storage via a presigned URL. This is the **"verified
  source"** premium tier: provably unaltered, cryptographically distinct identity,
  track record. The web `/upload` page is a login-required *unsigned* variant of
  the same lane (ADR-0007).
- **Lane A — already-public post (NOT BUILT).** Ingesting a public Telegram/X post
  (reporter-pasted link or monitored channel), geolocating, timestamping, and
  content-matching it into an Event as a lower-tier **"public source"**. This is
  the mass-audience path but is **deferred behind the pilot** (ADR-0020 Phase 2) —
  there is no Lane A code today.

A reader is meant to see *"N sources: X verified, Y public"* — honest about which
is which, degrading gracefully between tiers.

## 3. The trust engine (the core)

This is Melo's only defensible territory, so it is the part to understand first.
It lives in `app/events/` and `app/story/`.

### 3.1 The Event is the unit (ADR-0004)

A raw report is a `FileUpload` row. The **reader never sees raw reports as the
primary unit** — reports cluster into an **`Event`** (an incident) by geography +
time (`EVENT_CLUSTER_RADIUS_KM`, `EVENT_CLUSTER_WINDOW_HOURS` in `config.py`). A
new report auto-creates a singleton Event of one; subsequent nearby reports join
it. One incident = one Event = one map pin = one shareable `/events/:id` page.

### 3.2 Corroboration vs. independence (ADR-0006, ADR-0020 Phase 1)

An Event carries two counts, and the distinction is load-bearing:

- **`corroboration_count`** — `COUNT(DISTINCT user_id)` over VERIFIED, non-anonymous
  members. Anonymous members count 0 toward the threshold.
- **`independent_source_count`** — distinct identities **after collapsing
  byte-identical media to a single origin**. This is the **fake-independence
  detector**: two people filming the same event produce *different* SHA-256s and
  count separately; one clip reposted under many pseudonyms collapses to *one*
  origin (a reshare/astroturf, not corroboration). It is computed by a **union-find
  over people** in `app/events/service.py` — identities that share a
  `media_sha256` are merged. It is always `≤ corroboration_count`, so gating on it
  is strictly more conservative.

`independent_source_count` is the number the **CORROBORATED gate** and the reader
display trust. Promotion to CORROBORATED also requires a **rung-2+ member present**
(ADR-0005), so a flood of fresh rung-1 keys cannot self-promote (Sybil backstop).

### 3.3 Derived status

`Event.status ∈ { DEVELOPING, CORROBORATED, DISPUTED, CLOSED }` is a **derived
function** of members + verifications, computed by `recompute_event()`. A
moderator can pin it with a sticky `status_override`. Status colours the map pin
and the reader trust badge.

### 3.4 Corroboration graph + archive-grade snapshots (ADR-0020 Phase 1)

- `app/events/archive.py :: build_event_graph()` emits a **deterministic,
  privacy-preserving** (never a raw `user_id`), **hashable** (`graph_sha256`)
  provenance record for an Event: per source — pseudonym, provenance tier, media
  fingerprint, independence role, plus reshare clusters. Served at
  `GET /api/events/<id>/graph`.
- On the moment an Event first enters an archival status
  (CORROBORATED/DISPUTED/CLOSED), `recompute_event` writes an append-only,
  content-addressed **`EventGraphSnapshot`** (deduped by hash) — capture-before-
  deletion (UC9). History at `GET /api/events/<id>/snapshots`.

### 3.5 Advisory coordination signals (ADR-0020 Phase 1)

`app/events/independence.py :: analyze_independence()` flags **text
near-duplication** (Jaccard over 3-word shingles) and **synchronized submission**
(tight-window bursts across identities). These are **advisory only** — they never
reduce the corroboration count, because for text/timing the same pattern also
marks *genuine* corroboration (independent witnesses of one event naturally submit
around the same time and describe it similarly). Only byte-identical **media**
collapses the hard count.

> **Deferred, on purpose (ADR-0020):** (1) *byte-capturing, not link-storing* —
> snapshots preserve state + hashes, but media is still a storage key; full UC9
> capture needs the bytes (infra-heavy, coupled to the UC7 jurisdiction decision).
> (2) *perceptual (near-duplicate) media hashing* — the server never sees media
> bytes (ADR-0009), so this needs an on-device perceptual hash in the signed
> envelope. (3) *stored `verified/public` provenance tier* — waits for Lane A.

## 4. Identity, signing & trust ladder

- **Pseudonymous identity = a device keypair** (ADR-0003, ADR-0013). The device
  **ECDSA P-256 public key IS the pseudonym** (AndroidKeyStore, hardware-backed),
  stored base64-SPKI. There is no email/password for a reporter; a fresh key
  self-registers on its first signed report. Web accounts are the `registered`
  identity type (email/password); device identities are `pseudonymous`.
- **Signature scope & canonical message** (ADR-0008, ADR-0014). The signed payload
  is a compact sorted-key JSON persisted verbatim (`FileUpload.signed_message`), so
  **reader-side verification** (ADR-0009) can rebuild the byte-identical input.
- **JWT is only a turnstile** (ADR-0016). The signature is the real identity; the
  JWT just gates the ingest endpoint. Access-token lifetime is a long 30 days by
  default (a field reporter is often offline) — acceptable because token-at-rest
  hardening is ADR-0011's job.
- **Trust ladder** (ADR-0005, ADR-0012). `User.trust_rung` 1..3 (0 = anonymous,
  no `User` row). A fresh key starts at rung 1 and earns nothing automatically;
  only corroborated history + time, or a steward vouch, climbs it. Track record
  (`reports_count`, `corroborated_count`) is computed on read (ADR-0012).
- **Roles** replace an old boolean: `reporter` (default), `moderator` (reviews the
  verification queue / event status), `steward` (M-of-N governance, also
  moderator-capable).

## 5. Clients

### 5.1 Web — the reader + moderation surface (ADR-0007, ADR-0021)

`app/frontend/` — React 18 (CRA). The web is the **primary product surface**: it
reaches the mass audience with no install and is where the UC4 belief question is
actually tested.

- **Reader:** a single screen toggling **Map ↔ List of Events**
  (`components/leafletMap/MapArea.js` — react-leaflet + marker clustering, one
  status-coloured pin per Event, click-to-zoom incident list; `pages/EventsFeed.js`,
  `pages/EventDetail.js`). Trust display in `components/trust/TrustUI.js`
  (corroboration count leading with the *independent* number, status badge,
  reporter track-record chip). Reader browse is login-free.
- **Reporter/moderator:** login-required. `/upload` is the unsigned web report
  lane; `pages/Moderation.js` is the verification queue (inline media review).

### 5.2 Android — reporter-first (ADR-0010, ADR-0013, ADR-0021)

`android/` — Kotlin (Retrofit, osmdroid, DataStore, AndroidKeyStore). The app's
defensible reason to exist is the **hardened signed capture path** (Lane B):
on-device signing, EXIF strip, offline queue, panic-wipe, decoy mode, mesh relay
(`security/`, `sync/`, `mesh/`).

**Boundary (ADR-0021):** Android is reporter-first and carries only a **thin,
decoy-gated awareness layer** — the reporter's own track record, a compromise
alert on their pseudonym (ADR-0018), and a light situational-awareness event map
(`ui/map/`, one mark per Event via `GET /api/events`). It must **not** grow into a
full reader browser; that belongs on the web. Rationale: the reporter's phone is
the highest-risk object in the system (seizure at a checkpoint), so it should hold
the minimum.

## 6. Backend structure

Flask **app-factory** (`app/__init__.py :: create_app`) with `ensure_schema_
compatibility` self-healing (adds new columns / backfills derived counts on live
DBs so deploys don't go dark). Blueprints:

| Blueprint      | Prefix          | Responsibility                                   |
|----------------|-----------------|--------------------------------------------------|
| `auth`         | `/api/auth`     | Login / registration / JWT turnstile             |
| `profile`      | `/api/profile`  | Reporter profile & track record                  |
| `file_upload`  | (root)          | Media presigned-URL issue + report create        |
| `file_types`   | (root)          | Allowed upload types                             |
| `story`        | (root)          | Ingest (`/api/stories/ingest`), report serialize |
| `moderation`   | (root)          | Verification queue, status override              |
| `events`       | (root)          | Event feed, detail, `graph`, `snapshots`         |
| `search`       | `/api`          | Geo/text search over Events                      |
| `ai`           | `/api/ai`       | (Legacy/optional AI helpers — not the product)   |
| `templates`    | `/api`          | Input/output templates                           |
| `output`       | (root)          | Export/output                                    |

Key data model (`app/models.py`): **`User`** (pseudonymous identity, trust ladder),
**`FileUpload`** (a report/Event member — carries `media_sha256`,
`report_signature`, `signed_message`, `verification_status`, `event_id`),
**`Event`** (the reader unit — `status`, `corroboration_count`,
`independent_source_count`, `status_override`), **`EventGraphSnapshot`**
(append-only content-addressed provenance capture), plus `FileType`, `Search`,
templates.

## 7. Storage & infrastructure (ADR-0017)

- **Object storage:** media is uploaded **directly** by the client to an
  S3-compatible **private bucket** (Hetzner Object Storage) via **presigned PUT**;
  readers get short-lived **presigned GET** URLs (`MEDIA_READ_URL_TTL_MINUTES`,
  default 60). The server never proxies media bytes. `STORAGE_BACKEND` selects
  `s3` (Hetzner/MinIO — `modules/s3_handler.py`) or `azure` (legacy —
  `modules/azure_handler.py`); the abstraction is `modules/object_storage.py`.
- **Database:** PostgreSQL via SQLAlchemy (connection pool pre-ping / recycle in
  `config.py`).
- **Deployment:** containerised (`Dockerfile`, `docker-compose.yaml`,
  `docker-compose.prod.yml`) behind **nginx** (`nginx.conf`) as reverse proxy, on a
  Hetzner host. Dev connectivity for the phone during the drill is over Tailscale.
  Entry point `main.py`, config `config.py` (`ENVIRONMENT` = development|production).

## 8. Security posture — read this before calling it safe

> **Hard release gate (ADR-0011).** Real at-rest encryption, Keystore-backed
> secrets, and signature-only auth are a **hard-blocking gate before any real
> at-risk reporter uses the app**. Today that layer is **stubbed**. The app must
> **not** be presented as safe for real reporters (e.g. Palestinian field
> journalists) until ADR-0011 is done.

- The current pilot runs on **signed pseudonyms with a dummy cohort** (ADR-0016) —
  the drill, not a live at-risk deployment.
- **Anonymous public ingest is DISABLED for the pilot** (`ANONYMOUS_INGEST_ENABLED
  = false`, ADR-0007): it is the easiest Sybil/spam vector, adds nothing to the
  scripted drill, and anonymous reports count 0 toward corroboration anyway.
  Re-enable post-pilot only with real anti-abuse (device attestation / PoW).
- Passwords (web accounts) are hashed — irrecoverable, only resettable.
- **De-risked for the mass case by ADR-0019:** Lane A public-post readers never
  install a capture client, so there is no on-device identity or cleartext store to
  seize. ADR-0011 remains a hard gate for the Lane B premium tier.

## 9. Build sequence & where we are (ADR-0020)

- **Phase 0 — the drill (current).** Scripted T4P corroboration exercise on the
  Lane-B signing path, re-scoped to **falsify** the UC4 belief-change hypothesis on
  a skeptical, non-aligned reader (`docs/pilot/`). This gates everything after it.
- **Phase 1 — no-regret core (BUILT, 135 tests green).** The archive-grade
  corroboration data model, fake-independence detector, corroboration graph,
  durable snapshots, advisory coordination signals — §3 above.
- **Phase 2 — branch on the drill result (NOT started).** If belief-change is
  strong → lead with the reader trust layer (build **Lane A ingest** + graded
  feed). If weak/backfires → shift emphasis to the archive and/or debunk shapes.
- **Phase 3 — per-surface hardening (NOT started).** ADR-0011 before any real
  Lane-B reporter; moderation-at-scale (UC6) + takedown/jurisdiction (UC7) scoping
  before any public Lane-A launch.

## 10. Where the decisions live

The ADRs in [`adr/`](adr/) are canonical; this document summarises them. Most
load-bearing for the architecture:

- **0001** North star: reader trust · **0002** First-party only (scrapers removed)
- **0004** Event as primary unit + corroboration · **0006** Non-binary basis of trust
- **0005** Rung gate + safety override · **0007** Web=reader / Android=reporter lanes
- **0009** Reader-side media verification · **0011** Security-hardening release gate
- **0013** P-256 hardware-backed signing · **0014** Canonical signing message
- **0016** Drill identity/rung bootstrap · **0017** Hetzner S3 object storage
- **0019** Purpose = reader-side trust layer · **0020** One engine, three shapes
- **0021** Android reporter-first, reader on web
