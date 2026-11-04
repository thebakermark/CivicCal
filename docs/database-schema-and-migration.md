# Database Schema and JSON Migration Design

**Status:** design only; no database implementation is authorized by this document.

## 1. Purpose and constraints

CivicCal's MVP needs durable storage for organizations, independent event sources, source captures, source observations, source-scoped events, revision history, and publication decisions. The current JSON identity-state file is a useful development backend, but it combines several records with different lifecycles.

The database must preserve existing behavior:

- One registered source has one independent subscription endpoint.
- A source belongs to an organization; an organization may have many independent sources.
- Event identity is scoped to its source. No cross-source merge or community-wide event identity is introduced.
- Publisher event IDs are not assumed globally unique.
- Every source observation is retained separately from material event revisions.
- Original publisher/parser values and capture provenance remain inspectable.
- Floating date-times, explicit timezones, UTC offsets, date-only values, and unresolved temporal values remain distinguishable. Never infer a timezone from a nearby VTIMEZONE declaration alone.
- Missing from a partial or incomplete capture does not imply cancellation. A complete snapshot may record a presence/missing observation, but must not delete or cancel the event.
- Reprocessing the same source capture is idempotent.
- Unkeyed observations and identity conflicts are retained for review.
- Publication is explicit, source-scoped, and separate from ingestion.
- No LLM participates in identity, lifecycle, approval, or other deterministic rules.

The logical model below is database-engine-neutral. SQLite is the likely first embedded/local implementation, with a later PostgreSQL adapter possible. This is not yet a final engine decision.

See [Relational Event-History Model](event-history-relational-model.md) for the complete sequence, relationship, and no-double-counting rules.

The source authorization model is human-controlled: authorization flags are manually edited by an operator. Application code may read and enforce them but must not write them. See [Source Authorization Control Boundary](source-authorization-boundary.md). The relational event-history expansion and exact migration reconciliation rules are defined in [Relational Event-History Model](event-history-relational-model.md).

## 2. Proposed logical entities

### Organization

One real-world publisher or community organization.

Fields:
- `organization_id` — stable registry ID; primary key.
- `name`, `organization_type`, `website`.
- `verification_status`, `notes`.
- `created_at`, `updated_at`.

Organization metadata does not define a calendar aggregation boundary.

### Source

One independently captured and subscribed publisher channel.

Fields:
- `source_id` — stable registry ID; primary key.
- `organization_id` — owning organization; foreign key.
- `name`, `source_type`, `source_url`, `scope`.
- `access_status`, `terms_reviewed`, `robots_reviewed`.
- `consent_required`, `consent_granted`, `polling_enabled`.
- `timezone_policy`, `completeness_profile`, `configuration_json`.
- `created_at`, `updated_at`.

A source's consent and access controls remain explicit and human-edited. The application has read-and-enforce access only; it must not grant consent, approve access, mark reviews complete, or enable polling. Migration must preserve each flag exactly and never change it. Changing a flag does not itself fetch or schedule anything. Source registry IDs remain stable across migration.

### Capture

One archived attempt to retrieve a source payload.

Fields:
- `capture_id` — stable capture identifier; primary key.
- `source_id` — foreign key.
- `captured_at`, `requested_url`, `final_url`, `http_status`.
- `content_type`, `etag`, `last_modified`.
- `payload_sha256`, `payload_size_bytes`, `archive_uri`.
- `outcome`, `completeness`, `completeness_evidence`.
- `metadata_json` — complete capture metadata for forward compatibility.

Raw payload bytes should initially remain in the existing archive/file layout; the database stores a verified digest and archive reference. This avoids forcing large raw payloads into the first database migration. A later storage adapter may move payloads to a blob store without changing event identity.

### Processed capture

A unique processing receipt prevents duplicate ingestion.

Fields:
- `source_id`, `capture_key`, `processing_token`.
- `capture_id` where a capture record exists.
- `processed_at`, `result_json`.

Unique constraint: `(source_id, processing_token)`.

The processing token must preserve the current deterministic behavior: it is derived from source ID and capture key. A repeated token returns the prior result or an explicit already-processed result and creates no duplicate observations or revisions.

