# Summit Hill SD 161 iCalendar Request Contract

## Verified publisher links

The official district Events page exposes separate calendars and their **Subscribe → Download .ICS** links. Each district-hosted calendar resolves to its own stable endpoint:

| Calendar | Stable feed URL |
|---|---|
| District Events | https://www.summithill.org/apps/events/ical/?id=0 |
| Indian Trail School Events | https://www.summithill.org/apps/events/ical/?id=3 |
| Dr. Julian Rogus School Events | https://www.summithill.org/apps/events/ical/?id=4 |
| Hilda Walker Intermediate School Events | https://www.summithill.org/apps/events/ical/?id=5 |
| Summit Hill Jr. High School Events | https://www.summithill.org/apps/events/ical/?id=6 |

The IDs 3–6 were verified by following the official Download .ICS link from each corresponding calendar view. Keep these as five independent source feeds; do not combine their identities or assume one is a complete substitute for another.

Mary Drew Early Learning Center has its own school-site calendar on a separate host:

https://mdelc.summithill.org/apps/events/ical/?id=0

That id=0 is scoped to the Mary Drew subdomain and is not the district-domain District Events feed.

## Cache-buster observation

A separately shared URL was supplied in percent-encoded form:

    www.summithill.org%2Fapps%2Fevents%2Fical%2F%3Fid%3D0%26cb%3D1793784704293

Decoded, it is:

    https://www.summithill.org/apps/events/ical/?id=0&cb=1793784704293

For District Events (id=0), the official Google Calendar subscription link wraps the same feed in a webcal:// URL and includes cb=<13-digit timestamp>. A second rendering produced a different timestamp. This confirms that the publisher dynamically adds cb when generating that Google Calendar subscription URL. It strongly suggests a cache-busting purpose, but it does not prove the server requires the parameter or that it changes feed content.

**Implementation decision:** store the stable publisher URLs above; never persist a generated cb value as source identity. The cache-buster behavior has been observed for the District Events Google Calendar subscription link only. Do not assume it applies to the other district calendars or Mary Drew until their subscription links are inspected. Preserve the option to add a fresh cb at request time if direct HTTP testing demonstrates that it is needed. Do not add it to every request yet: doing so could interfere with normal HTTP cache validators (ETag / Last-Modified) and 304 handling.

## Retrieval behavior observed

The publisher endpoints respond as text/calendar. The web text reader rejects that MIME type, so its inability to display the body is not evidence that a feed is broken. The actual ICS payloads still need to be downloaded and archived through a compatible client before feed contents, recurrence, timezone behavior, and completeness can be verified.

## CivicCal boundary

- All six Summit Hill feed URLs are registered as separate source records.
- All six remain review_required; polling remains disabled.
- No live payload has been captured by CivicCal.
- No completeness policy has been enabled.
- The existing one-shot ICS coordinator remains the intended capture path after source gates are deliberately resolved.
