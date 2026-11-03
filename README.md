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

Early foundation. No public API or automated ingestion is deployed yet.

## Principles

1. Publicly accessible events first; clearly label registration-required and member-only events.
2. Never treat a temporary fetch failure as proof that an event was cancelled.
3. Preserve provenance: every event should be traceable to one or more sources.
4. Treat inbound email and attachments as untrusted input.
5. Keep organization records even when an organization does not yet publish a machine-readable calendar.
6. No paid services or deployment without an explicit project decision.

## License

To be selected before public contributions or reuse are encouraged.