### Source event / current event

One publisher event identity owned by exactly one source. This is CivicCal's current event record, not a cross-source canonical event.

Fields:
- `event_id` — stable existing CivicCal ID (for example, `evt_<24 hex chars>`); primary key.
- `identity_key` — stable source-scoped identity hash; unique.
- `source_id` — foreign key.
- `source_event_id` — publisher-provided identifier.
- `recurrence_instance_id` — optional recurrence instance discriminator.
- `current_fingerprint`, `current_revision_number`.
- `first_seen_at`, `last_seen_at`.
- `presence_status`, `missing_snapshot_count`, `first_missing_at`, `last_missing_at`.
- `lifecycle_status`.
- `current_event_json` — full normalized event, including fields not yet promoted to columns.

Uniqueness: `identity_key`; also enforce the source-scoped identity tuple `(source_id, source_event_id, recurrence_instance_id)` where the chosen database supports the required null semantics. The application must validate this invariant consistently across engines.

Keep `event_id` and `identity_key` exactly as generated by the current tracker during migration. Do not regenerate IDs from titles, dates, or URLs.

### Event observation

Every keyed appearance of an event in a capture, including unchanged appearances.

Fields:
- `observation_id` — stable observation ID; primary key.
- `event_id`, `source_id`, `capture_id` / `capture_key`.
- `source_event_id`, `observed_at`, `material_fingerprint`.
- `event_sequence` — explicit per-event sequence preserving the legacy `observation_ids[]` array order.
- `event_json` — full normalized source observation.

Unique constraint: `observation_id`; also enforce uniqueness of `(event_id, event_sequence)`. The observation row's `event_id` foreign key is the authoritative membership relationship; do not retain a second mutable observation-ID array on `source_events`. Validate every legacy array reference during migration. Retain observation-to-revision linkage; an unchanged observation does not need to create a new revision.

### Event revision

Append-only material history for a source event.

Fields:
- `event_id`, `revision_number`.
- `fingerprint`, `observed_at`, `observation_id`.
- `change_type` (created/updated).
- `previous_fingerprint`.
- `values_json` — material projection used by the current tracker.

Primary key: `(event_id, revision_number)`. Each revision must reference the observation that triggered it, with a same-event ownership constraint (composite relationship `(event_id, observation_id)` to the observation table). Revisions are never updated or deleted by normal ingestion. Current event state is a convenient projection of the latest revision, not a replacement for history. Preserve revision array order/number; do not use timestamps as the sequence.

### Presence observation

Records presence or absence evidence from a capture.

Fields:
- `presence_observation_id` — stable ID.
- `source_id`, `event_id`, `capture_id` / `capture_key`.
- `observed_at`, `presence` (present/missing).
- `presence_sequence` — explicit sequence preserving the global `presence_observations[]` array order.
- `missing_snapshot_count`, `completeness_evidence`, `reason`, `record_json`.

The global `presence_observations[]` array is authoritative. Event-level `missing_observation_history[]` is a nested mirror and must be reconciled, not imported a second time. Reappearance mirrors may have different shapes; preserve unmatched nested data in migration diagnostics/legacy JSON and never double-count. A missing observation is not a cancellation. Explicit source status changes are stored separately as lifecycle transitions and must be based on source evidence.

### Unkeyed observation and identity conflict

Keep events without stable publisher IDs and same-capture identity collisions as first-class review records. Preserve their original normalized event JSON, source ID, capture key, observation time, and review reason. Do not silently discard, merge, or invent an identity for them. **Current-state limitation:** the JSON tracker persists unkeyed observations in `unkeyed_observations`, but same-capture identity conflicts are currently returned in the processing result and are not appended to the identity-state file. The database must persist conflicts for future ingestions. A migration can import historical conflicts only from separately retained processing reports; it must not claim that conflicts can be reconstructed from the identity-state JSON.

### Lifecycle transition

Append-only explicit status history.

Fields:
- `event_id`, `lifecycle_sequence` — explicit per-event sequence preserving `lifecycle_history[]` order.
- `observed_at`, nullable `observation_id` where the source transition has no direct observation link.
- `transition_type`, `from_status`, `to_status`, `evidence_json`.

