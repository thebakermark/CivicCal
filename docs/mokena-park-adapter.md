# Mokena Park District HTML adapter

`scripts/parse_mokena_park.py` parses saved HTML from the Park District's
Upcoming Events editorial page. It is intentionally source-specific; the
Village calendar uses a different adapter.

## Run offline

```sh
python scripts/parse_mokena_park.py saved-upcoming-events.html --output events.json
```

The parser recognizes event headings and following content blocks. It keeps
the event's date text, registration-deadline text, fee text, location text,
descriptions, and registration/detail links in separate fields.

It does not guess a year when the page omits one. It does not promote a
registration deadline or judging date into the event date. Sections without a
clear event date are retained as undated records for review. A saved,
representative HTML fixture and tests cover these rules.

The fixture is a controlled test sample based on the page's observed content,
not a captured complete page response. Before live ingestion is approved,
capture an actual response as a versioned fixture and verify parser output
against it. This parser performs no network requests and enables no polling.
