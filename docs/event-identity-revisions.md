# Event Identity and Revision Tracking

## Purpose

`scripts/track_event_identity.py` adds a deterministic, offline reconciliation step after normalization. It tracks an event across captures from the same registered source and records material revisions without merging records across sources.

It writes a portable JSON state snapshot as a prototype for the later SQLite repository. No database is created or deployed.

## Stable identity

A stable tracked identity is created only when the normalized record has a publisher-provided `source_event_id` (such as an ICS UID or Village MunicipalCMS `cid`). The identity key is a SHA-256 digest of:

- CivicCal `source_id`
- Publisher `source_event_id`
- Recurrence instance identifier, when present

The CivicCal event ID is derived from that source-scoped identity key. It remains stable when mapped event content changes. The same publisher ID in two different registered sources produces two separate CivicCal event IDs.

A record without a stable publisher ID is retained as an unkeyed observation and flagged for review. CivicCal does not pretend that a title/date fingerprint is a permanent identity. This currently applies to the Park District adapter, which extracts event cards but does not yet identify a stable per-event publisher ID.

## Revision rules

The material revision fingerprint includes normalized title, description, start/end, all-day/time semantics, timezone, location, event and registration links, registration deadline, cost/free status, event status, attendance mode, audience, organizer, image, categories, and recurrence metadata.

Capture metadata and unmapped source-record details are excluded from the material fingerprint. They remain preserved in the current event record and can be reviewed without creating a false material revision.

- First observation creates revision 1 (`created`).
- Same source identity and same material fingerprint in a new capture updates last-seen/observation history but creates no revision.
- Same source identity with changed material fields appends a revision and preserves the previous revision.
- Reprocessing the same capture is idempotent.
- Duplicate source identities within one capture are reported as conflicts and are not written over one another.
- Missing events are not cancelled or deleted. Absence tracking is deliberately deferred until source adapters can assert complete snapshots.
- Cross-source matching and merging are not performed.

## Recurrence

For a source UID with a recurrence instance identifier, the instance identifier is included in the source-scoped identity key so separate instances do not overwrite each other. The recurring master (without an instance identifier) remains its own record. This does not expand RRULEs or generate occurrences.

## Usage

First normalize a parser result:

```sh
python scripts/normalize_events.py parsed-events.json --output normalized.json
```

Then process the normalized result using a JSON state file:

```sh
python scripts/track_event_identity.py normalized.json --state data/identity/state.json --output identity-result.json
```

The state file is created on first use and updated on each new capture. For a dry review, pass a separate path with `--state-output` so the prior state remains unchanged.

## State model

The prototype state stores:

- Source-scoped stable event identity.
- Current normalized event.
- First/last seen timestamps.
- Observation IDs.
- Append-only material revision entries with fingerprints and changed values.
- Unkeyed observations and source-identity conflicts.
- Processed capture keys for idempotency.

This JSON shape is a prototype contract, not the final SQLite schema. The storage implementation should preserve these semantics.

## Safety boundaries

This tool is offline. It does not fetch or parse sources, assign missing IDs, infer event continuity from title/date, mark missing events cancelled, merge cross-source records, publish, or write a database.
