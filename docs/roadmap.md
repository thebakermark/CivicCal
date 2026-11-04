# CivicCal Roadmap

## Mission

CivicCal is community information infrastructure for collecting publicly useful local events from independent organizations, preserving their source context, and distributing them through standard calendar and developer interfaces.

It is not limited to a consumer-facing calendar website. Its primary product is a dependable, reusable event catalog and subscription service.

## Product principles

- Broad community coverage: schools, local government, park districts, libraries, nonprofits, civic groups, youth organizations, faith communities, clubs, and other public-interest sources.
- Preserve what publishers actually say. Do not invent dates, times, locations, fees, eligibility, or registration details.
- Keep source provenance and change history.
- Missing from a later capture does not automatically mean cancelled.
- Do not silently merge or delete possible duplicates.
- Deterministic processing; no LLM in eligibility gates, event identity, or publication decisions.
- Free/self-hostable core, portable across Linux hosts, with replaceable storage and delivery components.
- Public read access to published information; administrative controls for source management and review.
- No deployment, automatic polling, or external service dependency is implied by this roadmap.

## End-to-end lifecycle

1. Discover an organization and its public event sources.
2. Register the source, its format, URL, scope, timezone policy, and operational settings.
3. Capture source content politely and reproducibly.
4. Archive the raw response and capture metadata.
5. Parse source-specific content into source observations.
6. Normalize observations into the CivicCal event model without losing original values.
7. Reconcile observations with prior events and revisions.
8. Store events, source relationships, revisions, and review candidates.
9. Publish approved records through JSON APIs and iCalendar feeds.
10. Notify opted-in webhook subscribers of meaningful changes.
11. Monitor source health, delivery health, data quality, backups, and restore capability.

## Phases and completion criteria

### 0. Blueprint and reuse assessment
- Document source lifecycle, event model, processing, storage, API, ICS, webhooks, operations, and reuse strategy.
- Inspect candidate projects' code, tests, dependencies, licenses, and architecture before copying code.
- Record decisions and unresolved questions.

**Complete when:** the architecture documents agree on terminology, boundaries, interfaces, and an implementable first release.

### 1. Source registry and onboarding
- Define source types and stable source identifiers.
- Record publisher, source URL, organization, geographic scope, content type, timezone policy, polling policy, access/consent flags where applicable, and review status.
- Validate registry records and document source onboarding.
- Keep source discovery separate from source activation.

**Complete when:** every initial Mokena-area source has a traceable registry entry and an explicit operational status.

### 2. Capture engine
- Implement reusable fetchers for ICS, HTTP pages, JSON APIs, RSS/Atom, and source-specific adapters.
- Support conditional requests (ETag, Last-Modified), timeouts, size limits, redirect controls, rate limits, jitter, retries, and backoff.
- Save raw payloads and response metadata.
- Make manual capture possible independently of scheduled polling.

**Complete when:** a capture run is repeatable, auditable, bounded, and cannot silently bypass source settings.

### 3. Parsing and normalization
- Parse ICS, JSON-LD Event, RSS/Atom, JSON APIs, and adapter-specific HTML.
- Preserve original text and source values alongside normalized fields.
- Handle timezones, floating times, all-day events, recurrence, exceptions, cancellations, and registration deadlines.
- Emit structured warnings instead of guessing.

**Complete when:** representative source fixtures normalize consistently and timezone/recurrence tests pass.

### 4. Identity, reconciliation, and quality
- Define source-event identity and CivicCal event identity.
- Track observations, revisions, cancellations, missing observations, and duplicate candidates.
- Add deterministic matching and human review where confidence is insufficient.
- Never equate disappearance with cancellation.

**Complete when:** repeated captures are idempotent and every material change is explainable from source observations.

### 5. Storage
- Start with SQLite behind a repository/storage interface.
- Store organizations, sources, captures, raw payload references, source events, canonical events, event-source links, revisions, duplicate candidates, and audit records.
- Plan migrations and a documented PostgreSQL path without requiring it for the initial core.
- Define retention and backup policies.

**Complete when:** a clean install can initialize, ingest fixtures, query history, back up, and restore.

### 6. Public JSON API
- Define versioned, read-only endpoints.
- Support date ranges, geography, organization, source, category, text search, pagination, and incremental change queries.
- Publish OpenAPI documentation and consistent error responses.
- Add caching and validators.

**Complete when:** an independent client can discover and retrieve events using only the published API contract.

