# Capture-to-Parser Handoff

## Purpose

`scripts/parse_capture.py` processes an archived capture without making a network request. It verifies capture metadata and the SHA-256 of the raw payload, chooses an existing parser, and writes a separate JSON parse result.

## Run

After a permitted one-shot capture:

```sh
python scripts/parse_capture.py \
  --source-id example-source \
  --capture-metadata data/captures/example-source/capture-<timestamp>-<hash>.json \
  --adapter auto \
  --output data/processed/example-source.json
```

The capture metadata file is the handoff contract. Its `raw_payload_file` must identify a payload in the same archive directory. The source ID must match the registry record and capture metadata. The payload is re-hashed before parsing; a mismatch stops processing.

## Parser dispatch

- `auto`: ICS sources use the RFC 5545 parser; HTML sources use the generic Schema.org JSON-LD extractor.
- `mokena_park`: reviewed Mokena Park District Upcoming Events adapter.
- `village`: Village MunicipalCMS listing/detail adapter.
- Other source types require a future explicit adapter; the handoff does not guess.

Use an explicit adapter for source-specific HTML. The Village listing parser emits detail links rather than event dates; a detail page is the authoritative event observation. Fetching those links is a separate future capture step and is not performed by this command.

## Output

The output envelope contains:
- CivicCal parse-result format version.
- Registry source ID and selected adapter.
- Capture metadata reference, timestamp, final URL, and payload hash.
- Full parser output, including warnings and limitations.

Parser output is separate from the raw archive. Re-running the same capture can regenerate the parse result. This command does not change the source registry, capture metadata, raw payload, canonical event store, or publication feeds.

## Boundaries

- Offline only; no network access.
- No polling or scheduler.
- No database writes.
- No event merging or deletion.
- No canonical event persistence or publication.
- No guessed timezone, event dates, or missing values.
