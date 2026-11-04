# Manual public-event snapshot format

**Status:** supported by the offline normalizer; no network access is performed.

`civiccal.manual-events.v1` is the deterministic fallback when a public calendar page can be reviewed but a raw HTML capture or machine-readable feed is unavailable. It is intended for source-linked manual transcription, not for untraceable hand-entered calendar items.

## Required envelope

```json
{
  "format": "civiccal.manual-events.v1",
  "source_id": "mokena-library-events",
  "source_url": "https://mokena.librarycalendar.com/events/list",
  "observed_at": "2026-11-04T16:00:00Z",
  "events": [
    {
      "title": "Example program",
      "start": "2026-11-10T18:30:00",
      "end": "2026-11-10T19:15:00",
      "event_url": "https://mokena.librarycalendar.com/event/example-12345",
      "location": {"name": "Program Room", "branch": "Mokena Public Library"},
      "age_groups": ["Preschool", "Family"],
      "program_types": ["Storytime"],
      "categories": ["Storytime"],
      "registration_required": true,
      "registration_status": "waitlist",
      "description": "Publisher-provided description, retained verbatim."
    }
  ]
}
```

`observed_at` must be the actual observation timestamp in ISO 8601 form; do not copy the illustrative timestamp above. `source_url` must be the HTTPS listing or detail page from which the snapshot was prepared. Every event should include its own `event_url` whenever the publisher provides one. Preserve exact publisher wording and use `null` or omit a field when it is not known.

## Field handling

- `start` and `end` accept ISO date or date-time values. Date-times without an offset remain floating; the normalizer does not infer a timezone.
- `all_day: true` may be supplied for date-only events. Multi-day programs retain both start and end.
- `location` can preserve a room and branch as an object; do not geocode or infer an address.
- `age_groups` are preserved as normalized `audience` labels. `categories` should preserve the publisher's program-type labels; `program_types` may also be retained in the original source record.
- `registration_required` is separate from `registration_status`. Values such as `open`, `full`, `waitlist`, and `closed` describe registration availability, not event cancellation.
- `uid` or `cid` may be supplied only when the publisher actually exposes a stable identifier. Do not invent one from a title or date.
- The complete original event object is retained under `source_record` in normalized output.

## Offline processing

```bash
python scripts/normalize_events.py data/fixtures/library-manual-snapshot.json \
  --output data/normalized/library-manual-snapshot.json
```

The normalizer performs no network requests, database writes, identity merges, duplicate deletion, or publication. Manual records remain observations. If a later HTML or ICS import represents the same event, identity tracking should create a candidate relationship rather than silently merging the records.

## Provenance and quality rules

1. Record the actual observation time and exact official source URL.
2. Keep the source event URL per event where available.
3. Do not infer missing dates, end times, timezones, recurrence instances, audience eligibility, or cancellations.
4. Keep source registration state as mutable metadata; refresh it independently from event status.
5. Keep duplicate observations and flag candidates for review.
6. Mark the capture method as `manual-public-page-review`; do not label manual transcription as an HTML capture or automated fetch.
7. Do not treat this format as authorization for network capture or polling.

## Library-specific source

For Mokena LibraryCalendar, use the public List view as the primary index, then consult linked event detail pages for room, registration, eligibility, and description details. The Upcoming view can repeat featured events in its main listing. Individual `.ics` exports can be imported separately as supplemental observations. See [the source research](research/mokena-library-calendar-source.md) for the mapping rules and source access status.
