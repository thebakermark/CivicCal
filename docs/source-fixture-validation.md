# Offline source-fixture validation

CivicCal's first three source adapters and the common event normalizer can be checked together without contacting any source website.

## Run

From the repository root:

```bash
python scripts/validate_source_fixtures.py
```

For the full machine-readable report:

```bash
python scripts/validate_source_fixtures.py --json
```

The runner parses only these checked-in fixtures:

- `data/fixtures/sample-community.ics` through `scripts/parse_ics.py`
- `data/fixtures/mokena-park-upcoming.html` through
  `scripts/parse_mokena_park.py`
- `data/fixtures/village-calendar-detail.html` through
  `scripts/parse_village.py`

After parsing, it passes each parser result through `scripts/normalize_events.py` and checks that the canonical records retain source IDs, event counts, temporal semantics, and review flags. It checks representative source semantics across all three adapters:
calendar UIDs, timezone preservation, cancellation status, Park District
registration-deadline and judging-date separation, explicit year preservation,
and Village detail-field extraction without timezone guessing. It also verifies that the Village's explicit date/time becomes a floating local datetime, ICS TZID and cancellation status survive normalization, and undated Park District cards remain present with registration deadlines kept separate.

The report includes parser warnings rather than suppressing them. Warnings are
not automatically failures because some are deliberate statements of parser
limits, but each warning should remain visible for review.

## Safety boundary

This is an offline fixture test only. It does not:

- make HTTP requests or read live source URLs;
- run scheduled polling or change source approval flags;
- write to a database or modify source fixtures;
- merge duplicate candidates or change event status;
- publish events or generate public feeds.

A passing fixture test proves that the parser behavior matches the checked-in
fixtures and assertions. It does **not** prove that a fixture is a complete
capture of the live website or that a source is approved for automated access.
The current Village and Park District fixtures are representative test inputs,
not verified full-page captures.
