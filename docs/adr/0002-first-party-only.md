# 0002. First-party citizen journalism only; scrapers and AI-intelligence features removed

- **Status:** Accepted
- **Date:** 2026-07-05
- **Deciders:** Project owner (design interviews, 2026-06-02/03)
- **Relates to:** ADR-0001

## Context

The original system ingested from automated scrapers (Telegram via Selenium, plus
RSS/Reddit adapters) through a Kafka pipeline, and layered "news-intelligence"
features on top: Predictions, a Tension Index, Keyword Trends, News Chat, City
History, and a Melo Summary. Several of these run an LLM over unverified single
reports and emit authoritative-sounding output.

Under ADR-0001 these are trust liabilities: a global "tension" score is false
precision and Sybil-gameable; an AI answering questions over one unverified report is
the highest hallucination risk on the platform; generative "history" over the most
contested geography on earth is a credibility landmine.

## Decision

- **Remove the scraping pipeline** (Telegram/RSS/Reddit adapters, Kafka, scheduler).
  The app ingests **only first-party reports** submitted through its own web and
  Android clients.
- **Hard-delete the AI-intelligence features**: Predictions, Tension Index, Keyword
  Trends, News Chat, City History, and the old Melo Summary. A git tag is the
  archive; no flag-gated dead code is kept (it is attack and maintenance surface).
- If a corroborated-events digest is ever wanted, it must summarize *verified Events*
  with attribution and hedging — a new thing, not the old Summary revived.

## Consequences

- The "empty map" problem: with scrapers gone, the map is only as full as real
  reporters make it. Launch is therefore a closed pilot in one region, not an open
  launch (see the pilot plan).
- Smaller, more defensible surface area; less to secure and maintain.
- `docs/architecture.md` (which still describes the scraper/Kafka/AI system) is stale
  and must not be trusted; it predates this decision.

## Code state (2026-07-05)

Scraper/Kafka code and the AI-intelligence features are removed from the working
tree. `docs/architecture.md` has **not** yet been rewritten and still documents the
deleted system — a known cleanup item.
