# CivicCal Architecture

**Status:** authoritative architecture aligned to the accepted product requirements and decision register. Older hosting, aggregation, mailbox, and automation proposals are not implementation authority.

## 1. Product shape

CivicCal is one modular, portable application for the user's personal use. The user selects organizations and desired calendars; the operator workflow finds and verifies official sources, captures permitted source data, normalizes and stores it with provenance/history, and provides a private read-only API plus a separate iCalendar relay for each selected source.

Do not split the MVP into microservices. Keep module boundaries clear and storage/delivery replaceable.

## 2. Core pipeline

Organization registry
→ independent source registry
→ explicit operator-invoked one-shot capture
→ immutable raw capture archive + metadata
→ source-specific parser/adapter
→ normalized source observations
→ source-scoped identity/revision/presence/lifecycle processing
→ persistent database
→ explicit source-scoped publication approval
→ read-only JSON API + exact-source iCalendar relay

Capture, ingestion, and publication approval are separate operations.

## 3. Organization and source boundaries

- Organization records identify publishers and support discovery/administration.
- A source record represents one independently subscribable publication channel.
- An organization can have many sources.
- Each source has its own stable source ID, authorization/configuration, capture history, event ownership, approval scope, and stable feed endpoint.
- The district umbrella feed and each school-level feed are distinct sources.
- Do not create community-wide or organization-wide aggregate calendars.
- Do not merge cross-source records. Duplicate candidates remain review metadata.

## 4. Source authorization and capture

Authorization flags are manually edited by a human operator. Application code may read and enforce them, never change them. See Source Authorization Control Boundary and Decision Register.

Protected flags include access_status, terms_reviewed, robots_reviewed, consent_required, consent_granted, and polling_enabled.

- No application API, CLI, worker, migration, or ingestion code may grant/revoke authorization or modify these fields.
- Changing a flag itself initiates no task, network request, capture, polling, or publication.
- A permitted one-shot capture requires a separate explicit operator invocation and rechecks all required gates.
- Polling remains false by default and is not part of MVP.
- No scheduler, background worker, source reconciler, or task queue in MVP.
- No source activation, public deployment, or unattended access without separate approval.

## 5. Parsing, normalization, and event identity

Supported current foundations include ICS and source-specific HTML adapters. New formats are added only when needed and verified.

Preserve:
- Publisher/source IDs and exact source URL.
- Original source record and raw capture provenance.
- Title, description, location, dates/times, links, categories, registration/eligibility/fees where supplied.
- Date-only, floating, zoned, UTC, and unresolved temporal values without guessing.
- Every keyed source observation, including unchanged appearances.
- Material revisions and current event projection.
- Missing/presence evidence separately from explicit cancellation.
- Lifecycle transitions based on explicit source evidence.
- Unkeyed observations and identity conflicts as reviewable records.

Stable identity remains source-scoped. Similar titles, dates, or locations do not establish identity across sources. No LLM or semantic inference controls identity, authorization, or publication.

## 6. Storage

The current JSON/file backend is a development foundation. The MVP requires a persistent database behind backend-independent domain/storage contracts.

The logical model includes organizations, sources, captures, source events, observations, revisions, presence observations, lifecycle transitions, unkeyed observations, identity conflicts, publication approvals, and approval audit.

The exact database engine/implementation remains subject to user review in the target environment. Do not install, create, migrate, or cut over the database until explicitly approved. Preserve JSON parity, raw archives, exact identifiers, ordering, and authorization values; provide rollback.

## 7. Publication and API

Publication approval is separate from capture and ingestion. Only explicitly approved events for the exact source may be exposed.

- JSON API is read-only and versioned.
- iCalendar output uses RFC 5545.
- Each registered source has one stable feed URL.
- The feed contains only records owned by that exact source and explicitly approved for publication.
- No community, category, or organization aggregate feed in MVP.
- API and ICS must query the same database-backed approved record set.
- Current loopback server is a development harness, not public deployment.

## 8. Standards and MeaningWire

- RFC 5545: calendar subscription exchange.
- Schema.org Event: vocabulary mapping for aligned event concepts.
- OpenAPI: API description.
- CloudEvents: candidate envelope for future webhooks.
- JSON-LD: optional future structured representation.
- CivicCal domain model remains authoritative for source identity, provenance, temporal uncertainty, revisions, and approval.
- MeaningWire may later provide a semantic adapter. CivicCal must operate fully without MeaningWire. No RDF triple store, ontology engine, or MeaningWire runtime in MVP.

## 9. Deferred capabilities

Not part of MVP:
- Scheduled polling, source monitoring/reconciliation, task queues, and flag-triggered automation.
- Email/mailbox ingestion.
- Webhook delivery workers and subscriber management.
- Public website/UI, accounts, and administration portal.
- Cloudflare-specific or other hosting selection and public deployment.
- Community/organization/category aggregate feeds.
- Cross-source canonicalization/automatic merging.

These require separate product decisions and must not be inferred from old design documents.

## 10. Canonical project controls

- Product scope and acceptance: Product Requirements.
- Accepted product choices: Decision Register.
- Implementation status and evidence: Feature Register.
- Sequence and milestones: Roadmap.
- Current assessment: Project Assessment.
