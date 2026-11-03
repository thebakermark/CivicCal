# CivicCal Architecture

## 1. Shape of the system

Start as one modular application, not a fleet of independently deployed microservices. Keep clear module boundaries so components can be separated later if scale justifies it.

- **Public API and feed gateway:** Cloudflare Worker (TypeScript) for read-only JSON endpoints, ICS feeds, admin endpoints, and inbound webhooks.
- **Canonical store:** Cloudflare D1 (SQLite) for organizations, sources, events, revisions, observations, and delivery state.
- **Scheduled ingestion:** Python jobs in GitHub Actions for source polling and normalization.
- **Optional raw archive:** Cloudflare R2 for source snapshots and permitted attachments, subject to retention rules.
- **Mailbox adapters:** Gmail API / Pub/Sub and Microsoft Graph subscriptions where configured; IMAP polling or IDLE as a fallback where supported.

Use portable interfaces around storage, queueing, and publishing so Cloudflare-specific code does not leak into parsers and normalization logic.

## 2. Logical modules

1. **Organization registry** — organizations, categories, locations, public contact details, and participation status.
2. **Source registry** — websites, ICS/RSS feeds, APIs, registered mailboxes, sender rules, polling policy, and source health.
3. **Ingestion adapters** — ICS, RSS/Atom, JSON APIs, HTML, email, and approved attachment formats.
4. **Normalization and reconciliation** — parse, normalize time zones, match duplicates, compare changes, and preserve provenance.
5. **Event repository** — canonical events, source observations, revisions, and cancellation state.
6. **Publishing gateway** — JSON API, ICS feeds, organization feeds, category feeds, and future webhooks.

These are modules within the initial application, not separate deployables.

## 3. Data model

Core records:

- `organizations`: name, type, description, website, service area, public contact, visibility, verification status.
- `sources`: organization, source type, URL or mailbox reference, access method, polling interval, terms/robots review, last success, next poll, health state.
- `events`: stable CivicCal ID, title, description, start/end, timezone, location, status, visibility, access notes.
- `event_source_links`: links canonical events to all originating sources.
- `source_observations`: immutable observation of what a source reported and when it was observed.
- `event_revisions`: meaningful canonical event changes over time.
- `jobs`: scheduled work, retries, and outcomes.
- `outbox`: transactional publication work, enabling reliable downstream delivery.
- `mailbox_sources`: registered mailbox/provider references and subscribed folders or labels.
- `mailbox_sender_rules`: approved sender/domain and message handling rules.
- `received_messages`: provider message ID, sender, received time, processing status, and safe metadata.
- `message_event_links`: extracted event relationships and review state.

Credentials and tokens belong in the platform's secret store, never in source registry records or Git.

## 4. Event lifecycle

1. Fetch or receive a source observation.
2. Preserve safe source metadata and, where permitted, a raw snapshot.
3. Parse and normalize the event, including timezone and source URL.
4. Match it to an existing canonical event using source IDs, UID, dates, title, and location; uncertain matches go to review.
5. Record the observation and compare meaningful fields.
6. Create a revision only when canonical data changes.
7. Publish changes through the API and regenerate relevant ICS output.
8. Treat disappearance as a possible source-side removal, not immediate cancellation. Confirm through subsequent successful fetches or an explicit cancellation signal.

An event found on a website, email notice, and ICS feed should normally resolve to one canonical event with three provenance links.

## 5. Mailbox monitoring

Mailbox monitoring is opt-in and scoped to a registered mailbox, folder/label, and approved sender rules. It is not broad scanning of a personal inbox.

- Gmail: OAuth-authorized Gmail API and Pub/Sub notifications, with history retrieval and periodic reconciliation.
- Microsoft 365: Microsoft Graph change notifications, subscription renewal, and periodic reconciliation.
- IMAP: IDLE when available, plus polling fallback.

Notifications signal that a mailbox changed; they are not necessarily the full message. Retrieve the message through the authorized provider API, validate sender and message metadata, then process supported content.

Parse ICS attachments first; then supported HTML/text and selected document formats. Treat all email text and attachments as untrusted data. Never execute attachments, follow instructions embedded in messages, or automatically reply. Ambiguous events, cancellations, and conflicting details should enter a review queue.

## 6. Polite source monitoring

Use conditional requests (ETag / If-Modified-Since) and content hashes. Starting intervals are configurable defaults, not promises:

- Push notifications: process promptly, then reconcile periodically.
- ICS / RSS / stable APIs: approximately every 5–15 minutes.
- Ordinary HTML calendars: approximately every 30–60 minutes.
- Heavier JavaScript-driven pages: approximately every 1–4 hours.

Add jitter, per-domain concurrency limits, exponential backoff, and respect Retry-After. Review robots rules, site terms, and access restrictions before enabling a source. Prefer official feeds, APIs, and explicit submissions over scraping.

## 7. Public interface

Initial read endpoints:

- `GET /api/v1/events`
- `GET /api/v1/events/{id}`
- `GET /api/v1/organizations`
- `GET /api/v1/organizations/{id}`
- `GET /api/v1/sources` (public-safe fields only)
- `GET /api/v1/changes`
- `GET /api/v1/categories`
- `GET /health`

iCalendar endpoints:

- `GET /feeds/community.ics`
- `GET /feeds/categories/{category}.ics`
- `GET /feeds/organizations/{organization_id}.ics`

Public endpoints expose only public events and safe organization/source metadata. Admin operations and mailbox management require authentication. Future webhook subscriptions need per-subscriber secrets, delivery retries, and revocation.

## 8. Hosting target

Initial target: Cloudflare Workers + D1, optional R2, and GitHub Actions for scheduled Python ingestion. Stay within free tiers where practical, but verify current provider limits before launch. Free-tier availability and limits can change; the project must not assume a permanent $0 operating cost.

## 9. First milestones

1. Establish source registry and organization taxonomy.
2. Add ICS parser and one verified school/community feed.
3. Normalize events and publish a read-only JSON endpoint.
4. Generate a valid community ICS feed.
5. Add HTML adapters and change detection.
6. Add opt-in mailbox monitoring and review workflow.
7. Add organization-submitted events and public administration.
