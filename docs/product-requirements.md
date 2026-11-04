# CivicCal Product Requirements

**Authority:** Product-level source of truth. If an older design conflicts with this document or the decision register, update the older document; do not silently revive superseded ideas.

## 1. User outcome

The user can identify organizations whose events they want, work with CivicCal to find and verify the organizations' official calendar sources, decide which sources to use, and subscribe to each selected source in their own calendar application. CivicCal is a personal-use tool operated by the user; it is not a public community calendar service.

CivicCal maintains the information relay. It does not replace the user's calendar app or edit the user's personal calendar.

## 2. Core product model

- An organization is an entity that publishes or is associated with public-interest information.
- A source is one independently identifiable event/calendar publication channel belonging to an organization.
- An organization can have multiple sources.
- Each registered source gets its own stable CivicCal subscription endpoint.
- A source endpoint contains only events belonging to that exact source.
- No combined community calendar or organization-wide aggregate calendar in the MVP.
- District umbrella calendars and individual school calendars are separate sources. Never assume umbrella coverage or merge overlapping feeds.
- The same real-world event published by two sources remains two source-owned records. Duplicate detection may create review candidates, never automatic merges or deletions.

## 3. MVP requirements

| ID | Requirement | Acceptance evidence |
|---|---|---|
| CC-001 | Discover and register organizations and official event sources | Registry stores organization and separately identified source records with evidence/status |
| CC-002 | Represent multiple independent sources per organization | Each source has its own stable ID, configuration, history, and endpoint |
| CC-003 | Manually controlled source authorization | Human manually edits authorization flags; application only reads/enforces; no Python or migration changes them |
| CC-004 | Perform permitted one-shot source capture | Explicit operator invocation; access/terms/robots/consent gates checked before network access |
| CC-005 | Preserve raw capture and provenance | Capture metadata, source URL, time, response facts, and raw payload/archive reference retained |
| CC-006 | Parse supported source formats | ICS and existing HTML adapters produce source observations |
| CC-007 | Normalize event details | Preserve title, dates/times, location, description, links, categories, registration/eligibility/fees where published, and original source fields |
| CC-008 | Preserve temporal meaning and uncertainty | Date-only, floating, zoned, UTC, unresolved values remain distinct; no invented timezone/end time |
| CC-009 | Track source-scoped identity and history | Stable event IDs, observations, material revisions, presence evidence, lifecycle transitions |
| CC-010 | Preserve ambiguous records safely | Unkeyed observations and identity conflicts remain reviewable; no automatic cross-source merge |
| CC-011 | Persist operational data in a database | Organizations, sources, captures, source events, observations, revisions, presence/lifecycle history, approvals and audit data persist |
| CC-012 | Provide a read-only JSON API | Clients query stored, approved data through documented, versioned endpoints |
| CC-013 | Provide one stable iCalendar feed per source | RFC 5545 feed includes only approved events for exact source; stable UIDs and correct updates |
| CC-014 | Support ordinary calendar subscriptions | Independent client subscribes and receives subsequent source-approved updates without duplicate churn |
| CC-015 | Keep publication approval separate from ingestion | Capture never publishes automatically; source-scoped event approval is explicit |
| CC-016 | Show source health and operational outcomes | Operator identifies capture/parse/validation failures and inspects provenance |
| CC-017 | Back up and restore database and raw archive | Documented, tested recovery from backup |
| CC-018 | Document future webhook interoperability | Stable event-change envelope and delivery contract specified; actual delivery is post-MVP |


## 4. Operational and safety invariants

1. Authorization fields are manually edited by a human operator. Python may read and enforce them, never change them.
2. Protected fields include access_status, terms_reviewed, robots_reviewed, consent_required, consent_granted, polling_enabled, and any future equivalent authorization field.
3. Changing a flag does not itself initiate a task, request, capture, polling, or publication.
4. Every network capture is a separate explicit operator action and must pass all required gates.
5. Polling is disabled by default and is not part of the MVP.
6. No deployment, remote access, installation, paid service, or spending without explicit approval.
7. No credentials, private-account access, bypassing access controls, or indiscriminate mailbox scanning.
8. Absence from a snapshot is not cancellation. Only explicit publisher evidence can establish cancellation.
9. Preserve source provenance, source IDs, source event IDs, temporal semantics, and history.
10. Duplicate candidates are review aids, not merge instructions.
11. No LLM or semantic inference may grant authorization, decide identity, or publish events.
12. CivicCal is a personal-use application. The user decides which organizations and event sources to include.

## 5. Standards and semantic interoperability

- iCalendar RFC 5545 is the subscription format.
- Schema.org Event is a vocabulary mapping where fields align.
- OpenAPI describes the API.
- CloudEvents is a candidate envelope for future webhooks.
- JSON-LD may be an optional future representation.
- CivicCal's domain model remains authoritative for source identity, provenance, observations, revisions, uncertainty, and approval.
- MeaningWire compatibility is a future adapter boundary, not an MVP runtime dependency.

## 6. Explicit exclusions from MVP

- Community-wide or organization-wide aggregated feeds.
- Automatic cross-source event merging or canonicalization.
- Unattended scheduled polling, source monitors, task queues, or flag-triggered actions.
- Webhook delivery workers and subscriber administration.
- Email/mailbox ingestion unless separately approved and specified.
- Public community discovery directory, public website, subscriber accounts, or public subscription portal.
- Cloudflare-specific hosting or any selected hosting provider until explicitly decided.
- RDF triple store, generalized ontology engine, or MeaningWire runtime.
- Automatic edits to users' personal calendars.

## 7. Release acceptance test

From a clean installation, an operator can register an organization and one or more independent sources, manually configure authorization, ingest a representative fixture (and later a permitted live capture), store records and complete history in the database, query the same records through the read-only API, and generate a valid stable source-specific ICS feed. A calendar client can subscribe and receive subsequent approved updates without duplicate churn. Backup and restore are demonstrated. No source authorization flag is changed by application code or migration.

## 8. Change control

A new feature or changed behavior must be added to the feature register and, when it changes an agreed product constraint, the decision register. Update acceptance criteria and affected docs/tests. An idea, proposal, or assistant suggestion is not an accepted decision until the user accepts it.
