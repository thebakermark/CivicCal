# Mokena SD 159 — 2026–27 Calendar Verification

**Reviewed:** 2026-11-04  
**Organization:** Mokena School District 159  
**Purpose:** Reconcile the 2026–27 school schedule dates missing from the user-provided iCalendar snapshot, which begins on 2026-11-03.

## Authoritative district evidence located

The district's own Apptegy live-feed pages and district-created graphics provide the following supplemental schedule evidence:

| Date | District statement | Interpretation |
|---|---|---|
| 2026-08-19 | “What a great morning at all of our schools as we welcomed our students to the 2026-2027 school year!” | First day of school; district-wide. |
| 2026-09-04 | September district dates graphic: “EARLY RELEASE DAY.” | Early release; exact dismissal times are not attached because the separate times graphic's date association is not conclusive. |
| 2026-09-07 | “NO SCHOOL–LABOR DAY”; live-feed reminder says there is no school Monday due to Labor Day. | No student attendance; date resolved to Monday, September 7, 2026. |
| 2026-10-09 | “NO SCHOOL TEACHERS INSTITUTE”; explicit live-feed reminder confirms Friday, October 9. | No student attendance. |
| 2026-10-12 | “NO SCHOOL SCHOOL HOLIDAY”; explicit live-feed reminder confirms Monday, October 12. | No student attendance. |
| 2026-10-13 | “We will see everyone back on Tuesday, October 13th!” | District return-to-school date. |
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

A district-created graphic also gives dismissal times of MJHS 10:55 AM, MIS 11:30 AM, and MES 12:00 PM. However, the accessible post context does not conclusively establish that this graphic belongs to September 4, so those times are deliberately not assigned to that date.

## Calendar PDF candidate rejected

A web-indexed PDF appeared under the title “2026-2027 School Calendar” and was initially considered a possible copy of the district calendar:

https://d16k74nzx9emoe.cloudfront.net/d7f61342-5f69-4bc4-850c-5bd37c9bab92/26.27%20School%20Calendar%20FInal%20Revised%203.23.2026.pdf

**Do not use this PDF as Mokena SD 159 evidence.** Its extracted contents identify NEOEA Day, Ohio-style grade bands (PK–12), a 174-instructional-day calendar, and a different August start sequence. These details do not match Mokena SD 159. The search result title was a false match. The district's own March 19, 2026 announcement links the approved calendar at:

https://drive.google.com/file/d/10XU79esFWvZ8pJ-IhHGh0w-TVtgkoUdq/view

That Google Drive document still needs to be retrieved and independently checked; the rejected CloudFront PDF is not a substitute.

## Data handling decision

- Keep the existing iCalendar-derived schedule fixture unchanged. It begins November 3, 2026 and retains its original source UIDs.
- Use the separate live-feed supplement for the seven district-confirmed dates above. Do not fabricate iCalendar UIDs.
- Do not import the third-party calendar index's remaining August–October entries without district confirmation. In particular, August 17–18 teacher institute dates remain unresolved because no readable official district evidence confirming student attendance status was found in this review.
- Do not infer dismissal times from a graphic whose association with a specific date is unclear.
- Do not enable network retrieval or polling. The SD159 automated-access consent gate remains unchanged (`consent_granted=false`, `polling_enabled=false`).

## Related official calendar announcement

The district announced on 2026-03-19 that the Board of Education approved the 2026–2027 school-year calendar:

https://www.mokena159.org/article/2775307

The announcement points to the Google Drive calendar link above. The announcement verifies approval and the existence of the calendar, but not individual schedule dates by itself.
