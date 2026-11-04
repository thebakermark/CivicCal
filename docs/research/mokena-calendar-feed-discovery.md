# Mokena calendar feed discovery

**Checked:** 2026-11-03  
**Purpose:** Record whether the Village of Mokena and Mokena Community Park District publish an obvious calendar feed that could replace HTML extraction.

This is discovery evidence, not an access approval. No automated fetch, polling, database write, or publication was performed.

## Village of Mokena

- Canonical public calendar: https://www.mokena.gov/calendar.aspx
- The public calendar renders a calendar view with event-detail links using `calendarView.aspx` and a `cid` query parameter. Example observed link: https://www.mokena.gov/calendarView.aspx?catid=0&cid=30604&id=0
- The rendered calendar page did not expose an iCal or RSS subscription control.
- The Village notifications page, https://www.mokena.gov/notify.aspx?catid=0&id=20802, exposes email notification categories including Calendar & Events, Community Events, boards/commissions, and Village of Mokena. It is an email-notification signup, not a demonstrated machine-readable calendar feed.
- A search result surfaced a MunicipalOne-hosted calendar at https://mokenail.municipalone.com/calendar.aspx. It resembles the Village calendar, but the canonical Village site did not establish that as an official feed or supported integration endpoint. Do not switch the registered source to this host without confirming the relationship.

**Finding:** No public iCal/RSS feed was identified from the rendered public calendar and notification pages. This is not proof that no feed or vendor API exists; raw response headers/source and vendor documentation were not available in this review.

## Mokena Community Park District

- Official upcoming-events page: https://www.mokenapark.com/upcoming-events-2/
- The page presents event headings, date/time text, descriptions, fees, registration deadlines, locations, and links to the Rec1 registration system.
- The rendered page did not expose an iCal or RSS subscription control.
- The current listing includes some content that is not itself a dated event (for example, preschool registration) and an event/contest section with deadlines and judging dates but no explicit event date. An adapter must preserve those distinctions rather than manufacture event dates.

**Finding:** No public iCal/RSS feed was identified on the official upcoming-events page. This is not proof that no feed or supported API exists; raw response headers/source and vendor documentation were not available in this review.

## Implementation consequences

1. Keep both existing source records in `review_required`; do not enable polling.
2. Continue treating the Village and Park District HTML adapters as offline parsers until a permitted, reproducible capture method is established.
3. Do not infer that a page's public visibility grants permission for automated retrieval.
4. Before live ingestion, obtain genuine saved page responses through an authorized route and use them as regression fixtures. Do not substitute hand-reconstructed HTML for captured source pages.
5. Keep the current deterministic extraction rules: no inferred years/time zones; registration deadlines and judging dates must not become event dates; retain undated source entries for review.

## Evidence reviewed

- Village calendar: https://www.mokena.gov/calendar.aspx
- Village notifications: https://www.mokena.gov/notify.aspx?catid=0&id=20802
- Park District upcoming events: https://www.mokenapark.com/upcoming-events-2/

The pages were inspected through rendered web views. Those views are useful for confirming visible content and link patterns, but they are not complete raw HTML captures and do not establish robots.txt or terms-of-use status.
