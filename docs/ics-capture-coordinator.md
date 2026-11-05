# One-shot iCalendar Capture Coordinator

## Purpose

`scripts/capture_ics_source.py` connects the registered-source capture utility, raw archive, RFC 5545 parser, canonical event normalizer, and source snapshot validator for a single iCalendar feed.

It is intended for the Summit Hill SD 161 feed records and any later registered source explicitly configured with a `single_feed` completeness profile. It is not a scheduler or a publisher.

## Run

From the repository root, for a source whose registry gates have been deliberately approved:

```sh
python scripts/capture_ics_source.py \
  --source-id summit-hill-sd161-events-ical \
  --archive-dir data/captures \
  --output data/processed/summit-hill-district-events.json
```

The current Summit Hill source records remain `review_required`, so the command stops before making a network request. This example documents the interface; it does not authorize live capture.

For a source that has been independently verified to publish a genuinely empty calendar, an operator may explicitly attest to the empty feed:

```sh
python scripts/capture_ics_source.py \
  --source-id example-empty-ics-feed \
  --confirm-empty-snapshot \
  --output data/processed/example-empty-feed.json
```

That flag does not override `allow_complete_snapshot: false` in the source policy.

## Summit Hill SD 161 request URL

The official Download .ICS link for District Events resolves to `https://www.summithill.org/apps/events/ical/?id=0`. The official Google Calendar subscription link wraps the same feed in a `webcal://` URL and dynamically adds a `cb` timestamp. Keep the stable URL in the source registry and never store that generated value as source identity. Add a fresh cache-buster to individual requests only if direct HTTP testing shows it is needed; otherwise preserve ordinary ETag/Last-Modified behavior. See [the request-contract research note](research/summit-hill-ical-request.md).

## Workflow

1. The command loads the source through the existing registry eligibility and consent gates.
2. It requires an `ics` source type and exactly one matching `single_feed` completeness profile.
3. It validates the registered HTTPS URL against the source host/path allowlist.
4. It fetches exactly one feed; redirect destinations must remain inside that same allowlist.
5. It archives the original response bytes by SHA-256 and writes capture metadata.
6. It verifies a complete `VCALENDAR` envelope and parses VEVENT records with the existing dependency-free parser.
7. It normalizes each event while retaining UID, recurrence metadata, original source fields, temporal semantics, and capture provenance.
8. It builds a one-feed snapshot manifest and runs the existing completeness validator.
9. It writes one normalized JSON document with parser warnings, manifest evidence, completeness result, and archive reference.

## Safety and data handling

- The source registry remains authoritative. `review_required`, `blocked`, and consent-required sources cannot be bypassed by this coordinator.
- `polling_enabled` is not changed or used to enable repeated access.
- The coordinator does not send conditional requests. A 304 response, if returned by the server, is archived as not-modified metadata but is not treated as a newly parsed snapshot.
- A response without a complete `BEGIN:VCALENDAR` / `END:VCALENDAR` envelope is rejected.
- Parser warnings make the page parse status partial and prevent a complete snapshot.
- UID is preserved as the source event ID. Missing UIDs remain unkeyed; CivicCal does not invent stable IDs.
- TZID, UTC, floating times, all-day dates, and recurrence fields are retained by the existing parser and normalizer. Floating times are not assigned a timezone.
- An empty feed requires the explicit `--confirm-empty-snapshot` operator assertion. That assertion still cannot override a disabled source completeness profile.
- No event is cancelled or deleted based on disappearance. No records are merged, published, or written to a database.

## Current boundary

All Summit Hill source profiles currently set `allow_complete_snapshot: false`. A successful one-shot capture can therefore produce parsed and normalized events while its completeness remains `unknown`. The feed payloads still need to be compared against the corresponding visible publisher calendars before any source policy is reconsidered.

## Mokena SD159 deployment profile

The Mokena SD159 Apptegy/Thrillshare source now has a conservative `single_feed` profile in `data/source-completeness.json`. Its exact host and path are allowlisted, but `allow_complete_snapshot` remains false until a fresh capture is reconciled against the district's visible calendar. A successful capture can therefore be parsed and normalized without treating missing events as cancellations.

The current source registry's structured fields read `access_status=approved`, `consent_required=true`, and `consent_granted=true`; however, its free-text notes still claim `consent_granted` remains false. The coordinator enforces the structured fields and does not interpret or rewrite notes. This contradiction must be reviewed by the operator/source owner before the first live capture. Do not change any authorization or polling flags as part of this deployment.

A manually invoked, restricted systemd unit is documented in [the deployment guide](../deploy/README.md). It runs the existing coordinator as a separate unprivileged account, writes only to raw-capture and report directories, and has no scheduler or publication path.
