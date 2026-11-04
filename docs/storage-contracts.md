# Storage Contracts (Design Only)

**Status:** proposed application contracts; no runtime implementation or database dependency is included.

## 1. Design goal

CivicCal should depend on domain-level storage operations, not SQL, table names, filesystem paths, or one database vendor. The current `IdentityStateStore` remains the JSON compatibility boundary during the transition. It is not sufficient as the final application-wide storage contract because it loads and replaces the entire identity-state document.

The future contract should support atomic ingestion and publication operations without requiring the caller to load and rewrite every event in the database.

## 2. Proposed application ports

The following are logical interfaces, not committed Python signatures. Exact method signatures and DTOs should be finalized alongside implementation.

### Organization and source catalog

Responsibilities:
- Retrieve an organization by stable `organization_id`.
- List organizations with simple status filters.
- Retrieve a source by stable `source_id`.
- List sources for one organization.
- Validate that each source belongs to exactly one organization.
- Update source configuration and permission/consent flags through an explicit administrative operation.

Rules:
- IDs remain stable and are not regenerated from names or URLs.
- Organization membership does not aggregate event feeds.
- A source remains an independent capture and subscription unit.
- Changing a source flag does not start capture, polling, or a background job.

### Capture archive catalog

Responsibilities:
- Register one capture and its verified metadata.
- Retrieve capture metadata by stable capture ID.
- Find a capture by source plus deterministic capture key.
- Resolve the archive reference for offline reprocessing.

Rules:
- The raw payload may remain file-backed in the first database implementation.
- Store its SHA-256, byte size, content type, source, timestamp, and archive reference.
- A database row must not imply that the raw payload still exists; archive verification must be explicit.
- Reprocessing a capture must not duplicate its capture record.

### Event identity and history

Responsibilities:
- Find an event by its source-scoped identity key.
- Insert a new source event with its stable CivicCal event ID.
- Append a source observation, including unchanged observations.
- Append a material revision only when the material fingerprint changes.
- Update the current event projection and last-seen metadata.
- Append explicit lifecycle transitions.
- Append presence observations only when completeness evidence authorizes them.
- Persist unkeyed observations and identity conflicts for review.
- Record and retrieve the processed-capture idempotency receipt.

Rules:
- Event identity is always source-scoped.
- Stable event IDs and identity keys are preserved during migration.
- No cross-source merge, title-based identity, or silent duplicate collapse.
- Repeated processing tokens return an already-processed outcome without new writes.
- An unchanged observation is still retained but does not create a revision.
- Absence from a partial/unknown snapshot does not create a missing transition.
- Even a complete snapshot may mark presence as missing; it never cancels or deletes an event.
- Explicit lifecycle status changes require source evidence.

### Publication approvals

Responsibilities:
- Check whether one event is currently approved for its exact source.
- Approve or revoke one source/event pair.
- List approved event IDs for one source.
- Append an immutable approval-action audit record.
- Validate event ownership before changing approval.

Rules:
- Approval and revocation are separate from ingestion.
- A source-specific feed can only query approved events whose `source_id` exactly matches the route.
- Revocation removes the event from the next feed response but does not delete event data or history.
- Approval changes and their audit records commit atomically.
- Existing manifest state can migrate to current approvals, but past actions are not fabricated.

### Read/query service

Responsibilities:
- Query events for one source with bounded filters such as date range, presence, and lifecycle status.
- Query publication-ready events for one source.
- Return source and event provenance needed by API and ICS serializers.

Rules:
- Read APIs are read-only.
- No implicit organization-wide or community-wide event aggregation.
- The serializer receives already source-scoped records; it must not infer ownership from event titles, organizers, or locations.
- Stable source-specific endpoints remain independent of storage backend.

## 3. Transaction boundary: one ingestion batch

The application should expose one atomic ingestion operation (or unit-of-work boundary) that persists the result of processing one verified capture.

Within one transaction:
1. Validate source and capture ownership.
2. Check the deterministic processed-capture token.
3. Register/link the capture metadata when available.
4. Insert keyed observations.
5. Insert new source events or update current projections.
6. Append material revisions when fingerprints change.
7. Persist unkeyed observations and identity conflicts.
8. Append lifecycle and presence history supported by evidence.
9. Store the processed-capture receipt and result summary.

If any write fails, none of the batch's writes commit. A retry with the same token must not double-count observations, revisions, or events.

The parser and normalizer remain outside the database adapter. They produce normalized input and provenance. The deterministic identity processor decides what changed. The storage adapter enforces persistence constraints and transactionality; it does not invent identity or lifecycle decisions.

## 4. Transaction boundary: one publication action

Approval/revocation is a separate transaction:
1. Resolve the source and event.
2. Verify that the event belongs to that exact source.
3. Change current approval state idempotently.
4. Append an audit action when state changes (or explicitly record attempted actions if that policy is later chosen).
5. Commit both changes together.

Publication must never be an implicit side effect of ingestion.

## 5. Compatibility transition

A safe staged transition is:

1. Keep `IdentityStateStore` and `JsonFileIdentityStateStore` unchanged as the working JSON backend.
2. Define typed domain records and the application-level ports before selecting concrete SQL.
3. Extract identity-processing decisions from whole-document state mutation so the processor can work with a repository/unit-of-work boundary.
4. Add database adapter behind the same application ports; do not make parsers or serializers issue SQL.
5. Keep JSON import/export as explicit migration and backup tools, not a second hidden source of truth.
6. Run JSON/database parity tests on the same fixture set and compare API JSON and source-specific ICS semantics.
7. Switch the configured backend only after explicit approval and a verified backup/rollback path.

Do not attempt to make a database adapter emulate whole-file replacement by loading the entire database into a dictionary. That would preserve the current bottleneck and weaken transaction boundaries.

## 6. Error contract

The application should distinguish:
- Not found: requested organization/source/event does not exist.
- Ownership mismatch: event exists but belongs to a different source.
- Validation failure: malformed domain input or invalid state transition.
- Conflict: duplicate stable ID, duplicate identity, or incompatible existing record.
- Already processed: idempotency token exists; no duplicate writes are made.
- Storage failure: transaction or persistence operation failed.

Errors should be stable domain-level outcomes. Database-specific exception text must not leak into API responses. The API layer maps these outcomes to appropriate HTTP responses.

## 7. Not in scope yet

- Concrete Python Protocol definitions or DTO implementations.
- SQL DDL, ORM, query builder, or migration framework.
- SQLite/PostgreSQL dependencies or connection management.
- Runtime backend selection.
- Database creation, import execution, or cutover.
- Background workers, polling, scheduling, or network capture.

Those are implementation decisions for a later approved step.
