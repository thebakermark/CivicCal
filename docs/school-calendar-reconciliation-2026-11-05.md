# School calendar offline reconciliation — 2026-11-05

## Processing result

- Mokena School District 159: 49 source observations retained across three independent evidence channels.
- SD 159 date-range candidate groups: 27 distinct exact inclusive date ranges. Grouping is for review only; it does not create canonical event identities or deduplicate source observations.
- Summit Hill School District 161: 18 source observations retained in a separate dataset.
- No cross-district merging was performed.

## SD 159 evidence channels

1. Approved 2026–27 calendar PDF transcription: 25 records.
2. Official district live-feed supplement: 7 records.
3. User-provided offline district ICS schedule transcription: 17 records.

The live-feed supplement shares six exact date ranges with the approved calendar. The ICS schedule transcription shares sixteen exact date ranges with the approved calendar. Two records add dates not present in the approved calendar transcription: October 13, 2026 (students return after the October holiday) from the live-feed supplement, and January 5, 2027 (students return after winter break) from the offline ICS transcription.

Same-date records are retained separately when wording, attendance, scope, or schedule classification differs. For example, the November 12–13 conference entries retain both the approved-calendar category and the ICS-derived no-student-attendance wording.

## Cross-district overlaps are not duplicates

Summit Hill is a different district and remains in its own observation set. Shared dates such as Labor Day, October 12, winter break, and spring break are not merged with SD 159. School-specific scope and attendance differ, including November 3 and several half-day / early-dismissal dates.

## Important unresolved differences

- SD 159 November 3: district-wide calendar notes a school-specific e-learning arrangement (MJHS remote; MES and MIS in person). Summit Hill's November 3 entry is a closure only at Mary Drew Early Learning Center.
- Summit Hill November 23–24: parent/teacher conference days; SD 159 is in Thanksgiving break.
- Summit Hill November 25–27: Thanksgiving holiday; SD 159's Thanksgiving break spans November 23–27.
- Summit Hill October 9 and several other dates are described as half-days / teacher in-service, while SD 159 classifies the same date as a no-student-attendance or early-dismissal day. These are district-specific schedules, not contradictions to resolve by merging.

## Guardrails and limitations

- The SD 159 ICS endpoint remains blocked for automated retrieval. Only the already user-provided local ICS export was used.
- The approved PDF and live-feed supplements are not assigned to the SD 159 ICS source ID. No new source registry records or IDs were invented.
- Summit Hill's PDF transcription is not represented as a captured ICS feed.
- Original event records, source UIDs, source wording, date ranges, scope, and attendance metadata are retained.
- Date-range grouping is a review aid, not stable event identity.
- No canonical event IDs, identity revisions, or lifecycle states were assigned because the relevant PDF/live-feed source records are not separately registered.
- No source registry authorization flags were modified. No network access, database writes, polling, publication, or deployment occurred.

## Files

- `data/processed/mokena-sd159-2026-27-calendar-observations.json`
- `data/processed/summit-hill-sd161-2026-27-calendar-observations.json`
