# Mokena SD 159 — 2026–27 Calendar Verification

**Reviewed:** 2026-11-04  
**Organization:** Mokena School District 159  
**Purpose:** Reconcile the 2026–27 school schedule dates missing from the user-provided iCalendar snapshot, which begins on 2026-11-03.

## Authoritative district evidence located

The district's own Apptegy live-feed pages contain these schedule notices:

| Date | District statement | Interpretation |
|---|---|---|
| 2026-09-07 | “There is no school on Monday due to Labor Day.” | No student attendance; date resolved to Monday, September 7, 2026. |
| 2026-10-09 | “There is no school on Friday, October 9th due to Teachers Institute…” | No student attendance. |
| 2026-10-12 | “…and Monday, October 12th due to a school holiday.” | No student attendance. |
| 2026-10-13 | “…We will see everyone back on Tuesday, October 13th!” | District return-to-school date. |

District live-feed source pages:
- https://mis.mokena159.org/live-feed
- https://mjhs.mokena159.org/o/mis/live-feed
- https://mes.mokena159.org/live-feed

The September Labor Day reminder and October 9–13 notice are published by Mokena School District 159 on its own school-site live feeds. These notices are stronger evidence than third-party calendar transcriptions.

## Calendar PDF candidate rejected

A web-indexed PDF appeared under the title “2026-2027 School Calendar” and was initially considered a possible copy of the district calendar:

https://d16k74nzx9emoe.cloudfront.net/d7f61342-5f69-4bc4-850c-5bd37c9bab92/26.27%20School%20Calendar%20FInal%20Revised%203.23.2026.pdf

**Do not use this PDF as Mokena SD 159 evidence.** Its extracted contents identify NEOEA Day, Ohio-style grade bands (PK–12), a 174-instructional-day calendar, and a different August start sequence. These details do not match Mokena SD 159. The search result title was a false match. The district's own March 19, 2026 announcement links the approved calendar at:

https://drive.google.com/file/d/10XU79esFWvZ8pJ-IhHGh0w-TVtgkoUdq/view

That Google Drive document still needs to be retrieved and independently checked; the rejected CloudFront PDF is not a substitute.

## Data handling decision

- Keep the existing iCalendar-derived schedule fixture unchanged for now.
- The iCalendar snapshot begins on 2026-11-03, so it cannot establish August–October coverage.
- Treat the four district live-feed dates above as independently verified supplemental evidence. Add them to the normalized school-schedule dataset only with explicit live-feed provenance, not fabricated iCalendar UIDs.
- Do not import the third-party calendar index's remaining August–October entries without district confirmation; that index has known conflicts with the district's own feed.
- Do not enable network retrieval or polling. The SD159 automated-access consent gate remains unchanged (consent_granted=false, polling_enabled=false).

## Related official calendar announcement

The district announced on 2026-03-19 that the Board of Education approved the 2026–2027 school-year calendar:

https://www.mokena159.org/article/2775307

The announcement points to the Google Drive calendar link above. The announcement verifies approval and the existence of the calendar, but not individual schedule dates by itself.
