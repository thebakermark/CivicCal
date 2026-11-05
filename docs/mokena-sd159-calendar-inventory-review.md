# Mokena SD 159 Calendar Inventory Review

## Scope and source

This review covers the archived district iCalendar payload `mokena_school_district_159_events.ics`, captured 2026-11-03T23:30:43Z. It is an archive review, not a fresh network capture. The payload SHA-256 is `33cf370e9abde1cfddef88e77e82babce747e7e1f7313ebcea4248f8b1fb2774`.

The file contains 5,936 VEVENT records. The 2026–27 review window is 2026-08-01 through 2027-06-30 inclusive. Because the archived payload begins on November 3, 2026, it cannot establish coverage for August–October 2026.

## Verified inventory

- 216 VEVENT records fall in the 2026–27 review window.
- All 216 have a publisher UID, and all 216 UIDs are unique within this window.
- 81 distinct raw SUMMARY title strings occur in the window (after trimming surrounding whitespace for this count).
- All event date-times in the reviewed records are floating local values; no timezone is assigned by this review.
- The feed-level VTIMEZONE declares America/Chicago, but individual DTSTART/DTEND values do not carry TZID or UTC markers. Preserve this distinction.
- The inventory includes schedule exceptions and ordinary school/community calendar events. Do not treat the entire inventory as a school-closure calendar.

The previous working estimate of 150 records was incorrect. The verified count is 216. Use this count in subsequent work.

## Broad title-family counts

These are mutually exclusive, first-match descriptive buckets, not formal CivicCal categories. They sum to 216:

| Family | Records |
|---|---:|
| School schedule / attendance wording | 62 |
| Board / committee governance | 43 |
| STEAM | 35 |
| Other / awareness / community | 29 |
| PTA / parent groups | 24 |
| Arts / music / performance | 12 |
| Student activities / trips / athletics | 11 |
| **Total** | **216** |

The original SUMMARY text remains authoritative. These buckets are inventory aids only; they must not overwrite event titles or determine publication approval.

## Timed duplicate-candidate groups

There are 17 groups with multiple VEVENT records sharing the exact same floating DTSTART date and time. They contain **64 source records** in total. Every source record and UID must remain intact. The shared start is a candidate relationship signal, not permission to merge.

| DTSTART (floating local) | Records | Title pattern |
|---|---:|---|
| 2026-11-10 19:00 | 3 | Three differently titled PTA listings |
| 2026-11-11 19:00 | 5 | Three “Mokena School Board Meeting”; two “School Board Meeting” |
| 2026-11-12 14:00 | 2 | MES Parent/Teacher Conferences; Parent/Teacher Conferences |
| 2026-11-13 08:00 | 2 | MES Parent/Teacher Conferences; Parent/Teacher Conferences |
| 2026-12-08 19:00 | 3 | Three differently titled PTA listings |
| 2026-12-16 19:00 | 4 | Three “Mokena School Board Meeting”; one “School Board Meeting” |
| 2027-01-12 19:00 | 3 | Three differently titled PTA listings |
| 2027-01-20 19:00 | 5 | Three “Mokena School Board Meeting”; two “School Board Meeting” |
| 2027-02-09 19:00 | 3 | Three differently titled PTA listings |
| 2027-02-17 19:00 | 5 | Three “Mokena School Board Meeting”; two “School Board Meeting” |
| 2027-03-09 19:00 | 3 | Three differently titled PTA listings |
| 2027-03-17 19:00 | 5 | Three “Mokena School Board Meeting”; two “School Board Meeting” |
| 2027-04-13 19:00 | 3 | Three differently titled PTA listings |
| 2027-04-21 19:00 | 5 | Three “Mokena School Board Meeting”; two “School Board Meeting” |
| 2027-05-11 19:00 | 3 | Three differently titled PTA listings |
| 2027-05-19 19:00 | 5 | Three “Mokena School Board Meeting”; two “School Board Meeting” |
| 2027-06-16 19:00 | 5 | Three “Mokena School Board Meeting”; two “School Board Meeting” |

Group totals: eight board-meeting groups (39 records), seven PTA groups (21 records), and two conference groups (4 records). The board and PTA groups have highly consistent start/end times and title patterns across repeated dates. Most have empty descriptions and locations; one PTA variant supplies “Mokena, IL, USA” while the other two are blank. This supports recording mirrored-listing candidates, but does not establish source relationships or justify destructive deduplication.

## Other same-date overlaps

Additional date-only DTSTART collisions exist, including a holiday and unrelated observances, report-release entries alongside early dismissal, break records with overlapping school-specific records, and unrelated events on the same date. These are not included in the 17 timed duplicate-candidate groups. A shared date alone is not evidence of duplication.

Examples requiring separate event identities include:
- November 20, 2026: MES early dismissal and MES report cards released.
- November 23, 2026: Thanksgiving break and school-specific/no-school records.
- January 4, 2027: multiple teacher-institute/no-school representations.
- January 18, 2027: Martin Luther King Jr. Day/no-school records and an unrelated birthday entry.
- February 15, 2027: Presidents’ Day/no-school records and Susan B. Anthony’s Birthday.
- April 22, 2027: a seventh-grade Springfield trip and Earth Day.
- May 27, 2027: early-childhood last day and MES Carnival.

## Processing and publication boundary

- Preserve every source observation, UID, original title, date/time string, end value, location, description, URL, and recurrence property.
- Keep floating date-times floating. Do not infer America/Chicago as a per-event TZID.
- Treat the 17 timed groups as review candidates only. Do not merge, suppress, delete, or rewrite source events.
- Do not infer cancellations from absence.
- Keep approved-calendar transcription records separate from ICS-derived observations.
- This inventory is not an approval manifest and does not authorize publication.
- Do not use live feeds, announcements, news, or other non-calendar communications as event sources. This review uses only the archived iCalendar event records and the separately maintained approved-calendar transcription.

## Remaining capture limitation

A new authorized network capture was not available to this review. The MIME type `text/calendar` is appropriate for an iCalendar response; a reader that rejects that MIME type is a reader limitation, not proof that the source is malformed. The archived capture is valid and internally consistent, but it is not evidence of the source's current live state. A fresh network capture and subsequent offline ingestion remain separate steps.
