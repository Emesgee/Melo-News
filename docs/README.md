# Documentation Index

Welcome to Melo-News documentation! This index will help you find what you need.

> **Melo-News is a reader-side trust layer for conflict content** (ADR-0019): it
> shows a lay reader which of tonight's many public posts is **corroborated**, by
> **how many independent sources**. It is *not* a scraper or an AI news
> summariser — that was a previous version, now archived under
> [`old-architecture/`](old-architecture/).

## 🚀 Getting Started

- **[User Guide](USER_GUIDE.md)** - How to use the Melo-News app
- **[Installation Guide](../INSTALLATION.md)** - Setup for Docker and development
- **[README](../README.md)** - Project overview and quick start
- **[Contributing Guide](../CONTRIBUTING.md)** - How to contribute to the project

## 📚 Technical Documentation

### Core Architecture
- **[Architecture Overview](architecture.md)** — current system design (the trust engine, two lanes, clients, storage, security posture)
- **[Architecture Decision Records](adr/)** — the canonical decisions; `architecture.md` is a map of these
- **[API Reference](api-reference.md)** — REST API documentation ⚠️ _may be partly stale; the Events/trust endpoints in `architecture.md` §3 & §6 are authoritative_

### Pilot
- **[Pilot / drill protocol](pilot/)** — the scripted T4P corroboration drill (Phase 0)

### Legacy feature docs (pre-pivot — kept for history, no longer the product)
- **[Data Sources](features/data-sources.md)** — ⚠️ describes the removed Telegram scraping pipeline (superseded by first-party reports, ADR-0002)
- **[Melo Summary](features/melo-summary.md)**, **[News Chat](features/news-chat.md)**, **[City History](features/city-history.md)** — ⚠️ AI features from the aggregator era; not the current product (ADR-0019)

## 🛠️ Development — quick reference

- **Backend**: Python / Flask (app-factory + blueprints) with PostgreSQL (SQLAlchemy)
- **Frontend**: React 18 — the reader + moderation surface (Map/List of Events)
- **Mobile**: Kotlin Android — the signed reporter lane (Lane B)
- **Storage**: S3-compatible object storage (Hetzner), private bucket + presigned URLs (ADR-0017)
- **Trust engine**: Event clustering → `recompute_event` → fake-independence detector → corroboration graph → durable snapshots (`app/events/`)
- **Deployment**: Docker Compose behind nginx on a Hetzner host

### Key components
```
app/
├── __init__.py         # Flask app factory (+ schema self-heal)
├── models.py           # User · FileUpload · Event · EventGraphSnapshot
├── events/             # THE TRUST ENGINE (service, independence, archive, routes)
├── story/              # report ingest + serialization
├── moderation/         # verification queue
└── frontend/src/       # React reader + moderation web app
android/                # Kotlin signed-reporter client (Lane B)
```

## 🌐 External Resources

- **[PostgreSQL Documentation](https://www.postgresql.org/docs/)** - Database reference
- **[React Documentation](https://react.dev/)** - Frontend framework
- **[Leaflet Documentation](https://leafletjs.com/)** - Mapping library

## ❓ Need Help?

1. **First time?** Start with [Installation Guide](../INSTALLATION.md)
2. **Developers?** Read [Architecture Overview](architecture.md), then the [ADRs](adr/)
3. **Why did it change from a news aggregator?** See [`old-architecture/`](old-architecture/) and ADR-0019
4. **Contributing?** Read [Contributing Guide](../CONTRIBUTING.md)

## 📄 License

This project is licensed under the MIT License - see [LICENSE](../LICENSE) for details.

---

🇵🇸 **Built for Palestinian liberation and community empowerment**
