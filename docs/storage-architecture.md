# Storage Architecture

## Current decision: database deferred

CivicCal is intentionally staying database-independent until the project is reviewed on the user's laptop. No SQLite or PostgreSQL schema, installation, migration, or deployment is part of the current milestone.

A replaceable storage boundary now exists for identity state in [docs/storage-interface.md](storage-interface.md). The current implementation is an atomic JSON-file adapter. This keeps the working pipeline usable now while leaving the eventual storage engine open.

## Future logical data model

The following logical entities describe information CivicCal will eventually need to persist. They are not a database schema and do not imply that tables currently exist.

- **organizations:** publisher identity and public metadata.
- **sources:** source registry, source type, URL/configuration, organization link, timezone policy, operational status, and polling settings.
- **captures:** each capture attempt, including timestamps, status, HTTP metadata, payload hash, parser status, warnings, and raw payload reference.
- **raw_payloads:** content-addressed payload metadata and storage location.
- **source_observations:** parsed source events tied to a capture, retaining original source fields and source event identity.
- **events:** CivicCal event records with stable source-scoped IDs and current normalized values.
- **event_sources:** links between event records and source observations, with relationship type and evidence.
- **event_revisions:** append-only history of material changes.
- **duplicate_candidates:** candidate groups, matching evidence, review state, and resolution history.
- **publication_state:** publication visibility and stable feed/API projection metadata.
- **webhook_subscriptions, webhook_outbox, webhook_deliveries:** subscriber configuration and delivery history.
- **audit_log:** administrative and system decisions affecting sources, events, review, or publication.

## Storage contract

Processing code should depend on small repository interfaces, not SQL dialects or database-specific query behavior. The current IdentityStateStore contract exposes load and save operations for the identity-state document. Future stores must preserve source-scoped identity, revision history, idempotency, unkeyed observations, and non-destructive missing-event behavior.

The JSON adapter is single-writer only. Concurrency coordination and transactional multi-record writes must be designed when a persistent database is selected.

## Future integrity requirements

When a database is chosen:
- Enforce source-scoped identity uniqueness.
- Use transactions for capture completion, observation persistence, event revisions, and publication outbox creation.
- Make capture processing idempotent.
- Keep revisions append-only; corrections create new revisions.
- Store timestamps in UTC for instants and preserve local wall-clock/timezone semantics for floating or date-only values.
- Preserve original source data and parser version.
- Define migration, backup, restore, and retention policies before production.

## Future backend options

SQLite remains a candidate for a small local deployment; PostgreSQL remains a possible later option if concurrency or operational needs justify it. The choice is open pending review on the target laptop/server. No database-specific behavior should leak into parsers, normalizers, identity rules, or API/feed projections.

## Raw payloads, backups, and retention

Raw capture files continue to live in the existing content-addressed file archive. A future persistence design must coordinate backups of metadata and referenced payloads. Define separate retention for raw payload bodies, capture metadata, source observations, event revisions, webhook delivery logs, and audit history. A backup is not verified until a restore has been tested.
