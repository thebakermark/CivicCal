# Mokena Community Public Library calendar source research

**Checked:** 2026-11-04  
**Official publisher:** Mokena Community Public Library District  
**Calendar platform:** LibraryCalendar by Library Market  
**Registry source ID:** `mokena-library-events`

This is source discovery based on official publisher pages and rendered calendar views. No raw source response was captured, no event was imported, and no polling, database write, or publication was performed.

## Publisher link and calendar views

The official library website links directly to its Available Programs Calendar:

- Official library site: https://mokenalibrary.org/
- Calendar landing/listing: https://mokena.librarycalendar.com/events/upcoming
- Event list: https://mokena.librarycalendar.com/events/list
- Month view: https://mokena.librarycalendar.com/events/month
- Week view: https://mokena.librarycalendar.com/events/week
- Day view: https://mokena.librarycalendar.com/events/day

The calendar provides filters for keyword, date/time, age group, program type, and registration type. Age groups include babies, toddlers, preschool, grade bands, junior high, high school, teen volunteering, adults, family, and neurodiversity. Program types include after school, arts and crafts, book clubs, games, health and wellness, music, sensory, storytime, take-and-make crafts, STEAM, technology, workshops, and more.

## Event detail structure

A representative public detail page:

https://mokena.librarycalendar.com/event/sensory-storytime-40613

Rendered detail fields include:

- Event title
- Date and time
- Room / venue
- Program type
- Age group
- Registration required or not
- Registration capacity and waitlist state
- Program description and disclaimers
- Library location and contact information

The inspected detail page explicitly states that all times are Central time. Other event details demonstrate that events can be offsite or can use a named room within the library.

Examples:

- Sensory Storytime: Falling Leaves & Cozy Reads — November 4, 2026, 6:30–7:15 PM, Program Room; registration required and waitlist available.
- Music Therapy with Edge Music Academy — November 10, 2026, separate 9:30 AM and 10:00 AM sessions; separate event records and distinct times.
- Family Reading Month — a multi-day passive program running through November.
- Adult Take & Make activities — multi-day pickup windows rather than single-time events.

## Important normalization behavior

1. **Featured cards repeat in the listing.** The Upcoming view presents featured cards and then a detailed event listing. The same event can appear twice in one rendered page. Use stable event/node identity and preserve duplicate observations; do not create two canonical events from the featured card and its list entry.
2. **Multi-day programs are real ranges.** Passive reading challenges, scavenger hunts, and take-and-make pickup windows may span several days. Preserve start and end dates/times.
3. **Registration status is mutable metadata.** Open, full, waitlist, closed, and registration-required states should be preserved as observations, not confused with event cancellation.
4. **Age group and program type are valuable structured metadata.** Retain source labels rather than collapsing them into guessed audience categories.
5. **Do not infer recurrence from prose.** For example, a program description may say it meets every Tuesday and Thursday, while the calendar contains individual dated entries. Keep the published event instances; do not generate additional dates from narrative text.
6. **Preserve eligibility and audience disclaimers.** Some programs prioritize library cardholders or have age limits and accompanying-adult requirements. Do not treat a public listing as proof that every attendee can register.

## Individual iCalendar export

A public event's Add to Calendar page was discovered:

https://mokena.librarycalendar.com/node/45947/add_to_calendar

It displays **Add to Google Calendar** and **Download iCal File**. Following the iCal link resolves to:

https://mokena.librarycalendar.com/node/45947/export.ics

The web reader rejects the response as `text/calendar`, which is not evidence that the export is broken. This verifies an event-specific iCalendar export route for at least one event. The underlying node ID differs from the numeric suffix used in the public event slug, so do not assume the suffix can be substituted into the `/node/{id}/export.ics` route.

This is not yet a combined calendar feed. Library Market's public product documentation says LibraryCalendar can expose RSS, XML, iCal, or JSON feeds to external websites/services, with configurable query parameters. That confirms the platform supports such feeds in principle, but does not prove Mokena has enabled one or disclose its URL.

Relevant product documentation:
- https://www.librarymarket.com/blog/calendar-built-for-libraries
- https://portal.suffolklibrarysystem.org/sites/default/files/2023-12/LibraryCalendar-Features.pdf

**Preferred next step:** ask the library whether its LibraryCalendar instance has a public combined iCal, RSS, XML, or JSON feed and, if so, request the publisher-approved URL and usage guidance. A combined feed would be preferable to discovering and fetching each event's individual export.

## Access and completeness status

- Keep `mokena-library-events` at `review_required`.
- Keep `polling_enabled: false`.
- Terms and robots review remain outstanding; the attempted robots.txt lookup did not yield a readable response.
- Do not use the event-specific export as permission to crawl every event.
- No complete snapshot can be claimed until the actual listing pagination, detail links, duplicate featured cards, and terminal-page behavior are verified from genuine captured responses.
- No source completeness profile is enabled for this source yet; the capture policy needs to account for query-parameter pagination and variable event-detail paths.

## Evidence reviewed

- Official library website: https://mokenalibrary.org/
- Upcoming Events: https://mokena.librarycalendar.com/events/upcoming
- Event List: https://mokena.librarycalendar.com/events/list
- Example event detail: https://mokena.librarycalendar.com/event/sensory-storytime-40613
- Event-specific iCal page: https://mokena.librarycalendar.com/node/45947/add_to_calendar
- Library Market product documentation: https://www.librarymarket.com/blog/calendar-built-for-libraries

The rendered web pages support source discovery and schema planning. They are not raw captures and do not grant permission for automated retrieval.
