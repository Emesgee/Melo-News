# 0017. Media object storage is S3-compatible (Hetzner), not Azure

- **Status:** Accepted
- **Date:** 2026-07-05
- **Deciders:** Project owner + grill session, 2026-07-05
- **Relates to:** ADR-0007, ADR-0009, ADR-0015
- **Refines:** ADR-0009 (the storage backend behind the direct-upload model)

## Context

Media reaches storage via a **direct upload**: the server issues a short-lived
presigned URL and the phone PUTs the bytes straight to the store, so the API
server **never sees the media bytes** (ADR-0009). That property is the point —
not an implementation detail — because the threat model assumes the server can
be compromised or coerced.

The app was wired to **Azure Blob Storage** (SAS URLs). With the backend moving
to a **Hetzner** deployment, the question is whether to keep Azure or move
storage there too. The moment is ideal: **no media is stored yet** (media-token
returns 503, Azure was never configured), so switching costs a code change, not a
data migration.

## Decision

**Media object storage is S3-compatible and hosted alongside the Hetzner
deployment; the server issues S3 presigned PUT URLs instead of Azure SAS.**

- **Direct-upload preserved.** S3 presigned URLs give the exact same "phone →
  storage, server never sees the bytes" model as Azure SAS, so ADR-0009 is
  unchanged. The presigned URL is signed **without** a fixed Content-Type, so the
  client PUT is a plain PUT of the bytes.
- **No Android change; client stays backend-agnostic.** The app's PUT sends
  `x-ms-blob-type: BlockBlob`, which Azure *requires* and S3/Hetzner *ignores*
  (not an `x-amz-*` header, not part of the presigned signature). Keeping it means
  the same client works against either backend, and the **currently installed
  build can exercise the S3 media path with no rebuild**.
- **Backend is config-selected, not hard-coded.** `STORAGE_BACKEND` = `s3` |
  `azure`. Code supports both; the deployment chooses. Default stays `azure` so
  existing tests/deploys are unaffected; the Hetzner deploy sets `s3`.
- **Trust model untouched.** `media_sha256` (ADR-0015) is hashed from the
  sanitized bytes *before* upload, so signing/verification is identical
  regardless of backend.

### Why S3-on-Hetzner over Azure

1. **Jurisdiction fits the mission.** This is at-risk-reporter media. Azure is
   US-headquartered (US CLOUD Act reach, any region); Hetzner is EU (Germany/
   Finland), GDPR, no CLOUD Act exposure. Media *integrity* is anchored by the
   signature reader-side (ADR-0009), so the backend choice is purely about who
   can be compelled to surrender or seize the bytes — and EU is the safer default.
2. **One provider: simpler ops, cheaper egress**, one credential set, one network.
3. **Cheapest moment** — empty bucket, nothing to migrate.

### Sub-choice (deployment, not code)

Managed **Hetzner Object Storage** (S3-compatible) for least ops, or self-hosted
**MinIO** for media on disks you control. Start managed; move to MinIO only if
full disk sovereignty is wanted. Either is a config change (endpoint + keys).

## Consequences

- New `modules/s3_handler.py` (boto3 presigned PUT + server-side upload) and a
  `modules/object_storage.py` dispatcher; the media-token endpoint calls the
  dispatcher. `boto3` is a new dependency.
- **Android: unchanged.** The `x-ms-blob-type` header is retained (Azure needs it,
  S3 ignores it), so the client is backend-agnostic and the installed build works
  against S3 without a rebuild.
- Web/anonymous lane (ADR-0007, server-side EXIF-strip then upload) keeps its
  existing local-fallback path for now; it can adopt the S3 dispatcher next.
- Config: `S3_ENDPOINT_URL`, `S3_REGION`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`,
  `S3_SECRET_ACCESS_KEY`, optional `S3_PUBLIC_BASE_URL`, plus `STORAGE_BACKEND`.

## Code state (2026-07-05)

Being implemented in this change: `s3_handler` + dispatcher + endpoint switch +
Android header removal + a presign-structure unit test (boto3 signs locally, so
no live bucket needed to test the URL shape). End-to-end media-signing on-device
still needs a real Hetzner Object Storage bucket + keys in `.env` and
`STORAGE_BACKEND=s3`; until then the media-token endpoint returns 503 and reports
fall back to text-only.
