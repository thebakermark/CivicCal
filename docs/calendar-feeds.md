# iCalendar Feed Publishing

**Product rule:** one registered source = one independent stable CivicCal feed. This replaces any earlier proposals for combined, organization, or category feeds.

## Purpose

Let the user subscribe to selected source calendars using the calendar application they already use. CivicCal publishes feeds for the user's own use; it does not replace Apple Calendar, Google Calendar, Outlook, or other clients.

## Feed boundary

The only MVP feed type is the source-specific feed:

- `/calendars/sources/{source_id}.ics`

Every feed includes only records owned by the exact requested source and explicitly approved for publication. Organization records are descriptive/administrative; they do not aggregate source feeds. There is no community-wide, organization-wide, or category feed.

An event published by two sources remains two independent source-owned records and may appear in each source feed only after separate approval. Duplicate detection never merges or deletes records.

See [Independent Source Calendar Relays](organization-calendar-subscriptions.md) for exact filtering and approval rules.

## RFC 5545 requirements

- Valid VCALENDAR and VEVENT structure.
- Stable UID for each source event.
- Correct escaping, line folding, and content-line encoding.
- DTSTAMP and LAST-MODIFIED when applicable.
- SEQUENCE increments for material revisions.
- STATUS:CANCELLED only when cancellation is explicit or confirmed through documented evidence.
- Correct DTSTART/DTEND value types for date-only and date-time events.
- Preserve timezone definitions/references when needed.
- Preserve recurrence rules and exceptions, or use a documented expansion strategy without inventing occurrences.

## Identity and updates

A stable event UID must not change on every feed generation. Revisions update the same UID. A rescheduled event preserves identity only when the source identity establishes that it is the same event.

Do not emit cancellation solely because an event was absent from one capture. Missing-source handling is not cancellation.

## Feed caching and compatibility

Support ETag and Last-Modified so clients can avoid downloading unchanged feeds. Generation should be deterministic for the same publication state.

Test generated feeds with independent RFC 5545 parsers, then Apple Calendar, Google Calendar, and Outlook. Validate update, cancellation, recurrence, all-day, timezone, and unchanged-feed behavior. Do not claim client compatibility until tested.

## Current implementation status

Offline source-specific feed generation and a loopback-only source relay route exist. The endpoint is not publicly deployed, and calendar-client subscription against a stable external URL has not yet been verified. Public deployment requires a separate explicit decision.
