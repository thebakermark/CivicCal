# CivicCal

A community-wide event aggregation service for Mokena, Illinois and surrounding communities.

CivicCal collects publicly accessible events from official calendars, community organizations, churches, clubs, civic bodies, and registered event-notification mailboxes. It normalizes events into one source of truth and publishes a public API and iCalendar feeds.

## Project goals

- Aggregate public community events from multiple source types.
- Publish stable JSON API and iCalendar (ICS) feeds.
- Include churches, civic-engagement organizations, clubs, nonprofits, schools, libraries, parks, and local government.
- Preserve source attribution, event history, and meaningful change records.
- Avoid duplicate events when the same event appears in multiple places.
- Monitor sources politely and respect applicable terms, robots rules, rate limits, and access restrictions.
- Keep the public service inexpensive and portable, targeting free-tier hosting.

## Initial geography

Mokena, Illinois first; expand to nearby communities in Will and Cook counties as source coverage grows.

## Architecture

See [docs/architecture.md](docs/architecture.md).

## Source registry

The initial source registry is in [data/sources.json](data/sources.json). Entries are research candidates until their official URLs, event access, and monitoring permissions have been verified. A listed organization is not a claim that it has approved CivicCal or supplied a feed.

## Development status

Early foundation. A guarded, one-shot HTTP capture utility is available at [scripts/capture_source.py](scripts/capture_source.py). The [HTML page coordinator](scripts/capture_coordinator.py) and [single-feed iCalendar coordinator](scripts/capture_ics_source.py) connect capture, parsing, normalization, and source-completeness validation for their respective source types. The offline [capture-to-parser handoff](scripts/parse_capture.py) verifies archived payloads and dispatches them to existing parsers. [Event normalization](scripts/normalize_events.py) maps parser output into common event records while preserving every original source record and flagging incomplete data. The new [school schedule classifier](scripts/classify_school_schedule.py) labels explicit no-school days, school breaks, early dismissals, half days, late starts, and teacher institute days without changing source records or guessing at ambiguous events. [Source completeness validation](scripts/validate_snapshot.py) checks page coverage and pagination evidence before any absence observation can be recorded. [Source-scoped event identity and revision tracking](scripts/track_event_identity.py) assigns stable IDs only when a publisher supplies a stable event ID, and records material changes without cross-source merging. Identity state is written through a replaceable storage interface with an atomic JSON-file backend; database selection is deferred until laptop review. The new [offline iCalendar publisher](scripts/publish_ics.py) generates deterministic RFC 5545 feeds from an explicit publication approval manifest and identity state. The [offline JSON query engine](scripts/query_events.py) builds filtered, paginated public event projections from the same approved set, excluding internal capture payloads. The [local read-only HTTP service](scripts/serve_api.py) now exposes the approved JSON query and community ICS feed on loopback only, with ETag caching. It is a development harness, not a public deployment; automated ingestion and remote access remain disabled.

Example manual capture (only for a source whose registry gates permit network access):

```sh
python scripts/capture_source.py --source-id example-source --archive-dir data/captures

# For a registered ICS feed whose source gates permit capture:
python scripts/capture_ics_source.py \
  --source-id summit-hill-sd161-events-ical \
  --archive-dir data/captures \
  --output data/processed/summit-hill-district-events.json

# For a source-scoped page URL, only when the source's registry gates permit it:
python scripts/capture_source.py --source-id village-of-mokena-events \
  --request-url 'https://mokenail.municipalone.com/calendarView.aspx?cid=30642' \
  --page-role detail --archive-dir data/captures
```

Normalization and school-schedule classification (both offline):

```sh
python scripts/normalize_events.py data/parse-results/example.json --output data/normalized/example.json
python scripts/classify_school_schedule.py data/normalized/example.json --output data/processed/school-schedule-events.json
```

See [event normalization and validation](docs/event-normalization.md) and [school schedule exception classification](docs/school-schedule-classification.md) for the field, time-handling, and classification contracts.

## Principles

1. Publicly accessible events first; clearly label registration-required and member-only events.
2. Never treat a temporary fetch failure as proof that an event was cancelled.
3. Preserve provenance: every event should be traceable to one or more sources.
4. Treat inbound email and attachments as untrusted input.
5. Keep organization records even when an organization does not yet publish a machine-readable calendar.
6. No paid services or deployment without an explicit project decision.

## License

To be selected before public contributions or reuse are encouraged.

## Architecture and implementation roadmap

The project blueprint is documented before expanding the implementation:

- [Roadmap and milestones](docs/roadmap.md)
- [Source lifecycle and capture contract](docs/source-lifecycle.md)
- [Source completeness and pagination](docs/source-completeness.md)
- [One-shot HTML capture coordinator](docs/capture-coordinator.md)
- [One-shot iCalendar capture coordinator](docs/ics-capture-coordinator.md)
- [Summit Hill iCalendar request contract](docs/research/summit-hill-ical-request.md)
- [Capture-to-parser handoff](docs/capture-to-parser.md)
- [Canonical event data model](docs/event-data-model.md)
- [Event identity and revision tracking](docs/event-identity-revisions.md)
- [Processing pipeline](docs/processing-pipeline.md)
- [School schedule exception classification](docs/school-schedule-classification.md)
- [Storage interface (database deferred)](docs/storage-interface.md)
- [Future storage architecture](docs/storage-architecture.md)
- [Public JSON API specification](docs/api-specification.md)
- [Offline JSON query engine](docs/api-query-engine.md)
- [Local read-only HTTP service](docs/local-http-service.md)
- [Offline source health report](docs/source-health-report.md)
- [iCalendar feed publishing design](docs/calendar-feeds.md)
- [Offline iCalendar feed generation](docs/ics-publishing.md)
- [Webhook specification](docs/webhook-specification.md)
- [Open-source reuse assessment](docs/open-source-reuse.md)

The core is planned as a portable modular Python application, SQLite-first, with public JSON and iCalendar interfaces. These documents describe the target design; they do not mean the API, feed publisher, webhook service, database, or scheduled polling are already deployed.
