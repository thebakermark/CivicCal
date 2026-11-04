# Event Identity and Revision Tracking

## Purpose

`scripts/track_event_identity.py` adds a deterministic, offline reconciliation step after normalization. It tracks an event across captures from the same registered source and records material revisions without merging records across sources.

It writes state through the replaceable IdentityStateStore interface. The current backend is an atomic JSON file; database selection is deferred. No database is created or deployed.

## Stable identity

A stable tracked identity is created only when the normalized record has a publisher-provided `source_event_id` (such as an ICS UID or Village MunicipalCMS `cid`). The identity key is a SHA-256 digest of:

- CivicCal `source_id`
- Publisher `source_event_id`
- Recurrence instance identifier, when present

The CivicCal event ID is derived from that source-scoped identity key. It remains stable when mapped event content changes. The same publisher ID in two different registered sources produces two separate CivicCal event IDs.

A record without a stable publisher ID is retained as an unkeyed observation and flagged for review. CivicCal does not pretend that a title/date fingerprint is a permanent identity. This currently applies to the Park District adapter, which extracts event cards but does not yet identify a stable per-event publisher ID.

## Revision rules

The material revision fingerprint includes normalized title, description, start/end, all-day/time semantics, timezone, location, event and registration links, registration deadline, cost/free status, event status, attendance mode, audience, registration-required state, registration availability status, organizer, image, categories, and recurrence metadata.

Capture metadata and unmapped source-record details are excluded from the material fingerprint. They remain preserved in the current event record and can be reviewed without creating a false material revision.

- First observation creates revision 1 (`created`).
- Same source identity and same material fingerprint in a new capture appends a source observation and updates last-seen, but creates no material revision.
- Same source identity with changed material fields appends a revision and preserves the previous revision.
- Reprocessing the same capture is idempotent.
- Duplicate source identities within one capture are reported as conflicts and are not written over one another.
- Absence is recorded only when normalized input includes `snapshot.completeness: "complete"` and a non-empty `snapshot.evidence` explanation.
- An empty complete snapshot additionally requires `snapshot.empty_snapshot_confirmed: true`; this protects against empty parser output being mistaken for an empty publisher calendar.
- Partial, unknown, failed, and unchanged (HTTP 304) captures cannot mark events missing. The capture-to-parser handoff currently rejects 304 payloads, so no normalized document is produced from an unchanged response.
- A missing observation changes presence tracking only. It does not change publisher lifecycle status, create a material revision, cancel, or delete the event. Reappearance resets the current missing streak while retaining the history.
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

The state file is created on first use and updated on each new capture through the JSON backend documented in [Storage Interface](storage-interface.md). For a dry review, pass a separate path with `--state-output` so the prior state remains unchanged.

## State model

The normalized input may carry a source-level `snapshot` assertion. This assertion must be supplied by a trusted source adapter only after it can establish completeness; the generic parser does not infer it.

The prototype state stores:
- Append-only source observations for every keyed event in every newly processed capture, including unchanged observations.
- Append-only presence observations for events absent from explicitly complete snapshots, plus reappearance history.
- A separate lifecycle history recording creation and explicit publisher status transitions.

- Source-scoped stable event identity.
- Current normalized event.
- First/last seen timestamps.
- Observation IDs.
- Append-only material revision entries with fingerprints and changed values.
- Unkeyed observations and source-identity conflicts.
- Processed capture keys for idempotency.

This JSON shape is a prototype contract, not a database schema. The storage implementation should preserve these semantics.

## Safety boundaries

This tool is offline. It does not fetch or parse sources, assign missing IDs, infer event continuity from title/date, mark missing events cancelled, merge cross-source records, publish, or write a database.
