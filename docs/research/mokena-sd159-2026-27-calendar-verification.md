# Mokena SD 159 — 2026–27 Calendar Verification

**Reviewed:** 2026-11-04  
**Organization:** Mokena School District 159  
**Purpose:** Reconcile the 2026–27 school schedule dates missing from the user-provided iCalendar snapshot, which begins on 2026-11-03.

## Authoritative district evidence located

The district-approved 2026–27 calendar PDF, accessed through the district's public Google Drive viewer, is now the primary full-year reference. The district's own Apptegy live-feed pages and district-created graphics provide supplemental confirmation for dates and notices:

| Date | District statement | Interpretation |
|---|---|---|
| 2026-08-17–18 | Approved calendar marks both dates as Teacher Institute Days; the calendar legend counts four institute days. | Teacher Institute Days; no student attendance. |
| 2026-08-19 | “What a great morning at all of our schools as we welcomed our students to the 2026-2027 school year!” | First day of school; district-wide. |
| 2026-09-04 | September district dates graphic: “EARLY RELEASE DAY.” | Early release; exact dismissal times are not attached because the separate times graphic's date association is not conclusive. |
| 2026-09-07 | “NO SCHOOL–LABOR DAY”; live-feed reminder says there is no school Monday due to Labor Day. | No student attendance; date resolved to Monday, September 7, 2026. |
| 2026-10-09 | “NO SCHOOL TEACHERS INSTITUTE”; explicit live-feed reminder confirms Friday, October 9. | No student attendance. |
| 2026-10-12 | “NO SCHOOL SCHOOL HOLIDAY”; explicit live-feed reminder confirms Monday, October 12. | No student attendance. |
| 2026-10-13 | “We will see everyone back on Tuesday, October 13th!” | District return-to-school date. |
| 2027-04-06 | Approved calendar note: “MES, MIS will be in session, MJHS E-Learning Day 11/3, 4/6.” | MES and MIS in person; MJHS e-learning. |
| 2026-10-30 | October district dates graphic: “EARLY DISMISSAL DAY.” | Early dismissal; exact times not stated in the graphic. |

District live-feed source pages:
- https://mes.mokena159.org/o/mis/live-feed?page_no=2
- https://mes.mokena159.org/o/mis/live-feed
- https://mis.mokena159.org/live-feed
- https://mjhs.mokena159.org/o/mis/live-feed
- https://mes.mokena159.org/live-feed

District-created graphics:
- September dates: https://core-docs.s3.amazonaws.com/mokena_school_district_159_ar/live_feed_image/image/29325072/large_DIstrict_Dates__10_.png
- October dates: https://core-docs.s3.amazonaws.com/mokena_school_district_159_ar/live_feed_image/image/30848899/large_DIstrict_Dates__14_.png
- October no-school reminder: https://core-docs.s3.amazonaws.com/mokena_school_district_159_ar/live_feed_image/image/30662630/large_No_School__7_.png

The district's live-feed posts and graphics are direct district sources. They supersede third-party calendar transcriptions for the dates they explicitly identify.

## Supplemental fixture

The supplemental evidence is recorded separately in:

`data/fixtures/mokena-sd159-2026-27-live-feed-supplement.json`

This is intentionally separate from the iCalendar-derived fixture. These live-feed records have no iCalendar UIDs, and CivicCal must not fabricate UIDs or merge these records into the source-feed identity history. The supplement preserves each statement and links it to the district page or graphic that supports it.

The September early-dismissal times are now resolved: the official live-feed post says tomorrow is the first Early Dismissal Day and includes a district-created graphic listing MJHS 10:55 AM, MIS 11:30 AM, and MES 12:00 PM. The approved calendar identifies September 4 as the first early-dismissal date, linking the post and graphic to September 4. These times are recorded in the live-feed supplement. October 30 remains without verified times.

## Calendar PDF candidate rejected

A web-indexed PDF appeared under the title “2026-2027 School Calendar” and was initially considered a possible copy of the district calendar:

https://d16k74nzx9emoe.cloudfront.net/d7f61342-5f69-4bc4-850c-5bd37c9bab92/26.27%20School%20Calendar%20FInal%20Revised%203.23.2026.pdf

**Do not use this PDF as Mokena SD 159 evidence.** Its extracted contents identify NEOEA Day, Ohio-style grade bands (PK–12), a 174-instructional-day calendar, and a different August start sequence. These details do not match Mokena SD 159. The search result title was a false match. The district's own March 19, 2026 announcement links the approved calendar at:

https://drive.google.com/file/d/10XU79esFWvZ8pJ-IhHGh0w-TVtgkoUdq/view

The district's Google Drive viewer now successfully renders the approved one-page calendar as an image. Its manual transcription is preserved in `data/fixtures/mokena-sd159-2026-27-approved-calendar.json`. The rejected CloudFront PDF remains excluded.

## Data handling decision

- Keep the existing iCalendar-derived schedule fixture unchanged. It begins November 3, 2026 and retains its original source UIDs.
- Preserve the approved calendar transcription in its own fixture; do not fabricate iCalendar UIDs for calendar-image entries.
- The approved calendar identifies April 6, 2027 as a mixed schedule: MES/MIS in session, MJHS e-learning. This date was not in the earlier schedule-focused iCalendar transcription.
- Use the separate live-feed supplement for the seven district-confirmed dates above. Do not fabricate iCalendar UIDs.
- The approved calendar resolves August 17–18 as Teacher Institute Days and confirms the first student day is August 19. Do not rely on the third-party calendar index where it conflicts with district evidence.
- Do not infer dismissal times from a graphic whose association with a specific date is unclear.
- Do not enable network retrieval or polling. The SD159 automated-access consent gate remains unchanged (`consent_granted=false`, `polling_enabled=false`).

## Related official calendar announcement

The district announced on 2026-03-19 that the Board of Education approved the 2026–2027 school-year calendar:

https://www.mokena159.org/article/2775307

The announcement points to the Google Drive calendar link above. The announcement verifies approval and the existence of the calendar, but not individual schedule dates by itself.


## Approved calendar transcription

The official district calendar PDF is available at:

https://drive.google.com/file/d/10XU79esFWvZ8pJ-IhHGh0w-TVtgkoUdq/view

The district's March 19, 2026 announcement states that the Board approved the 2026–2027 school-year calendar and links this file. The Google Drive viewer rendered the single-page calendar as an image during this review. Its manual transcription is stored at:

`data/fixtures/mokena-sd159-2026-27-approved-calendar.json`

Key reconciliation results:

- August 17–18 are Teacher Institute Days; August 19 is the first student day.
- The four Teacher Institute Days are August 17–18, October 9, and January 4.
- The nine school-improvement/early-dismissal dates are September 4, October 30, November 20, December 18, January 15, February 12, March 12, April 16, and May 28.
- The calendar explicitly states that MES and MIS are in session while MJHS has e-learning on November 3 and April 6.
- The calendar summary lists 176 student attendance days and five emergency days (June 1–4 and June 7, 2027). Emergency days are contingency dates, not scheduled attendance days unless activated.
- Exact dismissal times are not printed in the calendar image. September 4 times are supported by the district live-feed post and its attached times graphic; October 30 times remain unknown. Retain only source-backed times.
