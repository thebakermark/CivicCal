# Summit Hill SD 161 calendar feed scope

**Checked:** 2026-11-03  
**Source page:** https://www.summithill.org/apps/events/

## What the public page shows

The default Events page displays October 2026 entries labelled **District Events** and exposes a **Subscribe → Download .ICS** link. Following that link resolves to:

`https://www.summithill.org/apps/events/ical/?id=0`

The endpoint responds as `text/calendar`; the web reader cannot render that media type, so the feed payload itself was not inspected here.

The page also lists six separately selectable calendars:

1. District Events
2. Indian Trail School Events
3. Dr. Julian Rogus School Events
4. Hilda Walker Intermediate School Events
5. Summit Hill Jr. High School Events
6. Mary Drew Early Learning Center

## Evidence about individual calendar IDs

- A public calendar page with `?id=5` displayed events labelled **Hilda Walker Intermediate School Events**. Its Download .ICS link resolved to `/apps/events/ical/?id=5`.
- A public calendar page with `?id=6` displayed events labelled **Summit Hill Jr. High School Events**.

This supports the conclusion that the `id` parameter selects a calendar rather than representing a generic feed format.

## Current interpretation

The default `id=0` page displays only entries labelled **District Events**, so the best-supported interpretation is that `id=0` is the district-level calendar, not an aggregate of all six school calendars.

**Do not treat this as fully verified feed contents.** The actual ICS response for `id=0` was not readable through the web inspection tool. Before assuming complete district-wide coverage, compare a permitted downloaded response with events shown on the individual calendar pages.

The IDs for Indian Trail, Dr. Julian Rogus, and Mary Drew have not been mapped in this review. Do not guess their IDs or add speculative feed URLs.

## Implementation status

- Existing registry source `summit-hill-sd161-events-ical` remains the `id=0` URL.
- Keep `access_status: review_required`, `polling_enabled: false`, `terms_reviewed: false`, and `robots_reviewed: false` until those reviews are completed.
- No network importer, polling, database write, or publication was run.
