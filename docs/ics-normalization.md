# ICS normalization

CivicCal's first calendar reader is a dependency-free Python implementation in
`scripts/parse_ics.py`. It reads an ICS file and emits normalized JSON.

## Run locally

```bash
python scripts/parse_ics.py data/fixtures/sample-community.ics \
  --source-id example-community-calendar \
  --source-url https://example.org/calendar.ics \
  --output /tmp/civiccal-events.json
python -m unittest discover -s tests -v
```

Use `-` as the input path to read ICS from standard input. The parser does not
make network requests and does not write to the event store.

## Semantics and deliberate limits

- Unfolds RFC-style continuation lines and decodes escaped TEXT values.
- Reads VEVENT properties, including UID, DTSTART/DTEND, text, URL, organizer,
  categories, sequence, timestamps, cancellation status, and recurrence fields.
- Preserves TZID and local wall-clock values. UTC values are marked UTC.
- Floating date-times remain floating; the parser never guesses a timezone.
- DATE values remain all-day dates.
- RRULE, RDATE, EXDATE, and RECURRENCE-ID are preserved as source values.
  Recurrences are not expanded in this first version.
- VTIMEZONE definitions are not interpreted. A TZID is retained as a reference;
  a later timezone-resolution layer must validate custom timezone definitions.
- Unknown properties are ignored. Malformed date-time values are retained as
  unparsed values with a warning rather than silently discarded.

## Duplicate-candidate review

After parsing, run the separate review tool against the normalized JSON:

```bash
python scripts/find_duplicate_candidates.py /tmp/civiccal-events.json \
  --output /tmp/civiccal-duplicate-candidates.json
```

The tool groups exact matches on normalized title, description, location,
start, end, and status. It ignores UID and source metadata so that the same
event published by multiple sources can be surfaced for review. It normalizes
case and whitespace, but does not use fuzzy matching.

**A candidate is not proof of a duplicate.** The report preserves each event's
array index, UID, source ID, and basic details. It never merges, deletes, or
rewrites events. Holiday entries and recurring calendar items remain
independent source records unless a later reconciliation process confirms
that they represent the same occurrence.

This is an ingestion and review primitive, not source approval. Do not enable
polling until the source's access rules and polling policy have been reviewed.
The parser does not determine whether an event is public, registration-required,
or members-only; that classification belongs to source/event review.


## One-shot source import and change reports

The manual importer can fetch a registry-listed ICS source only after the source
has `access_status: "approved"`, `terms_reviewed: true`, and
`robots_reviewed: true`. It does not require `polling_enabled: true`; that
flag remains reserved for a separately authorized scheduled-ingestion phase.

Run a one-time baseline import:

```bash
python scripts/import_ics_source.py \
  --source-id approved-calendar-id \
  --output-dir ./work/approved-calendar
```

Compare a later manual fetch with the saved baseline:

```bash
python scripts/import_ics_source.py \
  --source-id approved-calendar-id \
  --previous-snapshot ./work/approved-calendar/snapshot.json \
  --output-dir ./work/approved-calendar-latest
```

Each run writes a complete `snapshot.json` and a `change-report.json`.
The importer sends a descriptive CivicCal User-Agent, accepts calendar content,
uses a request timeout and response-size limit, and refuses non-HTTPS source
URLs or redirects. It does not follow a schedule, modify the registry, publish
events, or write to a database.

Change reports compare events by UID and report added, changed, and missing
UIDs. The first run is a baseline, so its events are not described as new
announcements. A missing UID means only that it was absent from this successful
fetch; it is not a cancellation. Review changes before any canonical event is
updated. Repeated or missing UIDs stop the comparison rather than creating an
ambiguous report.

The current Mokena SD 159 calendar source is still marked
`review_required`. The importer intentionally refuses to fetch it until the
source review is completed and the registry is updated accordingly. No live
fetch or scheduled polling is performed by the tests or CI.

### SD 159 manual-import consent switch

The SD 159 source record has `consent_required: true` and `consent_granted: false` in `data/sources.json`. Keep it false until written consent for automated access is received. After receiving written consent, change only `consent_granted` to `true` to enable the existing one-shot manual importer. The importer does not schedule polling; `polling_enabled` remains false. Set `consent_granted` back to `false` to disable network imports again. This switch does not publish the source or enable recurring fetches.
