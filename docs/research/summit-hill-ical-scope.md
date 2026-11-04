# Summit Hill SD 161 calendar feed scope

**Checked:** 2026-11-03  
**District source page:** https://www.summithill.org/apps/events/

## District calendar

The default district Events page displays entries labelled **District Events** and exposes **Subscribe → Download .ICS**. The link resolves to:

`https://www.summithill.org/apps/events/ical/?id=0`

The page also exposes separately selectable school calendars. The following IDs were observed by checking calendar pages and their displayed event labels. For IDs 3–6, the **Subscribe → Download .ICS** link was followed on each page; each resolved to the matching `/apps/events/ical/?id=<id>` endpoint:

| Calendar ID | Displayed calendar |
|---:|---|
| 0 | District Events |
| 3 | Indian Trail School Events |
| 4 | Dr. Julian Rogus School Events |
| 5 | Hilda Walker Intermediate School Events |
| 6 | Summit Hill Jr. High School Events |

Evidence pages:
- Default district calendar: https://www.summithill.org/apps/events/
- ID 3: https://www.summithill.org/apps/events/2026/11/?id=3 → `https://www.summithill.org/apps/events/ical/?id=3`
- ID 4: https://www.summithill.org/apps/events/2026/11/?id=4 → `https://www.summithill.org/apps/events/ical/?id=4`
- ID 5: https://www.summithill.org/apps/events/2026/11/?id=5 → `https://www.summithill.org/apps/events/ical/?id=5`
- ID 6: https://www.summithill.org/apps/events/2026/11/?id=6 → `https://www.summithill.org/apps/events/ical/?id=6`

The visible district page lists Mary Drew Early Learning Center among its calendar filters, but its corresponding numeric ID on the district domain has not been established. Do not infer that it is ID 7.

## Mary Drew Early Learning Center has its own school-site calendar

The official Mary Drew site is on a separate subdomain:

- Events page: https://mdelc.summithill.org/apps/events/
- The page identifies the school as Mary Drew Early Learning Center and shows one local calendar named **Events**.
- Its **Subscribe → Download .ICS** link resolves to:

`https://mdelc.summithill.org/apps/events/ical/?id=0`

This is a separate school-site feed. Its `id=0` is not the district-domain `id=0` feed. The web reader rejects the ICS response as `text/calendar`, so the actual payload has not been inspected.

## Decision: use the dedicated Mary Drew feed

**Chosen approach:** use the official Mary Drew school-site feed as the Mary Drew calendar source:

`https://mdelc.summithill.org/apps/events/ical/?id=0`

Do not block source onboarding on discovering a second, district-domain numeric filter ID for Mary Drew. The dedicated subdomain is the school's own official Events page, exposes its own Download .ICS link, and labels its local calendar **Events**. This is a direct, independently identified source and avoids guessing at the district selector's internal IDs.

The district-domain Mary Drew filter ID is therefore recorded as **not needed for the initial source set**, rather than guessed. Revisit only if a later coverage comparison shows that the dedicated feed omits events that appear under the district's Mary Drew filter.

This is a source-selection decision, not approval to fetch or poll the feed. Its payload remains uninspected, and its terms/robots review is still outstanding. Keep the record at `review_required` with polling disabled until those gates are resolved.

## Current implementation

The registry now contains six separate Summit Hill feed records, all assigned to the Summit Hill School District 161 organization:

1. `summit-hill-sd161-events-ical` — district-domain `id=0`
2. `summit-hill-indian-trail-events-ical` — district-domain `id=3`
3. `summit-hill-dr-julian-rogus-events-ical` — district-domain `id=4`
4. `summit-hill-hilda-walker-events-ical` — district-domain `id=5`
5. `summit-hill-summit-hill-jr-high-events-ical` — district-domain `id=6`
6. `summit-hill-mary-drew-events-ical` — Mary Drew subdomain `id=0`

All six remain `access_status: review_required`, `polling_enabled: false`, `terms_reviewed: false`, and `robots_reviewed: false`.

The district-level numeric ID for Mary Drew remains unknown. Do not guess it. The actual ICS payloads still need comparison with visible events before claiming complete coverage.

No automated retrieval, polling, database write, or publication was run.
