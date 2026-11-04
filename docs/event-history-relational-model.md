# Relational Event-History Model

**Status:** design reference only. No database implementation or migration is authorized by this document.

This document defines how the current JSON identity tracker expands into independently queryable relational history without changing event identity, revision semantics, presence semantics, or lifecycle semantics.

## 1. Design rules

1. One **source_events** row represents one publisher identity scoped to exactly one registered source.
2. Every keyed appearance in a successfully processed capture is an **event_observations** row, including unchanged appearances.
3. A material fingerprint change appends an **event_revisions** row. An unchanged observation does not.
4. The full normalized observation payload and the material revision projection are different records with different purposes; preserve both.
5. Presence observations, lifecycle transitions, and material revisions are separate histories. Do not infer one from another.
6. Each history table has one authoritative copy of each fact. Nested JSON history arrays are migration inputs/compatibility mirrors, not additional facts to duplicate.
7. Preserve original array order using explicit per-parent sequence numbers. Timestamps are data, not a reliable ordering key.
8. Keep source ownership explicit. No cross-source canonical event is introduced.

## 2. Proposed relational expansion

### source_events

One row per current source-scoped identity.

- Primary key: event_id (preserve existing evt_ value).
- Unique: identity_key (preserve existing hash).
- Required owner: source_id.
- Publisher identity: source_event_id, nullable only if historical data proves it; recurrence_instance_id.
- Current projection: current_event_json, current_fingerprint, current_revision_number.
- First/last observation: first_seen_at, last_seen_at.
- Current presence projection: presence_status, missing_snapshot_count, first_missing_at, last_missing_at.
- Current lifecycle projection: lifecycle_status.
- Optional legacy_state_json only if needed to retain unknown event-level fields during migration.

Validate that the events object key equals the nested identity_key, that the ID and identity key are unique, and that the event belongs to exactly one source. Do not regenerate either identifier.

current_event_json must preserve the exact current normalized event stored in JSON state. It is not safe to reconstruct it from the latest revision: current is replaced only when the material fingerprint changes, while non-material fields (including source_record) may differ in later observations without creating a revision.

### event_observations

One row for every keyed appearance.

- Primary key: observation_id (preserve existing deterministic ID).
- Foreign key: event_id.
- Also retain source_id, source_event_id, identity_key, capture_key, optional capture_id, observed_at, material_fingerprint, and full event_json.
- Unique observation_id.

The current tracker stores observation_ids[] on each event as a list of references to these global observation rows. In the relational model, the authoritative relationship is event_observations.event_id; do not also persist a second mutable observation-ID array on source_events. During migration, validate that every legacy observation_ids[] reference resolves to exactly one observation with the same event/source/identity. Preserve original array order as event_sequence on the observation row. Do not collapse repeated or unchanged observations.

### event_revisions

Append-only material history.

- Composite primary key: (event_id, revision_number).
- Foreign key: event_id.
- Foreign key: observation_id to event_observations.
- Fields: revision_number, fingerprint, observed_at, change_type, previous_fingerprint, values_json.

The current tracker stores revisions[] in event-local array order, with explicit revision numbers beginning at 1. Preserve those numbers exactly; validate contiguous ordering where current tracker guarantees it. The values object is the material projection selected by MATERIAL_FIELDS, not the full normalized event. Keep it distinct from event_observations.event_json and source_events.current_event_json.

A revision references the observation that triggered it. An unchanged observation has no revision row. Do not manufacture revision rows for unchanged observations.

### presence_observations

One authoritative append-only history of presence evidence.

- Primary key: stable presence_observation_id assigned during future DB ingestion; for migration, use a deterministic migration ID only when the source record lacks one and record the mapping.
- Foreign key: event_id; also retain source_id, capture_key, optional capture_id, observed_at, presence, missing_snapshot_count, completeness_evidence, reason, and original record_json.
- presence is present or missing; this table never means cancellation.

The current tracker writes a newly detected missing record to both global presence_observations[] and the event's nested missing_observation_history[]. These are two copies of the same fact. **Import the global presence_observations[] row once as authoritative; do not insert the nested missing-history mirror again.** Validate the mirror against the global row using event identity, capture key, observed time, presence, and missing count. If the mirror cannot be reconciled, preserve it in migration diagnostics/legacy JSON and fail or flag the affected record according to the migration's strictness policy; never silently discard it or double-count it.

