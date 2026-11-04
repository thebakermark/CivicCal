# CivicCal Decision Register

Durable record of accepted product decisions. New decisions are appended with an ID and date; superseded decisions remain visible with a replacement reference.

**Last reconciled:** 2026-11-04

| ID | Date | Decision | Status |
|---|---|---|---|
| DEC-001 | 2026-11-04 | One registered source maps to one stable CivicCal endpoint. Organization is descriptive/administrative, not a feed aggregation unit. | Accepted |
| DEC-002 | 2026-11-04 | No community-wide or organization-wide combined calendar in MVP. | Accepted |
| DEC-003 | 2026-11-04 | District umbrella calendar and each individual school calendar are separate sources; do not infer umbrella coverage or merge overlaps. | Accepted |
| DEC-004 | 2026-11-04 | Cross-source duplicates remain separate source-owned events; candidate detection only, no automatic merge/delete. | Accepted |
| DEC-005 | 2026-11-04 | Source authorization flags are manually edited by a human. Python/application/migrations may read and enforce but must never change them. | Accepted |
| DEC-006 | 2026-11-04 | Changing a source flag does not itself initiate a task, network request, capture, polling, or publication. A permitted capture is separately invoked by an operator. | Accepted |
| DEC-007 | 2026-11-04 | Polling and background automation are out of MVP; polling defaults false. | Accepted |
| DEC-008 | 2026-11-04 | Capture, ingestion, and publication approval are separate operations. Capturing does not automatically publish. | Accepted |
| DEC-009 | 2026-11-04 | Database is required for MVP, but implementation and migration are deferred until user is ready to review/run in target environment. Design can proceed remotely. | Accepted |
| DEC-010 | 2026-11-04 | Use a replaceable, backend-independent storage boundary; do not couple parser/identity logic to SQL/ORM. | Accepted |
| DEC-011 | 2026-11-04 | Standards-first and MeaningWire-compatible; no MeaningWire runtime, RDF store, or generalized ontology engine in MVP. | Accepted |
| DEC-012 | 2026-11-04 | RFC 5545 feeds are the subscription mechanism; Schema.org is a mapping vocabulary; OpenAPI documents API; CloudEvents is a candidate future webhook envelope; JSON-LD optional later. | Accepted direction |
| DEC-013 | 2026-11-04 | Webhook contract may be documented now, but webhook delivery is post-MVP. | Accepted |
| DEC-014 | 2026-11-04 | No deployment, public remote access, installs, spending, or paid services without explicit approval. | Accepted |
| DEC-015 | 2026-11-04 | Preserve source provenance, raw evidence, observation/revision history, temporal semantics, uncertainty, and explicit status evidence. | Accepted |
| DEC-016 | 2026-11-04 | Missing from a later snapshot is not cancellation; only explicit publisher evidence can establish cancellation. | Accepted |
| DEC-017 | 2026-11-04 | CivicCal is community information infrastructure, not a household-only calendar. | Superseded by DEC-019 |
| DEC-018 | 2026-11-04 | Email/mailbox ingestion is not an MVP dependency; it requires separate explicit scope and authorization. | Deferred |
| DEC-019 | 2026-11-04 | CivicCal is for the user's personal use. The user chooses which organizations and event calendars to include; source discovery is a collaborative operator workflow, not a public resident-facing directory or community service. | Accepted |

## Superseded or conflicting legacy design

The earlier architecture proposed Cloudflare Workers/D1/R2, scheduled GitHub Actions ingestion, mailbox integrations, organization/category/community feeds, and cross-source canonical event merging. These proposals are superseded by DEC-001 through DEC-018 and are not implementation authority.

## Decision process

- **Accepted:** user explicitly chose or confirmed the behavior.
- **Proposed:** suggested but not accepted; not implementation authority.
- **Deferred:** potentially useful later, explicitly not MVP.
- **Rejected:** explicitly excluded.
- **Superseded:** replaced by a later accepted decision.

Assistant recommendations do not become accepted decisions by being written into a draft. Material scope changes require user acceptance.
