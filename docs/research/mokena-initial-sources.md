# Mokena Initial Calendar Source Research

**Research date:** 2026-11-03  
**Scope:** Initial source discovery only. This document does not grant permission to automate collection.

## Discovered source records

| Organization | Registry source ID | Source type | Discovery evidence | Current state |
|---|---|---|---|---|
| Village of Mokena | `village-of-mokena-events` | HTML | Official site links to its Calendar of Events page. The calendar currently lists municipal and community items. | Review required; polling off |
| Mokena Community Public Library District | `mokena-library-events` | HTML | Official library site links to its Available Programs Calendar. The public calendar exposes upcoming programs and registration filters. | Review required; polling off |
| Mokena Community Park District | `mokena-park-district-events` | HTML | Official district site links to an Upcoming Events page. The page includes dates, eligibility, fees, and preregistration details. | Review required; polling off |
| Mokena School District 159 | `mokena-sd159-events-ical` | ICS | Official district Events page exposes a “Click to Download Calendar” link. Its target is an iCalendar-generation endpoint. | Review required; polling off |

## Observations that affect normalization

- Library events can have registration requirements, age groups, audience restrictions, and multi-day date ranges. Preserve those details rather than reducing each listing to title and start time.
- Park district listings may include resident eligibility, registration deadlines, fees, and age restrictions. These should be distinct fields or clearly retained in event notes.
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