On reappearance, the tracker appends a sparse {observed_at, capture_key, transition: reappeared} item to nested missing_observation_history[] and separately appends a global presence_observations[] row with presence: present and reason: event_seen_again. These are also one reappearance fact, not two presence events. Match them by event identity, capture key, timestamp, and transition/reason semantics; import the global row once. Preserve the sparse nested representation in migration diagnostics or a legacy-history JSON field if exact round-trip compatibility requires it.

The event-level presence_status, counters, and first/last missing timestamps are current projections, not extra observations. Preserve them on source_events; do not generate history rows from those summary fields.

### lifecycle_transitions

Append-only explicit publisher-status history.

- Primary key: (event_id, lifecycle_sequence).
- Foreign key: event_id.
- Nullable foreign key: observation_id (present for current created/status-change entries).
- Fields: observed_at, transition_type, from_status, to_status, evidence_json.

Expand lifecycle_history[] once, preserving its array order as lifecycle_sequence. The initial created transition has from_status = null; subsequent explicit changes reference the triggering observation. Do not synthesize lifecycle transitions from presence/missing history. The current lifecycle_status remains a projection on source_events.

### unkeyed_observations and identity_conflicts

Keep both review-oriented records independent of source_events.

- Unkeyed observations retain their existing observation_id, source, capture key, observed time, normalized event JSON, and review flags.
- Same-capture identity conflicts are persisted for future database-backed ingestion in the same transaction as the capture's other results. Historical conflicts may be imported only from retained result reports. Do not reconstruct them from identity state.

### processed_captures

Preserve current idempotency tokens exactly. Future receipts should also retain source, capture key, processing time, and result summary when those facts are available. Historical tokens alone do not justify inventing those fields.

## 3. Ordering and relationships

Use explicit integer sequence columns for histories:

| History | Sequence |
|---|---|
| Event observations | event_sequence per event, preserving observation_ids[] order |
| Event revisions | Existing revision_number |
| Presence observations | source_sequence preserving global presence_observations[] order; optionally event sequence as a query aid |
| Lifecycle transitions | lifecycle_sequence per event, preserving lifecycle_history[] order |

Do not order history solely by observed_at: multiple facts may share a timestamp, and source timestamps may be absent, floating, or not strictly monotonic.

Required links:
- event_observations.event_id → source_events.event_id.
- event_revisions.(event_id, observation_id) → the event observation that caused the revision; enforce same-event ownership.
- lifecycle_transitions.(event_id, observation_id) → the triggering observation where present; enforce same-event ownership.
- presence_observations.event_id → source_events.event_id.
- Each event/source relationship must agree with the source owner on source_events.

For presence rows without a direct source observation ID, capture_key and capture metadata provide provenance. Do not invent an observation ID for a missing fact.

## 4. Migration reconciliation procedure

For each event, migration must:

1. Insert exactly one source_events row using the existing event ID and identity key.
2. Import global keyed observations and assign event_sequence in the order their IDs appear in the event's observation_ids[] array. Reject missing, duplicate, or cross-event references. Also report global observations not referenced by an event.
3. Expand revisions in their stored array order, preserve explicit revision numbers and fingerprints, and resolve each observation_id to the same event.
4. Import global presence observations once, preserving global array order. Reconcile nested missing/reappearance mirrors without creating duplicate rows.
5. Expand lifecycle history in array order and resolve optional observation links.
6. Reconcile current projections against the latest applicable state without rewriting source JSON or treating a summary field as an additional historical fact.

The migration report must include:
- counts and stable IDs for source events, keyed observations, revisions, unkeyed observations, presence observations, and lifecycle transitions;
- event-to-observation link mismatches and unreferenced observations;
- duplicate/missing observation references;
- revision-to-observation and lifecycle-to-observation ownership mismatches;
- nested/global presence mirror matches, unmatched mirrors, and duplicate candidates;
- per-event sequence preservation and fingerprint consistency;
- all unknown fields preserved in JSON or explicitly reported.

Any ambiguous or conflicting reference blocks cutover. Keep original JSON files unchanged.

## 5. Future ingestion transaction

A database-backed ingestion transaction should write the capture/processing receipt, keyed observations, source-event projection changes, new revisions, unkeyed observations, identity conflicts, presence observations, and lifecycle transitions atomically. The deterministic tracker decides which facts exist; the storage adapter persists them. A failure rolls back the entire capture transaction.

This document does not authorize database installation, schema creation, migration, dependency changes, live capture, polling, or deployment.
