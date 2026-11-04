# iCalendar Feed Publishing

## Purpose

Let residents subscribe using calendar applications they already use. CivicCal publishes feeds; it does not need to replace Apple Calendar, Google Calendar, Outlook, or other clients.

## Feed types

Stable URLs should support:
- Combined community feed.
- Organization feed.
- Individual source/calendar feed.
- Category feed.
- Optional curated filtered feed in a later phase.

Examples (final route names are to be confirmed during implementation):
- `/calendars/community.ics`
- `/calendars/organizations/{organization_id}.ics`
- `/calendars/sources/{source_id}.ics`
- `/calendars/categories/{category}.ics`

## RFC 5545 requirements

- Valid VCALENDAR and VEVENT structure.
- Stable UID for each published event.
- Correct escaping, line folding, and content-line encoding.
- DTSTAMP and LAST-MODIFIED when applicable.
- SEQUENCE increments for material revisions.
- STATUS:CANCELLED only when cancellation is explicit or confirmed through documented reconciliation.
- Correct DTSTART/DTEND value types for date-only and date-time events.
- Preserve timezone definitions/references when needed.
- Preserve recurrence rules and exceptions, or publish correctly expanded instances under a documented strategy.

## Identity and updates

A stable event UID must not change on every feed generation. Revisions update the same UID. A rescheduled event should preserve identity when it is demonstrably the same event.

Do not emit cancellation solely because an event was absent from one source capture. Missing-source handling must be resolved before publication state changes.

## Feed caching

Support ETag and Last-Modified so clients can avoid downloading unchanged feeds. Return appropriate content type and cache headers. Feed generation should be deterministic for the same underlying publication state.

## Feed filtering

Filtering must be consistent with API query semantics. A community feed should not silently exclude low-volume organizations or niche community events. Document any category or geographic exclusions.

## Client compatibility testing

Test generated feeds with:
- Independent RFC 5545 parsers.
- Apple Calendar subscription.
- Google Calendar subscription.
- Outlook subscription.

Validate update, cancellation, recurrence, all-day event, timezone, and unchanged-feed behavior. Do not claim client compatibility until tested.

## Subscription privacy

Public feed URLs should not contain personal data. If private/custom feeds are introduced later, use revocable opaque tokens and avoid putting subscriber identity in URLs or logs.
