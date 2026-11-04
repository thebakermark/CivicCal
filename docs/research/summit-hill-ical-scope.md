# Summit Hill SD 161 calendar feed scope

**Checked:** 2026-11-03  
**Source page:** https://www.summithill.org/apps/events/

## What the public page shows

The default Events page displays October 2026 entries labelled **District Events** and exposes a **Subscribe → Download .ICS** link. Following that link resolves to:

`https://www.summithill.org/apps/events/ical/?id=0`

The endpoint responds as `text/calendar`; the web reader cannot render that media type, so the feed payload itself was not inspected here.

The page lists six separately selectable calendars:

1. District Events
2. Indian Trail School Events
3. Dr. Julian Rogus School Events
4. Hilda Walker Intermediate School Events
5. Summit Hill Jr. High School Events
6. Mary Drew Early Learning Center

## Calendar ID mapping observed

The following calendar pages display events under these labels:

| Calendar ID | Displayed calendar |
|---|---|
| 0 | District Events (default page) |
| 3 | Indian Trail School Events |
| 4 | Dr. Julian Rogus School Events |
| 5 | Hilda Walker Intermediate School Events |
| 6 | Summit Hill Jr. High School Events |

Evidence pages:
- Default: https://www.summithill.org/apps/events/
- ID 3: https://www.summithill.org/apps/events/2026/11/?id=3
- ID 4: https://www.summithill.org/apps/events/2026/11/?id=4
- ID 5: https://www.summithill.org/apps/events/2024/8/?id=5
- ID 6: https://www.summithill.org/apps/events/2027/2/?id=6

The Download .ICS link on an ID 5 page resolves to `/apps/events/ical/?id=5`. This supports the conclusion that the `id` parameter selects a calendar.

## Current interpretation

The default `id=0` page displays entries labelled **District Events**, so the best-supported interpretation is that `id=0` is the district-level calendar, not an aggregate of all six school calendars.

**Do not treat this as fully verified feed contents.** The actual ICS response for `id=0` was not readable through the web inspection tool. Before assuming complete district-wide coverage, compare a permitted downloaded response with events shown on the individual calendar pages.

The ID for Mary Drew Early Learning Center has not been mapped. Do not guess its ID or add a speculative feed URL.

## Implementation status

- Existing registry source `summit-hill-sd161-events-ical` remains the `id=0` URL.
- Keep `access_status: review_required`, `polling_enabled: false`, `terms_reviewed: false`, and `robots_reviewed: false` until those reviews are completed.
- No network importer, polling, database write, or publication was run.