Primary key: `(event_id, lifecycle_sequence)`. Where `observation_id` is present, enforce that it belongs to the same event. This preserves the current `lifecycle_history` semantics and keeps explicit publisher cancellation distinct from snapshot absence. Timestamps are not a reliable ordering key.

### Publication approval and audit

Replace the global JSON approval list with source-scoped relational records.

Current approval:
- `source_id`, `event_id`, `approved_at`, `approved_by` (nullable operator identifier), `approval_note`.

Primary key: `(source_id, event_id)`; foreign keys must ensure the event belongs to that exact source. Revocation removes the current approval but does not erase history.

Approval audit:
- `approval_action_id`, `source_id`, `event_id`.
- `action` (approve/revoke), `acted_at`, `actor`, `note`.

Every approval or revocation appends an audit row in the same transaction as the current approval change. Existing JSON manifest approvals migrate to current approvals; historical approve/revoke actions cannot be reconstructed if they were never recorded, so migration must not fabricate audit history.

The source-specific API and ICS feed query only currently approved events for that exact source.

## 3. Temporal and JSON preservation

The database must not flatten event times into naive timestamps.

Store the normalized temporal object without loss, including:
- raw/canonical value;
- kind: date, date-time, or unparsed;
- time status: date_only, floating, zoned, utc, or unresolved;
- timezone identifier when explicitly supplied;
- UTC offset when explicitly supplied.

For query performance, implementations may add derived date/time columns, but those columns must be reproducible from the preserved value and must never overwrite it. A floating local date-time must remain floating. A date-only event must remain date-only.

Keep complete normalized event JSON and source-record JSON available. Relational columns are query/index aids, not permission to discard publisher fields or provenance.

## 4. Relationships and indexes

Core relationships:

- Organization 1 → many Sources.
- Source 1 → many Captures.
- Source 1 → many Source Events.
- Source Event 1 → many Observations.
- Source Event 1 → many Revisions.
- Source Event 1 → many Presence Observations and Lifecycle Transitions.
- Source Event 1 → zero or one current Publication Approval.
- Capture 1 → many Observations and processing receipts.

Initial indexes:
- `sources(organization_id)`
- `captures(source_id, captured_at)`
- `source_events(source_id, source_event_id)`
- `source_events(source_id, presence_status)`
- `event_observations(event_id, event_sequence)`
- `event_observations(event_id, observed_at)`
- `event_observations(source_id, capture_key)`
- `event_revisions(event_id, revision_number)`
- `presence_observations(source_id, presence_sequence)`
- `presence_observations(source_id, observed_at)`
- `publication_approvals(source_id, event_id)`
- query indexes for event start date and source ID after actual query patterns are measured.

Avoid speculative full-text or geospatial infrastructure in the first database release.

## 5. Transaction boundaries

One ingestion transaction should commit together:
1. capture/processing receipt (or link to an existing archived capture);
2. keyed observations;
3. new source-event rows or updates to current projections;
4. append-only revisions;
5. unkeyed observations and identity conflicts;
6. presence observations and lifecycle transitions;
7. processed-capture idempotency receipt.

If any step fails, roll back the whole ingestion transaction. Do not leave an event current projection updated without its revision or observation.

Publication approval/revocation is a separate short transaction that validates the source-event relationship, changes current approval, and appends its audit row atomically. Capture, ingestion, and publication remain separate operations.

Use foreign keys and uniqueness constraints. Define a single-writer policy for the first SQLite release; if concurrent writers become necessary, add explicit locking/retry behavior rather than relying on accidental behavior.

## 6. JSON-to-database migration

Migration must be deterministic, repeatable, and non-destructive.

### Inputs

- `data/sources.json` — organizations and source registry.
- Current identity-state JSON — `events`, `observations`, `unkeyed_observations`, `processed_captures`, and `presence_observations`.
- Publication manifest JSON — `approved_event_ids`.
- Existing archived capture files and metadata remain in place; import references only when their exact metadata is available.

### Ordered migration

