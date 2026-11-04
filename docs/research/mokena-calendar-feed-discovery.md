# Mokena calendar feed discovery

**Checked:** 2026-11-04  
**Purpose:** Record whether the Village of Mokena and Mokena Community Park District publish an obvious calendar feed that could replace HTML extraction.

This is discovery evidence, not an access approval. No automated fetch, polling, database write, or publication was performed.

## Village of Mokena

- Canonical public calendar: https://www.mokena.gov/calendar.aspx
- The public calendar renders a calendar view with event-detail links using `calendarView.aspx` and a `cid` query parameter. Example observed link: https://www.mokena.gov/calendarView.aspx?catid=0&cid=30604&id=0
- The rendered calendar page did not expose an iCal or RSS subscription control.
- The Village notifications page, https://www.mokena.gov/notify.aspx?catid=0&id=20802, exposes email notification categories including Calendar & Events, Community Events, boards/commissions, and Village of Mokena. It is an email-notification signup, not a demonstrated machine-readable calendar feed.
- A search result surfaced a MunicipalOne-hosted calendar at https://mokenail.municipalone.com/calendar.aspx. It resembles the Village calendar, but the canonical Village site did not establish that as an official feed or supported integration endpoint. Do not switch the registered source to this host without confirming the relationship.

**Finding:** No public iCal/RSS feed was identified from the rendered public calendar and notification pages. This is not proof that no feed or vendor API exists; raw response headers/source and vendor documentation were not available in this review.

The current rendered calendar page also exposes quick-range views (Next 7 Days, Next 30 Days, Next 3 Months, Next 6 Months, Next Year) and a month view. The calendar page's visible text does not establish how those controls are represented in raw HTML or whether the existing parser's `rel=next` / `rel=last` pagination assumptions match the live markup.

Representative official detail pages reviewed on 2026-11-04:

- Chamber of Commerce Parade of Lights & Village Tree Lighting Ceremony — November 21, 2026, 5:00 PM, Front Street: https://www.mokena.gov/calendarView.aspx?catid=0&cid=28236&id=0
- Village Board Work Session — November 16, 2026, 6:00 PM, Village Hall: https://www.mokena.gov/calendarView.aspx?catid=0&cid=30732&id=0
- CPR Class with Mokena Fire Protection District — November 2, 2026, 5:30–9:00 PM, Mokena Fire Station #1: https://www.mokena.gov/calendarView.aspx?cid=30604

The CPR detail is a useful edge case: it represents one dated calendar occurrence but its description also lists multiple CPR class dates for the year. The parser should retain that description without automatically expanding it into additional events. The Village calendar also lists partner events (including Park District events), so cross-source duplicates are expected and must remain review candidates.

The rendered detail pages expose the expected labels `Event Date`, `Event Time`, `Location`, and `Details`, consistent with the current adapter's intended field mapping. This is rendered-page confirmation only, not a substitute for a raw HTML capture and parser regression fixture.

## Mokena Community Park District

- Official upcoming-events page: https://www.mokenapark.com/upcoming-events-2/
- The page presents event headings, date/time text, descriptions, fees, registration deadlines, locations, and links to the Rec1 registration system.
- The rendered page did not expose an iCal or RSS subscription control.
- The current listing includes some content that is not itself a dated event (for example, preschool registration) and an event/contest section with deadlines and judging dates but no explicit event date. An adapter must preserve those distinctions rather than manufacture event dates.

**Finding:** No public iCal/RSS feed was identified on the official upcoming-events page. This is not proof that no feed or supported API exists; raw response headers/source and vendor documentation were not available in this review.

## Additional Park District source channels

- Official Board Information page: https://www.mokenapark.com/board-information/ publishes a dated 2026 Board of Commissioners meeting schedule and meeting location/time. It is registered separately as `mokena-park-district-board-meetings`; the 2027 schedule is not yet published in the inspected page.
- The Park District homepage links to a seasonal Fall 2026 brochure PDF at https://www.mokenapark.com/wp-content/uploads/2026/07/Fall-2026-Brochure.pdf. This is not an HTML calendar feed. The current registry/parser does not support PDF as a source type, and the browser retrieval route rejected the full file due to response size. Do not register it as HTML or claim its contents have been inspected.
- The Rec1 registration catalog and TeamSideline calendar/schedules pages are additional discovery leads, not demonstrated public calendar feeds. TeamSideline's accessible schedules page currently renders a loading placeholder.

## Implementation consequences

1. Keep both existing source records in `review_required`; do not enable polling.
2. Continue treating the Village and Park District HTML adapters as offline parsers until a permitted, reproducible capture method is established. Keep the Park District Upcoming Events and Board Information pages as separate sources.
3. Do not infer that a page's public visibility grants permission for automated retrieval.
4. Before live ingestion, obtain genuine saved page responses through an authorized route and use them as regression fixtures. Do not substitute hand-reconstructed HTML for captured source pages.
5. Keep the current deterministic extraction rules: no inferred years/time zones; registration deadlines and judging dates must not become event dates; retain undated source entries for review.

## Evidence reviewed

- Village calendar: https://www.mokena.gov/calendar.aspx
- Village notifications: https://www.mokena.gov/notify.aspx?catid=0&id=20802
- Park District upcoming events: https://www.mokenapark.com/upcoming-events-2/
- Park District board information: https://www.mokenapark.com/board-information/
- Park District seasonal brochure: https://www.mokenapark.com/wp-content/uploads/2026/07/Fall-2026-Brochure.pdf

The pages were inspected through rendered web views. Those views are useful for confirming visible content and link patterns, but they are not complete raw HTML captures and do not establish robots.txt or terms-of-use status.
