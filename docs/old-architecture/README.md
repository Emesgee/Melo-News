# Old Architecture (archived — superseded)

> ⚠️ **These documents describe a previous version of Melo-News that no longer
> exists in the codebase.** They are kept only for historical reference. Do not
> use them to understand the current system.
>
> **Current architecture:** [`../architecture.md`](../architecture.md)
> **Decision record for the change:** [`../adr/`](../adr/) — especially
> ADR-0002, ADR-0004, ADR-0017, ADR-0019, ADR-0020, ADR-0021.

## What's archived here

| File | Superseded by |
|---|---|
| `architecture.md`, `infra_overview.html` | [`../architecture.md`](../architecture.md) |
| `DEPLOYMENT_GUIDE.md`, `CI_CD_DEPLOYMENT_CHECKLIST.md` | [`../deploy.md`](../deploy.md) |

The deployment docs described a **GitHub Actions → DigitalOcean** staging/production
pipeline that does not match the current stack (a single Hetzner box running
`docker-compose.prod.yml`). There is no CI/CD today; deploys are manual. They
also reference `docker-compose.yaml` services (Kafka/Zookeeper) that no longer exist.

## What changed and why

The archived docs (`architecture.md`, `infra_overview.html`) describe Melo-News
as a **real-time news-aggregation platform**: a Kafka streaming pipeline fed by
**automated Telegram scraping** (Selenium/ChromeDriver), storing scraped
**stories** in Postgres, adding **AI summaries / news chat / city history**
(OpenAI + Anthropic + Thaura.ai), with media in **Azure Blob Storage**, deployed
on a **DigitalOcean** droplet.

The project has since pivoted completely. In summary:

| Old (archived here)                              | Now (current)                                                        | Decided by |
|--------------------------------------------------|----------------------------------------------------------------------|------------|
| Automated Telegram/Selenium scraping             | First-party citizen-journalism reports only (scrapers removed)       | ADR-0002   |
| Kafka streaming pipeline                          | Direct Flask ingest → geo/time clustering into Events                | ADR-0004   |
| `stories` as the primary unit                     | **Event** (incident) as the primary reader-facing unit               | ADR-0004   |
| AI summary / news chat / city history as the product | A **reader-side trust layer**: corroboration across independent sources | ADR-0019   |
| Azure Blob Storage                                | Hetzner (S3-compatible) object storage, private bucket + presigned URLs | ADR-0017   |
| DigitalOcean droplet                              | Container on a Hetzner host (nginx + Flask + Postgres)               | ADR-0017   |
| Web-only news reader                              | Web reader/moderation surface **+** Android signed-reporter client   | ADR-0007 / 0021 |

The "AI news aggregator" framing is gone. Melo's purpose is now: **help a lay
reader know which of tonight's many public posts is corroborated, by how many
independent sources, and how much to believe it** (ADR-0019). The engine that
does this — Events, the corroboration graph, the fake-independence detector,
archive-grade snapshots — is documented in [`../architecture.md`](../architecture.md).

_Archived 2026-07-17._