1. **Freeze and inventory.** Stop ingestion and approval writers. Copy the source registry, identity state, publication manifest, and capture metadata into a timestamped backup directory. Record SHA-256 hashes and byte sizes. Never overwrite the originals.
2. **Validate before import.** Check schema versions, unique organization/source/event/observation IDs, valid source references, event ownership, unique revision numbers, valid approval references, and processed-capture token uniqueness. Fail closed on ambiguity; produce a report rather than guessing.
3. **Initialize an empty database.** Apply versioned schema migrations in order and enable foreign-key enforcement.
4. **Import organizations and sources.** Preserve every stable ID and configuration field. Validate each source references exactly one organization where applicable.
5. **Import captures and receipts.** Import capture metadata when available. Preserve each existing processed-capture token exactly; do not invent capture rows for tokens with no recoverable metadata. The current state stores tokens but not their result payloads, so a migration must not invent historical processing results.
6. **Import source events and history.** Preserve event IDs, identity keys, current JSON, fingerprints, timestamps, revisions, observation IDs, unkeyed records, presence history, and lifecycle history. Preserve array order where it represents history. Import identity conflicts only from retained processing reports; the identity-state file alone does not contain them.
7. **Import publication state.** Resolve every approved event to exactly one event and its exact source. Import current approvals only. Do not fabricate past approval audit actions.
8. **Reconcile counts and hashes.** Compare source counts, IDs, fingerprints, revisions, observations, unkeyed records, processed tokens, presence records, and approved source/event pairs. Produce a machine-readable migration report.
9. **Parity test while read-only.** Run the same API query and source-specific ICS generation against the JSON snapshot and database adapter. Compare normalized JSON objects and ICS semantic content; account for intentional serialization ordering only, not event differences.
10. **Cut over explicitly.** Keep the original JSON files and backup immutable. Change the configured backend only after parity passes and a human approves cutover.
11. **Rollback.** If parity or runtime checks fail, switch configuration back to the untouched JSON snapshot. Do not attempt a destructive reverse migration.

### Idempotency and safety

- Import must be safe to rerun against an empty/recreated target database.
- Never append duplicate rows on a retry. Use stable primary keys and explicit conflict checks; do not use blind upserts that overwrite conflicting data.
- A target database containing partial or conflicting data must fail validation or require an explicit clean rebuild. Do not silently reconcile by deletion.
- Preserve the old JSON data until backups, parity, and restore are verified.

See [Relational Event-History Model](event-history-relational-model.md) for the authoritative expansion of nested histories, sequence preservation, and duplicate-mirror handling. See [Current JSON State to Database Migration Map](json-migration-map.md) for the field-by-field mapping from the actual registry, identity-state JSON, archived capture metadata, and publication manifest into the proposed entities, including current-state gaps.

## 7. Acceptance tests before cutover

The database backend is not ready until tests demonstrate:

1. A clean database initializes with foreign keys enabled.
2. Organization/source relationships and exact source ownership are enforced.
3. Existing event IDs and identity keys survive import unchanged.
4. Same capture processed twice creates no additional observations, revisions, or events.
5. Changed material fields append exactly one revision; unchanged fields do not.
6. Unkeyed observations and identity conflicts survive round-trip.
7. Complete-snapshot absence creates presence history only; it never deletes or cancels an event.
8. Explicit cancellation creates a lifecycle transition based on source evidence.
9. Floating, zoned, UTC, and date-only times round-trip without semantic change.
10. Approval and revocation are source-scoped, audited, and atomic.
11. API output matches the JSON backend for the same approved data.
12. Source-specific ICS output matches the JSON backend and never includes another source's events.
13. Backup restore reproduces the same query and feed outputs.

## 8. Decisions intentionally deferred

- Final database engine and version.
- Whether raw capture payload bytes remain filesystem-backed or move to a database/blob adapter.
- Concrete SQL DDL and migration tooling.
- Connection pooling and multi-writer concurrency strategy.
- Retention/archival periods.
- Production backup schedule and hosting topology.

These choices should be made when implementation is reviewed on the target laptop/server environment. This document does not authorize installing dependencies, creating a database, migrating user data, deploying services, or enabling scheduled capture.
