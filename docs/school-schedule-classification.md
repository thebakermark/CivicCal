# School Schedule Exception Classification

## Purpose

`scripts/classify_school_schedule.py` adds a conservative, deterministic classification to normalized events from registered school sources. Its immediate purpose is to surface dates that change student attendance: no-school days, school breaks, early dismissals, half days, late starts, and teacher institute/in-service days.

## Usage

Run after normalization:

```sh
python scripts/classify_school_schedule.py data/normalized/school-events.json \
  --output data/processed/school-schedule-events.json
```

The command reads `data/sources.json` by default and refuses to classify a source unless its registered organization has type `school`.

## Output

Each event receives a `school_schedule` object containing:

- `is_schedule_exception`
- `schedule_type`
- `student_attendance`
- `classification` and `matched_rule`
- A short rationale

The document also receives a count summary. Original title, description, dates, source record, and provenance remain unchanged.

## Rules and safeguards

- Explicit no-school/closure wording is recognized.
- E-learning and remote-learning days are distinct from no-school days.
- Named seasonal breaks are recognized.
- Early dismissal/release, half-day, and delayed-start wording are distinct.
- Teacher institute, in-service, professional-development, and teacher-workday wording is flagged for attendance confirmation unless the source explicitly states no school.
- Unmatched events remain unclassified; the classifier does not infer that a holiday or staff event means students are off.
- Matching is deterministic and local. No model, network request, date inference, event deletion, or calendar publication is involved.

This is a first-pass classifier, not a substitute for checking the district's published calendar legend or school-specific exceptions. Rules should be expanded only against real source examples and regression tests.


## Verified Summit Hill calendar example

`data/fixtures/summit-hill-2026-27-school-schedule.json` is a manual, source-verified transcription of the one-page 2026–27 District Calendar linked from the official Summit Hill School District 161 School Calendar page. It records 18 schedule-related entries, including half days, no-school days, conferences, Thanksgiving, winter break, spring break, and a polling-place closure limited to Mary Drew Early Learning Center.

The fixture preserves the exact published wording, inclusive date ranges, and school scope. It deliberately does not invent dismissal times. The August teacher institute dates remain marked for student-attendance confirmation because the PDF labels them teacher institute days but does not explicitly say "No School" on those rows.

The fixture is a verified reference dataset for rule tests, not a claim that PDF extraction is automated. The PDF is the source of truth; the transcription should be compared with any future captured calendar feed before publication.


## Mokena SD 159 extracted schedule example

`data/fixtures/mokena-sd159-2026-27-schedule-exceptions.json` is a schedule-focused transcription from the user-provided official SD 159 iCalendar export. The source export contained 5,936 VEVENT records and covered November 3, 2026 through December 25, 2099. The fixture preserves source UIDs for every represented schedule record, including repeated entries; it does not delete or merge source events.

The captured school-schedule entries include:

- November 3, 2026: MES and MIS in-person; MJHS e-learning (school-specific wording in the source description)
- November 12–13: parent/teacher conferences and no student attendance
- November 20 and December 18: MES early dismissal at 12:00 PM; the export also has generic early-dismissal records whose school scope is not explicit
- November 23–27: Thanksgiving break
- December 21, 2026–January 1, 2027: winter break
- January 4: teacher institute day, explicitly no school
- January 5: MES students return from winter break
- January 15, February 12, March 12: MES early dismissal at 12:00 PM
- January 18 and February 15: no school
- March 26–April 2: spring break
- April 16: generic early-dismissal entries; school scope is not explicit in the captured records
- May 28: MES last day of school, early dismissal at 12:00 PM

The capture begins November 3, 2026, so this fixture is **not a complete 2026–27 school-year calendar**. The approved district calendar has now been retrieved through the district's public Google Drive viewer and transcribed separately in `data/fixtures/mokena-sd159-2026-27-approved-calendar.json`. It fills the missing August–October dates and adds the April 6 school-specific e-learning exception. The iCalendar export's VTIMEZONE declares America/Chicago, but individual DTSTART/DTEND values are floating (no TZID or UTC marker); CivicCal preserves that distinction rather than assigning a timezone by assumption. The iCalendar export's VTIMEZONE declares America/Chicago, but individual DTSTART/DTEND values are floating (no TZID or UTC marker); CivicCal preserves that distinction rather than assigning a timezone by assumption.

This fixture is derived from the actual export, not from an automated live capture. Its hash and capture metadata are recorded in the fixture for reproducibility. Source event UIDs remain intact for later identity/reconciliation work.


## Mokena SD 159 approved calendar transcription

`data/fixtures/mokena-sd159-2026-27-approved-calendar.json` is a manual transcription of the district-approved 2026–27 calendar PDF linked from the district's March 19, 2026 calendar announcement. The public Google Drive viewer rendered the one-page calendar as an image.

The calendar summary records 176 student attendance days, four teacher institute days, nine school-improvement/early-dismissal days, and five emergency days. It confirms August 17–18 as teacher institute days, August 19 as the first student day, October 9 as a teacher institute day, and January 4 as a teacher institute day. It also identifies the nine early-dismissal dates and preserves five emergency days as contingency dates rather than scheduled attendance days.

The approved calendar explicitly states: “MES, MIS will be in session, MJHS E-Learning Day 11/3, 4/6.” CivicCal represents November 3 and April 6 as mixed-by-school learning schedules, not district-wide closures. The November 3 entry is also present in the iCalendar-derived fixture; April 6 is newly added from the approved calendar transcription.

The calendar image does not provide exact dismissal times. September 4 school-specific times are recorded in the live-feed supplement: the attached district graphic lists MJHS 10:55 AM, MIS 11:30 AM, and MES 12:00 PM; its date is cross-checked using the post announcing tomorrow as the first early-dismissal day and the approved calendar's September 4 marker. Do not infer times for October 30. This transcription is a reference fixture, not an automated PDF parser or a live capture.
