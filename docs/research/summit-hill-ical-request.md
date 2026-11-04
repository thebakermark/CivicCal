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

The `cb` parameter resembles a cache-busting value. However, the official publisher's current Download .ICS link resolves without `cb`. There is not yet evidence that `cb` is required, that the server validates it, or that it changes the response.

**Implementation decision:** store the stable publisher URL with `id=0`; do not persist a timestamped `cb` value. Do not add automatic cache-busting to the capture client unless a real HTTP comparison demonstrates that it is necessary. If later testing requires a cache-buster, generate it per request and keep it out of source identity and event provenance.

## Retrieval behavior observed

The publisher endpoint responds as `text/calendar`. The web text reader rejects that MIME type, so its inability to display the body is not evidence that the feed is broken. The actual ICS payload still needs to be downloaded and archived through a compatible client before feed contents, recurrence, timezone behavior, and completeness can be verified.

## CivicCal boundary

- Registered source URL remains `https://www.summithill.org/apps/events/ical/?id=0`.
- Source remains `review_required`; polling remains disabled.
- No live payload has been captured by CivicCal.
- No completeness policy has been enabled.
- The existing one-shot ICS coordinator remains the intended capture path after source gates are deliberately resolved.
