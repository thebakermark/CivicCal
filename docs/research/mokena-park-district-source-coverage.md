# Mokena Community Park District source coverage

**Checked:** 2026-11-04  
**Organization:** Mokena Community Park District  
**Purpose:** Separate the Park District's public event channels by scope so CivicCal does not mistake a highlights page for a complete calendar.

This is source-discovery and rendered-page research. It is not a raw capture, permission determination, or completeness assertion. No live capture, polling, database write, or publication was performed.

## 1. Curated Upcoming Events page

- Official page: https://www.mokenapark.com/upcoming-events-2/
- Registry ID: `mokena-park-district-events`
- Existing parser: `scripts/parse_mokena_park.py`
- Existing representative fixture: `data/fixtures/mokena-park-upcoming.html`

The page is a curated editorial list. At the time of review it included:

| Listing | Published schedule information | Notes |
|---|---|---|
| Puzzlemania | Friday, November 6, 6–8 PM | All ages; preregistration; team fee and November 1 deadline |
| Cookies and Cocoa Night | Friday, November 13, 5:30–7 PM | One child and one adult; preregistration; November 8 deadline |
| Free Holiday Lights – House Decorating Contest | Registration deadline December 9; judging December 15, 6–9:30 PM | The listing does not state a separate event date; do not turn deadline or judging into an event date without source context |
| Lunch Bunch & Bingo | Wednesday, November 18, 11 AM–1 PM | 55+; The Oaks; fee and November 16 deadline |
| Preschool Fall 2026 Registration | No event date in the listing | Registration/program information, not a dated event |
| Card Show at the Barn | Saturday, February 20, 2027, 9 AM–2 PM | Yunker Farm Red Barn; admission information |

The parser must preserve date text, fees, eligibility, registration deadlines, and links separately. It must not invent a year where the publisher omits one or promote a registration deadline or judging time into the event's start date.

## 2. Board of Commissioners meeting schedule

- Official page: https://www.mokenapark.com/board-information/
- Registry ID: `mokena-park-district-board-meetings`
- Source type: HTML
- Current status: `review_required`; polling disabled

The official page lists the 2026 schedule:

- January 27
- February 24
- March 24
- April 28
- May 26
- June 23
- July 21 — special meeting
- July 28 — canceled
- August 25
- September 22
- October 27
- November 24
- December 15

The page states that regular meetings are held at 6:00 PM at The Oaks Recreation & Fitness Center, 10847 West La Porte Road, Mokena. The listed November 24 and December 15 meetings are the remaining 2026 dates as of this review. Preserve the July 21 special-meeting designation and July 28 cancellation. Do not infer the 2027 dates by applying a recurring fourth-Tuesday rule; the published notice itself identifies January and December exceptions in the 2025 schedule and 2026 dates differ.

## 3. Seasonal program brochures (PDF)

The Park District homepage links to a seasonal brochure. At the time of review, the linked Fall 2026 brochure URL was:

https://www.mokenapark.com/wp-content/uploads/2026/07/Fall-2026-Brochure.pdf

The brochure is a distinct source channel from the curated Upcoming Events page. It likely contains wider program and event coverage, but it is a PDF and the current source registry accepts only `ics`, `rss`, `atom`, `json_api`, `html`, and `email` source types. The browser retrieval route rejected the full brochure because of its response size. Do not register it as HTML or treat its contents as inspected. PDF source registration and a bounded PDF extraction workflow are future implementation work.

The earlier 2026 Summer brochure also explicitly states that Park District Board meetings are generally held on the fourth Tuesday of each month at 6:00 PM at The Oaks. This is useful context, but the current Board Information page's dated schedule is the better source for specific meeting dates.

## 4. Rec1 catalog and sports schedule

The Park District's registration button links to its Rec1 catalog:

https://secure.rec1.com/IL/mokena-community-park-district/catalog

The catalog is an interactive registration application, not a demonstrated calendar feed. A separate TeamSideline site exposes Calendar and Game Schedules pages:

- https://mokenacommunityparkdistrict.teamsidelinesite.com/calendar
- https://mokenacommunityparkdistrict.teamsidelinesite.com/schedules

The schedules page currently renders “Loading schedules...” in the accessible view, and no usable event payload was verified. Keep these as discovery leads, not active sources. Do not assume a team schedule API or scrape the registration portal without reviewing its applicable terms and access rules.

## 5. Source boundary and next steps

- Keep the Upcoming Events page scoped to curated public highlights.
- Keep Board meetings as a separate source record.
- Treat the seasonal brochure as an unsupported PDF source until PDF handling is deliberately added.
- Treat Rec1 and TeamSideline as separate discovery leads; do not conflate registration catalog items with public events.
- Keep all new sources at `review_required`; polling remains disabled.
- Obtain genuine saved responses through an approved capture route before creating raw HTML fixtures or asserting completeness.
- Reconcile Park District events already shown on the Village calendar as duplicate candidates, not silent merges.

## Evidence reviewed

- Upcoming Events: https://www.mokenapark.com/upcoming-events-2/
- Board Information: https://www.mokenapark.com/board-information/
- Homepage brochure link: https://www.mokenapark.com/
- Rec1 catalog: https://secure.rec1.com/IL/mokena-community-park-district/catalog
- TeamSideline calendar: https://mokenacommunityparkdistrict.teamsidelinesite.com/calendar
- TeamSideline schedules: https://mokenacommunityparkdistrict.teamsidelinesite.com/schedules
- 2026 Summer brochure: https://www.mokenapark.com/wp-content/uploads/2026/04/2026-Summer-Brochure.pdf

Rendered pages and indexed document text were used for discovery. They are not substitutes for raw captured source responses and do not establish terms-of-use or robots.txt status.
