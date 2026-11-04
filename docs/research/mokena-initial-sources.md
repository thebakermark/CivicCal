# Mokena Initial Calendar Source Research

**Research date:** 2026-11-03  
**Scope:** Initial source discovery only. This document does not grant permission to automate collection.

## Discovered source records

| Organization | Registry source ID | Source type | Discovery evidence | Current state |
|---|---|---|---|---|
| Village of Mokena | `village-of-mokena-events` | HTML | Official site links to its Calendar of Events page. The calendar currently lists municipal and community items. | Review required; polling off |
| Mokena Community Public Library District | `mokena-library-events` | HTML | Official library site links to its Available Programs Calendar. The public calendar exposes upcoming programs and registration filters. | Review required; polling off |
| Mokena Community Park District | `mokena-park-district-events` | HTML | Official district site links to a curated Upcoming Events page. It includes dated highlights, eligibility, fees, and preregistration details, but is not the complete program or sports schedule. | Review required; polling off |
| Mokena Community Park District | `mokena-park-district-board-meetings` | HTML | Official Board Information page publishes the Board of Commissioners meeting schedule. | Review required; polling off |
| Mokena School District 159 | `mokena-sd159-events-ical` | ICS | Official district Events page exposes a “Click to Download Calendar” link. Its target is an iCalendar-generation endpoint. | Review required; polling off |

## Observations that affect normalization

- Library events can have registration requirements, age groups, audience restrictions, and multi-day date ranges. Preserve those details rather than reducing each listing to title and start time.
- Park district listings may include resident eligibility, registration deadlines, fees, and age restrictions. These should be distinct fields or clearly retained in event notes. The district's curated Upcoming Events page, Board Information page, seasonal PDF brochures, and Rec1/TeamSideline services are separate source channels; do not treat one as complete coverage of the others.
- Municipal calendars mix civic meetings, community events, closures, and operational reminders. CivicCal should eventually classify these so users can filter them.
- School district's downloadable iCalendar endpoint was discovered from its official Events page. The endpoint returned a `text/calendar` response to the research fetch, but the browser preview could not parse the calendar body. Validate with a proper ICS parser before relying on it.

## Required before enabling any source

1. Review the source host's current terms and robots rules.
2. Confirm the endpoint's intended public use and acceptable request frequency.
3. Fetch and inspect representative content with a standards-compliant parser.
4. Determine timezone, stable event identifiers, recurrence, cancellations, and update behavior.
5. Define event visibility and audience rules, including registration-required and restricted events.
6. Record a verification timestamp and approved polling interval.
7. Only then change `access_status` to `approved` and enable polling.

## Research limitations

- This is a discovery pass, not a legal review or permission determination.
- HTML pages may be redesigned or backed by third-party platforms.
- No organization has been represented as endorsing or formally participating in CivicCal.
- No source in this initial set is enabled for automated polling.




Additional library source: `mokena-library-board-meetings` at https://mokenalibrary.org/library-board. This is a separate public Board of Trustees schedule; its December 2026 date is unresolved (schedule says Dec 15; agendas/minutes list Dec 22).
## Library ingestion fallback

The library-wide calendar feed is not a dependency. CivicCal's fallback is to ingest the public LibraryCalendar List/Upcoming views and linked detail pages from verified offline HTML snapshots, supplement selected events with their individual iCalendar exports, and accept manually transcribed source-linked JSON snapshots when raw HTML is unavailable. This remains an offline preparation path until source access review and genuine HTML fixtures are complete. See [Mokena library calendar source research](mokena-library-calendar-source.md) for field mapping and duplicate rules.
