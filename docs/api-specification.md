# Private Read-only JSON API Specification

## Status

Design baseline for the user's own CivicCal instance and connected calendar/tools. This is not a public community API and is not a claim that an externally reachable API is deployed.

## Principles

- Read-only API for the user's approved event information, with source-filtered access.
- Version paths explicitly (initially `/api/v1`).
- Stable CivicCal identifiers.
- ISO 8601/RFC 3339 date-time representations where an instant is known.
- Preserve all-day and floating-time semantics instead of forcing false UTC offsets.
- Pagination, bounded date ranges, caching, and predictable errors.
- OpenAPI document published with the implementation.

## Proposed endpoints

- `GET /api/v1/events` — search published events.
- `GET /api/v1/events/{event_id}` — retrieve one event.
- `GET /api/v1/categories` — category vocabulary.
- `GET /api/v1/changes` — incremental changes after a cursor or timestamp.
- `GET /api/v1/openapi.json` — machine-readable API description.

The current loopback implementation provides `/health`, `/api/v1/events`, `/calendars/sources/{source_id}.ics`, and `/api/v1/openapi.json`. Event detail, categories, incremental changes, geography filters, and remote access remain future work. The `source_id` event filter and source relay route preserve source boundaries; there is no combined community calendar.

## Event query parameters

- `from`, `to`: date/time window; require a bounded maximum range.
- `source_id`
- `category`
- `q`: text query.
- `location` or geographic bounding parameters, when supported.
- `status`
- `limit`: bounded page size.
- `cursor`: opaque pagination cursor.
- `updated_since`: incremental update query where appropriate.

Document whether the range filters event start, overlap, or both. Recommended default: events whose time interval overlaps the requested interval, with explicit semantics for date-only events.

## Response envelope

Collection responses should include:
- `data`: event or resource array.
- `next_cursor`: opaque cursor or null.
- `has_more`: boolean.
- `request_id`: diagnostic identifier.

Each event should expose its CivicCal ID, title, description, start/end semantics, timezone status, location, publisher links, categories, status, source attribution, first/last seen timestamps, and last-updated timestamp.

## Error format

Use RFC 9457 Problem Details (`application/problem+json`) with stable error type, title, status, detail, and instance. Do not expose stack traces or private source configuration.

## HTTP caching

Support ETag and Last-Modified on stable resources and collection queries where feasible. Honor If-None-Match and If-Modified-Since. Define cache policy for frequently changing and historical queries.

## Rate limits and access

The local instance is for the user's own use. Do not assume anonymous public access. Any remote access requires a separate security and deployment decision. Never expose authorization flags, private source configuration, webhook secrets, mailbox details, credentials, or internal capture payload locations.

## OpenAPI

Generate and validate an OpenAPI 3.1.1 document from the implemented contract. Keep examples and schemas in tests so implementation and documentation cannot drift.

## Versioning

Additive optional fields should remain backward-compatible. Breaking changes require a new API major version and a documented migration window.
