# ICS normalization

CivicCal's first calendar reader is a dependency-free Python implementation in
\`scripts/parse_ics.py\`. It reads an ICS file and emits normalized JSON.

## Run locally

\`\`\`bash
python scripts/parse_ics.py data/fixtures/sample-community.ics \\
  --source-id example-community-calendar \\
  --source-url https://example.org/calendar.ics \\
  --output /tmp/civiccal-events.json
python -m unittest discover -s tests -v
\`\`\`

Use \`-\` as the input path to read ICS from standard input. The parser does not
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

This is an ingestion primitive, not source approval. Do not enable polling until
the source's access rules and polling policy have been reviewed. The parser
does not determine whether an event is public, registration-required, or
members-only; that classification belongs to source/event review.
