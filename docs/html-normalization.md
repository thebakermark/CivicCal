# HTML event extraction

CivicCal's shared HTML extraction stage is deliberately offline-first. The
current implementation in `scripts/parse_html.py` reads saved HTML and
extracts Schema.org `Event` objects embedded in
`<script type="application/ld+json">` blocks.

## Contract

Run:

```sh
python scripts/parse_html.py saved-page.html \
  --page-url https://example.org/events/ \
  --source-id example-events \
  --output events.json
```

The normalized records retain source ID and page URL, event title,
description, start/end values exactly as published, location, event URL,
organizer, offer/registration URLs, price/currency, availability, free-access
flag, audience, and image where present. Relative links are resolved against
the canonical page URL. Dates and timezone offsets are not converted or
guessed.

## Safety and correctness

- Parsing is local; this command does not fetch a URL or execute JavaScript.
- It does not infer event dates from arbitrary text or calendar-grid cells.
- It does not merge records, even if two records appear identical.
- Invalid JSON-LD is reported as a warning and does not stop other blocks.
- A page with no JSON-LD produces zero events; this is not proof that the page
  has no events.
- HTML pages without JSON-LD need a reviewed source-specific adapter with
  saved fixtures before live retrieval is considered.
- Registration deadlines, fees, and event dates must remain distinct fields
  when a source-specific adapter is added. Do not turn every date on a page
  into an event.

## Mokena adapter work

The Park District's editorial event listings and the Village's calendar/detail
pages should be handled by separate source-specific adapters over this shared
normalization contract. Their exact selectors and pagination/detail-link
behavior must be verified against saved page fixtures before implementation.
No network fetching, scheduled polling, or source approval is enabled by this
parser.
