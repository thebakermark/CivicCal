# Village of Mokena MunicipalCMS adapter

`scripts/parse_village.py` supports two offline inputs:

- Calendar listing HTML from `https://www.mokena.gov/calendar.aspx`: extracts unique `calendarView.aspx` event-detail links identified by the `cid` query parameter.
- Individual `calendarView.aspx?cid=...` detail HTML: extracts the title, Event Date, Event Time, Location, Details, and `cid` identifier.

## Run offline

```sh
python scripts/parse_village.py saved-calendar.html --page-url https://www.mokena.gov/calendar.aspx --output links.json
python scripts/parse_village.py saved-event.html --page-url 'https://mokenail.municipalone.com/calendarView.aspx?cid=30642' --output event.json
```

The live calendar page and detail pages were inspected. A real event detail page
uses the `calendarView.aspx` route and exposes `Event Date:`, `Event Time:`,
`Location:`, and `Details:` fields. Its event identifier is the `cid`
query parameter. Example: [Food Trucks on Front detail page](https://mokenail.municipalone.com/calendarView.aspx?catid=0&cid=30642&id=0).

The committed tests use a controlled HTML sample based on the inspected detail
page's published fields. It is not represented as a complete captured response.
Before live ingestion, verify the parser against saved listing and detail HTML.
The listing parser intentionally does not assign dates from calendar-grid
positions; detail pages remain authoritative for event date/time. It also
reports explicit HTML `rel="next"` links as pagination candidates. It never
claims that the final page has been reached: absence of a `rel="next"` link is
not proof that the publisher has no other pages. Every discovered detail link
must be reconciled against a successfully parsed detail page before the
snapshot validator can consider completeness.

No network requests, polling, publication, timezone inference, or event merging
are performed. Source registry eligibility remains unchanged and polling stays
disabled.
