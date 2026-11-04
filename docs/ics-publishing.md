# iCalendar feed generation

**Status:** deterministic offline feed projection implemented; no HTTP service or subscriber delivery is deployed.

## Inputs

The publisher consumes two JSON files:

1. `civiccal.identity-state.v1` — output of `scripts/track_event_identity.py`.
2. `civiccal.publication-manifest.v1` — an explicit approval list maintained by an authorized operator.

Example publication manifest:

```json
{
  "format": "civiccal.publication-manifest.v1",
  "calendar_name": "Mokena Community Events",
  "approved_event_ids": [
    "evt_0123456789abcdef01234567"
  ]
}
```

Only event IDs named in `approved_event_ids` are included. An event's presence in identity state, a source registry entry, or a parser output does not imply publication approval. The publisher never edits the manifest or identity state.

## Command

```sh
python scripts/publish_ics.py \
  data/state/identity.json \
  data/publication/community.json \
  --output data/published/community.ics
```

The output is UTF-8 `text/calendar` with CRLF line endings, RFC 5545 text escaping, UTF-8-aware 75-octet line folding, stable event UIDs (`event_id@civiccal`), and `SEQUENCE` from the current identity revision. The revision observation timestamp supplies deterministic `DTSTAMP` and `LAST-MODIFIED` values.

## Current supported behavior

- Explicitly approved events only.
- Stable UID and revision sequence.
- All-day `DTSTART;VALUE=DATE`.
- All-day `DTEND` only when the record explicitly sets `end_exclusive: true`; otherwise the end is omitted rather than guessing whether a publisher's final date is inclusive.
- Floating local date-times remain floating; no timezone is invented.
- Date-times with explicit offsets are converted to UTC.
- Explicit cancelled status becomes `STATUS:CANCELLED`.
- Summary, description, location, categories, event URL, registration URL extension, and source ID extension.
- Deterministic output for unchanged identity state and approval manifest.

## Deliberate limits

The publisher fails closed for approved records with unresolved temporal values, zoned local times lacking an explicit UTC offset, or recurrence metadata. Generating correct `VTIMEZONE` components and recurrence-aware instances needs a separate implementation and independent compatibility tests; the publisher must not silently publish incorrect wall-clock times or incomplete recurring series.

The current script is a file-based projection, not a public endpoint. It does not provide combined/organization/source routes, HTTP caching, ETags, access controls, subscription management, or automatic refresh. Those belong to a later service layer and remain independent of the database decision.

## Validation

`tests/test_publish_ics.py` covers approval filtering, stable UIDs and sequence, UTC conversion, floating times, all-day values, cancellation, text escaping, UTF-8 line folding, invalid approvals, unresolved zones, and recurrence rejection. The repository CI suite runs these tests alongside parser, registry, and source-fixture validation.
