# Canonical Event Data Model

## Design goals

CivicCal must preserve the publisher's information, support multiple sources describing the same real-world event, retain history, and produce reliable API and iCalendar views.

The canonical model is not a replacement for source data. It is a normalized representation linked to immutable source observations.

## Core entities

### Organization
Represents the publisher or community organization.

Suggested fields: `organization_id`, name, aliases, website, organization type, geographic area, contact/public information, and status.

### Source
Represents one feed, calendar, webpage, API endpoint, or explicitly scoped mailbox.

A single organization can have multiple sources. A school district may publish district-wide and campus-specific calendars.

### Capture
One attempt to retrieve a source. Stores timestamps, request/response metadata, outcome, payload hash, and raw payload reference.

### Source observation
The event as represented in one captured source. This preserves source-specific identifiers and original values. Each newly processed capture contributes an observation, even when the event is unchanged; observations are distinct from material event revisions.

### Canonical event
The normalized CivicCal event record. It may be linked to one or more source observations, but those links do not imply automatic merging.

### Event revision
A record of each material change to a canonical event, including when it changed and which observation or operator action caused the revision.

### Duplicate candidate
A review record connecting two or more records that may describe the same real-world event. Candidate detection does not merge, delete, or suppress events.

### Audit record
Records administrative actions such as approval, correction, source pause, duplicate resolution, or publication changes.

## Canonical event fields

Recommended initial fields:

- `event_id`: stable CivicCal identifier.
- `title`: normalized display title.
- `description`: normalized description, retaining source text separately.
- `start`, `end`: date/time values with explicit semantics.
- `all_day`: boolean.
- `timezone`: IANA timezone when known.
- `time_status`: `zoned`, `utc`, `floating`, `date_only`, or `unresolved`.
- `location_name`, `street_address`, `locality`, `region`, `postal_code`, `country`, optional coordinates.
- `event_url`: publisher's event detail page.
- `registration_url`.
- `registration_deadline`: separate from event start/end.
- `cost_text`, `is_free` only when explicitly stated.
- `status`: scheduled, cancelled, postponed, rescheduled, or unknown.
- `attendance_mode`: in-person, online, mixed, or unknown.
- `audience`, `organizer`, `image_url`, `categories`.
- `first_seen_at`, `last_seen_at`, `created_at`, `updated_at`.
- `data_quality_flags`.

Do not require every field. Unknown values remain unknown rather than being guessed.

## Source observation fields

Preserve source identity and the source's original representation:

- `source_id`, `source_event_id` (UID or publisher-specific ID).
- Original title, description, date/time strings, timezone parameters, location, links, status, recurrence fields, and source categories.
- Capture ID and raw payload reference.
- Parser/adapter version.
- Observation timestamp and content hash.

This supports later parser improvements and makes corrections traceable.

## Identity rules

- Source event identity is scoped to a source unless the publisher documents a globally stable identifier.
- A source UID is not automatically the CivicCal event ID.
- CivicCal event IDs remain stable across routine edits to the same event.
- A changed date does not automatically mean a new event; reconciliation should use source identity and change evidence.
- Events from different sources remain separate records until an explicit, reviewable relationship is established.
- Duplicate candidates are not merged automatically.

## Time and recurrence

- Preserve RFC 5545 recurrence properties and exceptions from ICS.
- Distinguish date-only all-day values from date-times.
- Preserve TZID and VTIMEZONE information where available.
- Do not assign a timezone to floating date-times without an explicit source-level policy.
- Preserve local wall-clock time semantics across daylight-saving transitions.
- Keep registration deadlines and judging/award dates distinct from the actual event date.
- Define whether APIs return recurrence rules, expanded instances, or both; the initial design should retain the source rule and expose materialized occurrences for practical querying.

## Lifecycle

- Explicit source cancellation may update event status with provenance.
- A missing event in a later capture is not currently interpreted as a lifecycle transition or cancellation. Any future absence detector must first establish that the source capture is a complete snapshot.
- A source deletion or 404 does not cancel every previously published event.
- Rescheduled events retain history and stable identity when source evidence supports continuity.
- Past events remain available according to a documented retention policy.

## Cross-source relationships

Model relationships separately from event identity. A relationship can be:
- possible duplicate,
- confirmed same event,
- related series,
- mirrored listing,
- translated listing,
- unrelated.

Every confirmed relationship records evidence and who/what confirmed it. No automatic source attribution is discarded.

## Publication

Only records meeting publication rules appear in public feeds. Publication status and review state must not erase the underlying observations or history.
