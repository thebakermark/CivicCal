# Event Normalization and Validation

## Purpose

`scripts/normalize_events.py` converts a parser result into the first common CivicCal event representation. It is deterministic and offline. It does not fetch sources, reconcile identities, merge duplicates, write a database, or publish events.

## Usage

Normalize a parse-result envelope produced by `parse_capture.py`:

```sh
python scripts/normalize_events.py data/parse-results/example.json --output data/normalized/example.json
```

It also accepts direct output from the existing ICS, HTML, Park District, or Village parser:

```sh
python scripts/normalize_events.py parsed-events.json --output normalized-events.json
```

## Canonical record

Each normalized event includes:

- Source ID and source-scoped event ID (UID/cid when present).
- Title and description.
- Start/end temporal objects, all-day marker, time status, timezone and UTC offset.
- Location, event URL, registration URL, registration deadline, cost/free status.
- Event status, attendance mode, audience, organizer, image, categories.
- Recurrence metadata when present.
- Data-quality flags.
- Full `source_record` copy and capture provenance.

The envelope includes parser warnings, counts, and flag counts. No event is dropped for being incomplete; records without a usable title or start remain present and are flagged. A separate, pure Schema.org projection is available through `scripts/schemaorg.py`; it does not alter canonical records or replace CivicCal provenance and review data.

## Date and time policy

- ICS date-only values remain date-only and all-day.
- ICS TZID values remain attached to local wall-clock values.
- UTC values remain UTC.
- Floating date-times remain floating; CivicCal does not assign a local timezone.
- ISO date/time strings are parsed only when valid.
- Park District and Village date text is converted only for supported, explicit formats containing a year.
- A source-specific date plus an explicit AM/PM range may become floating local date-times. No timezone is invented.
- Ambiguous or yearless date text remains in `source_record` and receives a review flag.
- Registration deadlines and fees stay separate from event start/end.

## Validation behavior

Validation is non-destructive. Missing title/start, unresolved date semantics, missing location, and end-before-start are reported as flags. Warnings do not cause the source record to be discarded. The complete parser event is retained in `source_record`, including source-specific fields not yet mapped into the canonical vocabulary.

## Schema.org projection

Use `to_schemaorg_event()` from `scripts/schemaorg.py` to create a Schema.org Event view of one normalized event. The adapter maps supported names, descriptions, URLs, dates, locations, organizers, status, attendance mode, free-access status, keywords, audience, registration action, and publisher identifier. It omits unresolved temporal values and unknown status/mode values rather than guessing. It does not export CivicCal source authorization, publication approval, capture history, or internal identity state. Tests live in `tests/test_schemaorg.py`.

## Boundaries

This stage does not create stable CivicCal event IDs, reconcile source revisions, expand recurrence, compare events across sources, or determine publication eligibility. Those belong to later identity/reconciliation and storage stages. Duplicate detection remains a separate review-only operation.
