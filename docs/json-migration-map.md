# Current JSON State to Database Migration Map

**Status:** design reference only. No import code or database is implemented.

This document maps the repository's actual current files and state shape to the proposed database model. It is intentionally explicit about information that is not present in the current JSON state.

## 1. Migration inputs

| Current input | Contents | Destination |
|---|---|---|
| `data/sources.json` | `organizations[]`, `source_records[]`, region metadata | `organizations`, `sources`, plus region/configuration metadata |
| Identity-state JSON | `events` object keyed by identity key | `source_events` and child history tables |
| Identity-state JSON | `observations[]` | `event_observations` |
| Identity-state JSON | `unkeyed_observations[]` | `unkeyed_observations` |
| Identity-state JSON | `processed_captures[]` | `processed_captures` |
| Identity-state JSON | `presence_observations[]` | `presence_observations` |
| Publication manifest | `approved_event_ids[]` | `publication_approvals` |
| Archived capture metadata | Capture metadata and archive references, when available | `captures` |
| Retained ingestion result reports | Result-level identity conflicts and counts, when available | `identity_conflicts` and optional historical processing reports |

Do not assume there is only one identity-state file or one publication manifest in every environment. The migration tool must accept explicit paths and report exactly which inputs it imported.

## 2. Organization and source registry

- Import each `organizations[]` record using its existing `id` as `organization_id`.
- Import each `source_records[]` record using its existing `id` as `source_id`.
- Map `organization_id` as a foreign key; reject missing or ambiguous organization references.
- Preserve each complete original record as JSON in addition to promoted query columns.
- Preserve `region` and top-level registry schema metadata in a registry metadata record or versioned configuration snapshot.
- Do not infer source records from organization records or vice versa.
- Do not enable, unblock, consent, or schedule any source during migration.

## 3. Identity-state events

The current `events` value is an object whose keys are identity hashes. Each value includes:
- `event_id`, `identity_key`, `source_id`, `source_event_id`, `recurrence_instance_id`;
- `current` normalized event and `current_fingerprint`;
- `first_seen_at`, `last_seen_at`;
- `observation_ids[]`;
- nested `revisions[]`;
- `presence_status`, `missing_snapshot_count`, `missing_observation_history[]`;
- `lifecycle_status`, `lifecycle_history[]`.

Mapping:
- One row in `source_events` per object value.
- Preserve the object key and `identity_key`; validate they match rather than silently choosing one.
- Preserve `event_id` exactly.
- Store `current` in the full normalized JSON column; retain the current fingerprint and lifecycle/presence projection.
- Expand nested `revisions[]` into `event_revisions`, preserving array order as revision number order.
- Reconcile `missing_observation_history[]` against global `presence_observations[]`; do not import nested mirror records a second time. Missing facts are duplicated in both locations by the current tracker. Reappearance is also represented in both locations, with a sparse nested transition record and a global present record. Import the global record once and preserve/reconcile the nested mirror as described in [Relational Event-History Model](event-history-relational-model.md).
- Expand `lifecycle_history[]` into `lifecycle_transitions`, preserving order and source observation references.
- Resolve `observation_ids[]` against global observation rows; every referenced observation must exist and belong to the same source/event identity. Use the observation row's event foreign key as the authoritative relational link, not a second mutable array. Preserve the legacy array order as an explicit event sequence.

Do not create a second global/canonical event record. One current source event remains owned by one source.

## 4. Keyed observations

Each item in `observations[]` contains:
- `observation_id`;
- `source_id`, `source_event_id`, `identity_key`, `capture_key`;
- `observed_at`, `material_fingerprint`;
- full normalized `event`.

Expand one row per observation. Resolve `identity_key` to exactly one imported source event. Preserve the full event JSON and the original capture key. Do not collapse repeated observations with the same material fingerprint; unchanged observations are part of the source history. Assign an explicit per-event sequence using the event's observation_ids[] order and validate global observations not referenced by any event.

Validate that each observation ID is unique and that its source and identity key agree with its referenced source event.

