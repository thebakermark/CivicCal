# iCalendar feed generation

**Status:** deterministic offline feed projection implemented; a loopback-only development HTTP route serves the approved feed. No public service or subscriber delivery is deployed.

## Inputs

The publisher consumes two JSON files:

1. `civiccal.identity-state.v1` — output of `scripts/track_event_identity.py`.
2. `civiccal.publication-manifest.v1` — an explicit approval list maintained by an authorized operator.

Example publication manifest:

```json
{
  "format": "civiccal.publication-manifest.v1",
  "calendar_name": "Summit Hill District Events",
  "approved_event_ids": [
    "evt_0123456789abcdef01234567"
  ]
}
```

Only event IDs named in `approved_event_ids` are included. An event's presence in identity state, a source registry entry, or a parser output does not imply publication approval. The publisher never edits the manifest or identity state. Every identity record must have a unique non-empty `event_id` and a non-empty `source_id`; malformed or duplicate identities fail closed rather than allowing one record to shadow another. Operators can add or revoke one event with `scripts/set_publication.py`; see [manual event publication approval](manual-publication-approval.md). The command verifies the registered source and exact event ownership before changing only the manifest.

## Command

```sh
python scripts/publish_ics.py \
  data/state/identity.json \
  data/publication/summit-hill.json \
  --output data/published/summit-hill.ics
```

The output is UTF-8 `text/calendar` with CRLF line endings, RFC 5545 text escaping, UTF-8-aware 75-octet line folding, stable event UIDs (`event_id@civiccal`), and `SEQUENCE` from the current identity revision. The revision observation timestamp supplies deterministic `DTSTAMP` and `LAST-MODIFIED` values.

## Current supported behavior

- Explicitly approved events only.
- Stable UID and revision sequence.
- All-day `DTSTART;VALUE=DATE`.
- All-day `DTEND` only when the record explicitly sets `end_exclusive: true`; the RFC 5545 parser derives this flag from a date-valued `DTEND`, while manual/HTML sources must establish their own end-date semantics.
- Floating local date-times remain floating; no timezone is invented.
- Date-times with explicit offsets are converted to UTC.
- Zoned local date-times with a valid IANA timezone (for example, `America/Chicago`) retain local wall time using `DTSTART;TZID=...` and a generated `VTIMEZONE` component. The component is built from the runtime IANA timezone database for a bounded window around the event years, including start and end years. Fixed-offset IANA zones are supported.
- Explicit cancelled status becomes `STATUS:CANCELLED`.
- Summary, description, location, categories, event URL, registration URL extension, and source ID extension.
- Deterministic output for unchanged identity state and approval manifest.

## Deliberate limits

The publisher fails closed for approved records with unresolved temporal values, zoned local times lacking both an explicit UTC offset and a valid IANA timezone, or recurrence metadata. Recurrence rules, exceptions, and detached overrides are not yet emitted. Ambiguous repeated wall times and nonexistent spring-forward wall times fail closed unless the source supplies an explicit UTC offset. The generated `VTIMEZONE` covers a bounded window around each event year; this is appropriate for the currently supported non-recurring events, not a promise of indefinite recurring-series support.

The publisher script remains a file-based projection. The public JSON query projection and ICS publisher both validate event identity uniqueness and source ownership before returning records. Stored-data integrity failures are server-side `503` errors; invalid client query parameters remain `400` errors. The loopback-only HTTP service exposes `GET /calendars/sources/{source_id}.ics`, reading the registered source list and filtering strictly by exact source ID plus the global approval manifest. ETag and Last-Modified are scoped to that source's approved records. This is not a public endpoint; remote hosting and automatic refresh remain future work.

## Validation

`tests/test_publish_ics.py` covers approval filtering, stable UIDs and sequence, UTC conversion, floating times, IANA timezone/VTIMEZONE generation, fixed-offset zones, daylight-saving gap/fold rejection, all-day values, cancellation, text escaping, UTF-8 line folding, invalid approvals, unresolved zones, and recurrence rejection. The repository CI suite runs these tests alongside parser, registry, and source-fixture validation.
