# Summit Hill SD 161 iCalendar Request Contract

## Verified publisher link

The official district Events page exposes a `Download .ICS` link. Following that link resolves to:

```text
https://www.summithill.org/apps/events/ical/?id=0
```

The official page labels the currently selected calendar **District Events** and lists six selectable calendars:

1. District Events
2. Indian Trail School Events
3. Dr. Julian Rogus School Events
4. Hilda Walker Intermediate School Events
5. Summit Hill Jr. High School Events
6. Mary Drew Early Learning Center

The publisher page is the authority for the calendar label and feed link. The `id=0` value identifies the District Events export; other previously verified IDs are registered separately.

## Cache-buster observation

A separately shared URL was supplied in percent-encoded form:

```text
www.summithill.org%2Fapps%2Fevents%2Fical%2F%3Fid%3D0%26cb%3D1793784704293
```

Decoded, it is:

```text
https://www.summithill.org/apps/events/ical/?id=0&cb=1793784704293
```

The direct Download .ICS link resolves without `cb`, while the official Google Calendar subscription link wraps the same feed in a `webcal://` URL and includes `cb=<13-digit timestamp>`. A second rendering produced a different timestamp. This confirms that the publisher dynamically adds `cb` when generating its Google Calendar subscription URL. It strongly suggests a cache-busting purpose, but it does not prove the server requires the parameter or that it changes feed content.

**Implementation decision:** store the stable publisher URL with `id=0`; never persist a generated `cb` value as source identity. Preserve the ability to add a fresh `cb` value at request time if direct HTTP testing shows that the endpoint or an intermediary serves stale responses without it. Do not add it to every request yet: doing so could interfere with normal HTTP cache validators (`ETag` / `Last-Modified`) and 304 handling.

## Retrieval behavior observed

The publisher endpoint responds as `text/calendar`. The web text reader rejects that MIME type, so its inability to display the body is not evidence that the feed is broken. The actual ICS payload still needs to be downloaded and archived through a compatible client before feed contents, recurrence, timezone behavior, and completeness can be verified.

## CivicCal boundary

- Registered source URL remains `https://www.summithill.org/apps/events/ical/?id=0`.
- Source remains `review_required`; polling remains disabled.
- No live payload has been captured by CivicCal.
- No completeness policy has been enabled.
- The existing one-shot ICS coordinator remains the intended capture path after source gates are deliberately resolved.