## 5. Unkeyed observations

Each item in `unkeyed_observations[]` contains a deterministic observation ID, source ID, capture key, timestamp, normalized event, and review flags.

Import one row per item. Preserve the event JSON and review flags. These records have no source-event foreign key because a stable publisher identity was not established. Do not invent an event ID or match them by title/date during migration.

## 6. Processed capture tokens

The current `processed_captures[]` is a list of deterministic token strings, not a list of rich receipt objects.

- Preserve each token exactly.
- Validate uniqueness.
- Where the current token format can be verified, retain the source ID and capture key as explicit columns; otherwise preserve the token as opaque and report that the source/capture association could not be independently recovered.
- Do not invent a processing timestamp, capture row, or prior result payload.
- A later ingestion implementation should persist a richer receipt, including source, capture key, processed timestamp, and result summary.

## 7. Presence observations

The global `presence_observations[]` array is the authoritative import source. Event-level `missing_observation_history[]` is a legacy mirror: missing records are copied into both places, and reappearance is recorded in both places using different shapes. Import each global record once, reconcile the nested mirror by event/capture/timestamp/transition semantics, and report unmatched mirrors rather than double-counting them. Preserve nested-only fields in migration diagnostics or legacy JSON when needed for exact round-trip compatibility. See [Relational Event-History Model](event-history-relational-model.md) for the full reconciliation rules.

Import every item in `presence_observations[]` as an append-only row. Preserve all original keys in JSON even when selected fields are promoted to columns.

Resolve the source/event reference when an identity key is present. Preserve the capture key, observation time, presence value, reason, missing snapshot count, and completeness evidence. A presence record must never be converted into a cancellation.

Some historical presence records may be shaped differently (for example, a reappearance record versus a missing-snapshot record). Use a versioned mapping with validation; do not discard unknown fields or assume all records have identical keys.

## 8. Identity conflicts

The current tracker returns same-capture identity collisions in the processing result's `identity_conflicts[]`; it does not append them to the identity-state JSON.

- If a retained ingestion result report exists, import its conflict records with the report/capture provenance.
- If no report exists, record a migration coverage note that historical conflicts are unavailable.
- Never synthesize conflict rows from event titles, repeated publisher IDs in unrelated captures, or duplicate-candidate records.
- Future database-backed ingestion must persist conflicts in the same transaction as the rest of that capture's result.

## 9. Publication manifest

For each `approved_event_ids[]` value:
- Resolve exactly one `event_id`.
- Resolve its source.
- Confirm the event belongs to exactly one registered source.
- Insert the current `(source_id, event_id)` approval.

Reject duplicate, missing, or ambiguous references. Do not infer approval from event status, source flags, or prior publication output.

The manifest contains current approval state, not a full audit log. Migration must not invent historical approval/revocation timestamps or actors.

## 10. Required migration report

The import should emit a machine-readable report with:
- source registry input hashes and imported organization/source counts;
- identity-state input hash and counts for events, observations, unkeyed observations, revisions, lifecycle transitions, presence records, and processed tokens;
- number of conflicts imported from retained result reports and number unavailable;
- publication approvals imported and rejected;
- unresolved references, duplicate IDs, malformed rows, and unknown fields;
- per-entity source/target count and stable-ID reconciliation;
- explicit pass/fail for foreign-key, ownership, and fingerprint consistency checks.

The migration fails closed if any required record is malformed, ambiguous, duplicated, or references a missing owner. A report may be generated for diagnosis, but the database must not be cut over with unresolved integrity failures.

See [Relational Event-History Model](event-history-relational-model.md) for the complete relational expansion, sequence-number rules, same-event foreign-key constraints, and presence-mirror reconciliation.

## 11. No-loss rule

The original JSON files, archived capture payloads, metadata, and retained processing reports remain unchanged throughout import and parity testing. Unknown fields are preserved in JSON columns. No deduplication, cross-source merge, identity regeneration, inferred cancellation, or publication approval is performed as a migration cleanup step.
