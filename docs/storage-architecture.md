# Storage Architecture

## Current status

The current implementation uses JSON files behind a narrow replaceable storage interface. The MVP requires a persistent database, but database implementation and migration are deferred until the user is ready to review and run them in the target environment.

Database design can proceed remotely. The logical schema, field-by-field JSON migration map, relational event-history model, and backend-independent storage contracts are documented:

- [Database schema and migration design](database-schema-and-migration.md)
- [JSON migration map](json-migration-map.md)
- [Relational event-history model](event-history-relational-model.md)
- [Storage contracts](storage-contracts.md)
- [Storage interface](storage-interface.md)

No database engine is finally selected. SQLite is a candidate for a local first implementation; PostgreSQL may be considered later if justified. No installation, database creation, migration, or cutover is authorized yet.

## Logical entities

The future persistent model includes:
- organizations and independent sources;
- capture records and raw payload references;
- source events and complete normalized current projections;
- source observations and material revisions;
- presence observations and lifecycle transitions;
- unkeyed observations and identity conflicts;
- source-scoped publication approvals and approval audit;
- processed-capture idempotency receipts.

The relational event-history document defines authoritative relations, ordering, and no-double-counting rules.

## Storage contract

Processing code should depend on domain-level repository operations, not SQL dialects or ORM behavior. The current IdentityStateStore contract is only a narrow two-method identity-state boundary; it is not a complete application database interface.

Future storage must preserve source-scoped identity, revision history, idempotency, unkeyed observations, presence/lifecycle history, provenance, time semantics, and authorization values exactly.

## Authorization is not application-managed

Source authorization remains manually edited by a human operator. The application may read and enforce it but has no write operation for those flags. Database ingestion, ordinary updates, migration, repair, and cutover must preserve authorization values exactly.

## Integrity and recovery requirements

When implementation is approved:
- Enforce source-scoped identity uniqueness and foreign-key ownership.
- Use transactions for ingestion and publication approval.
- Make capture processing idempotent.
- Keep revisions append-only.
- Preserve source JSON and raw payload archive references.
- Define retention, backup, restore, and rollback.
- Demonstrate a clean restore before declaring production readiness.