### 7. iCalendar distribution
- Generate valid RFC 5545 feeds with stable UIDs and correct update/cancellation semantics.
- Offer community-wide, organization-specific, source-specific, and curated filtered feeds. Organization membership is derived from source registry ownership; see [organization subscription model](organization-calendar-subscriptions.md).
- Include feed caching and stable subscription URLs.
- Validate generated feeds with independent calendar parsers.

**Complete when:** Apple Calendar, Google Calendar, Outlook, and common ICS validators can subscribe and receive updates without duplicate churn.

### 8. Webhooks and integrations
- Define event-change notifications using a documented envelope (CloudEvents is the preferred starting point).
- Support subscriber registration, secret rotation, signed requests, retries, delivery logs, and disable/delete controls.
- Keep webhooks optional; feeds and API remain independently useful.

**Complete when:** a test receiver can reliably process create/update/cancel notifications and recover from failed delivery.

### 9. Operations and reliability
- Add source-health status, ingestion run history, structured logs, metrics, alertable failures, backup/restore checks, and security review.
- Keep scheduling simple (systemd timer or cron invoking a worker that exits).
- Avoid mandatory Redis, Celery, paid workflow platforms, or hosted AI.

**Complete when:** an operator can identify broken sources, recover a failed run, and restore the service from backup.

### 10. Local launch and expansion
- Validate coverage and accuracy for Mokena SD 159, Summit Hill SD 161, Village of Mokena, Mokena Community Park District, and Mokena Community Public Library.
- Expand to nearby communities only after the first service is reliable.
- Publish public documentation and subscription instructions.

**Complete when:** residents can subscribe to stable feeds and developers can use the documented API.

## MVP outcome (the product we are building)

The MVP is a working end-to-end public event discovery and calendar subscription service—not merely an API prototype or a set of feed generators.

A user must be able to:

1. Discover registered local organizations and their official public event sources.
2. Capture events and their available details from those sources (title, dates/times, location, description, links, categories, registration details, and source attribution where published).
3. Parse and normalize those records into a consistent CivicCal event model while preserving source provenance and uncertainty.
4. Store organizations, sources, events, source observations, and update history in a persistent database.
5. Retrieve the stored events through a read-only API.
6. Subscribe to a stable community-wide iCalendar URL and organization-specific iCalendar URLs in Apple Calendar, Google Calendar, Outlook, and other compatible calendar apps.
7. Refresh event data from sources through a controlled capture process, recording changes without treating a missing event as automatically cancelled.

**MVP acceptance test:** Starting from a clean installation, an operator can register an organization/source, ingest a representative source fixture (and later a permitted live capture), persist its events in the database, query them, and generate a valid `.ics` subscription feed from the same stored records. A calendar client can subscribe to that feed and receive subsequent approved updates without duplicate churn.

The current JSON/file-based pipeline and loopback API are development foundations. They are not the final storage layer or a substitute for the database-backed end-to-end MVP. Database implementation is intentionally sequenced for the user's laptop session; meanwhile, keep interfaces and data contracts storage-independent. Do not deploy, enable unattended polling, install software, or incur costs without explicit approval. Source-specific consent and access controls remain mandatory.
## First practical release (MVP)

Prioritize:
1. Source registry and deterministic capture.
2. ICS + existing HTML adapters.
3. Canonical event storage and revision history.
4. Combined community ICS feed and per-organization feeds.
5. Read-only JSON API.
6. Basic source health and backup/restore.

Webhooks, advanced search, user-created custom feeds, and a full web UI follow after this loop works end to end.

## Current project baseline

Already present in the repository: source registry schema/validator, source onboarding docs, dependency-free ICS parser, HTML/JSON-LD extraction foundation, Mokena Park District and Village adapters, duplicate-candidate detection, manual ICS source importer, fixture validation, CI checks, an offline RFC 5545 feed generator, a read-only JSON query projection, and a loopback-only HTTP integration server, all driven by an explicit publication approval manifest.

Not yet implemented as a complete service: canonical persistent event database, general scheduled capture engine, public deployment and remote API access, organization/source-specific feed routes (design documented; implementation pending), recurrence-aware ICS publication, webhook delivery, and operations/backup service. A loopback-only read-only HTTP integration server with ETag caching and an offline source health/integrity report are implemented for local testing.

The checked-in fixtures for the Park District and Village are representative fixtures, not proof that complete live source pages have been captured and validated. The SD 159 uploaded ICS has been inspected locally but is not yet integrated as a complete persistent dataset.

## Non-goals for the first release

- Replacing Google/Apple/Outlook calendar applications.
- Automatically editing a subscriber's personal calendar.
- Silent cross-source event merging.
- AI-based source eligibility or event mutation.
- Mandatory cloud hosting or paid automation services.
- A family-only calendar product.
