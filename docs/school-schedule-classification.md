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
- Named seasonal breaks are recognized.
- Early dismissal/release, half-day, and delayed-start wording are distinct.
- Teacher institute, in-service, professional-development, and teacher-workday wording is flagged as no student attendance, with a rationale reminding reviewers to confirm the district's actual student schedule.
- Unmatched events remain unclassified; the classifier does not infer that a holiday or staff event means students are off.
- Matching is deterministic and local. No model, network request, date inference, event deletion, or calendar publication is involved.

This is a first-pass classifier, not a substitute for checking the district's published calendar legend or school-specific exceptions. Rules should be expanded only against real source examples and regression tests.
