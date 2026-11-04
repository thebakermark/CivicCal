# Storage Architecture

## Initial recommendation

Use SQLite for the first operational release, behind a small storage/repository interface. Keep the schema portable and avoid database-specific behavior where practical so PostgreSQL can be introduced later if concurrency or operational needs justify it.

No database server, deployment, or automatic polling is enabled by this document.

## Logical tables

### organizations
Publisher identity and public metadata.

### sources
Source registry, source type, URL/configuration, organization link, timezone policy, operational status, and polling settings.

### captures
Each capture attempt: source, timestamps, status, HTTP metadata, payload hash, parser status, warnings, and raw payload reference.

### raw_payloads
Content-addressed payload metadata and storage location. Small deployments may store payload bytes on disk; database rows should hold hashes and references rather than large blobs when appropriate.

### source_observations
Parsed source events tied to a capture, retaining original source fields and source event identity.

### events
Canonical event records with stable CivicCal IDs and current normalized values.

### event_sources
Links between canonical events and source observations, with relationship type and evidence.

### event_revisions
Append-only history of material canonical event changes.

### duplicate_candidates
Candidate groups, matching evidence, review state, and resolution history.

### publication_state
Publication visibility and stable feed/API projection metadata.

### webhook_subscriptions
Subscriber endpoint, event filters, signing secret reference, state, and timestamps. Secrets themselves should not be stored in plaintext.

### webhook_outbox and webhook_deliveries
Transactional notification records and delivery attempts.

### audit_log
Administrative and system decisions that affect sources, events, review, or publication.

## Data integrity

- Use foreign keys and uniqueness constraints for source-scoped identities.
- Use transactions for capture completion, observation persistence, event revisions, and outbox creation.
- Make capture processing idempotent.
- Keep revisions append-only; corrections create new revisions.
- Store timestamps in UTC for instants and preserve local wall-clock/timezone semantics for floating or date-only values.
- Preserve original source data and parser version.

## Raw payload storage

Use content hashes to avoid storing identical payloads repeatedly. Retain capture metadata even when the body is deduplicated. Define maximum size and retention before production.

## SQLite considerations

- Enable foreign keys.
- Use WAL mode where appropriate for concurrent readers.
- Keep write transactions short.
- Add indexes for date range, organization, source, status, and incremental update queries.
- Back up using SQLite's supported backup mechanism or a coordinated snapshot; do not blindly copy a live database file without accounting for WAL state.

## PostgreSQL migration path

Use migrations and repository interfaces. Avoid relying on SQLite-only SQL or implicit type coercions. Test the same repository behavior against both databases before declaring PostgreSQL support.

## Retention and backups

Define retention separately for:
- Raw payload bodies.
- Capture metadata.
- Source observations.
- Canonical event revisions.
- Webhook delivery logs.
- Audit history.

Backups should include the database and referenced raw payload archive, with periodic restore tests. A backup that has never been restored is not a verified recovery plan.
