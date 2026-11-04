# Semantic Interoperability and Open Standards

**Status:** architecture decision. This document defines standards boundaries for the MVP. It does not add a runtime dependency, change the event model, or authorize a database migration.

## Decision

Build CivicCal **standards-first and MeaningWire-compatible**, not MeaningWire-dependent.

CivicCal remains responsible for its operational domain: registered organizations and independent sources, source captures, source-scoped event identity, observations, material revisions, presence evidence, lifecycle transitions, provenance, review, and publication approval.

Open standards are used at the boundaries where they already solve an interoperability problem. MeaningWire may later provide a reusable semantic description and relationship layer across CivicCal and other systems. It must not replace CivicCal's operational model or deterministic rules.

## 1. Standards by boundary

| Boundary | Standard | CivicCal decision |
|---|---|---|
| Calendar subscriptions | iCalendar, RFC 5545 and applicable updates | Primary interoperable event-delivery format. Preserve correct date-only, floating, UTC, timezone, recurrence, and cancellation semantics. |
| Event vocabulary | Schema.org Event | Use as a mapping vocabulary for fields that fit. It is not the CivicCal database schema. |
| Linked-data serialization | JSON-LD 1.1 | Optional future representation of API resources. Do not require JSON-LD to store, process, or publish the MVP. |
| HTTP API contract | OpenAPI | Continue documenting the existing read-only API. The current implementation declares OpenAPI 3.1.1; keep that pinned until tooling/client compatibility is tested before any version change. |
| Webhook envelope | CloudEvents (candidate) | Evaluate when webhook delivery is implemented; not part of the current MVP dependency surface. |

Standards references:
- iCalendar RFC 5545: https://www.rfc-editor.org/rfc/rfc5545
- Schema.org Event: https://schema.org/Event
- JSON-LD 1.1: https://www.w3.org/TR/json-ld/
- OpenAPI Specification: https://spec.openapis.org/oas/
- CloudEvents specifications: https://cloudevents.io/

The standards solve different problems and are complementary. None defines CivicCal's complete source-provenance and review model.

## 2. CivicCal remains the system of record

The internal domain model must preserve information that generic event vocabularies do not fully represent:

- Organization and independent source ownership.
- Publisher source-event ID and source-scoped CivicCal event ID.
- Exact source URL and capture provenance.
- Raw/canonical source values and parser/normalizer uncertainty.
- Every keyed observation, including unchanged appearances.
- Material revision history and the observation that caused each revision.
- Presence observations distinct from explicit lifecycle status changes.
- Unkeyed observations and identity conflicts for review.
- Source-specific publication approval and its audit history.
- Time semantics: date-only, floating, zoned, UTC, and unresolved.

Do not flatten these concepts into Schema.org Event properties or a JSON-LD graph and then attempt to reconstruct the operational state from that projection.

Schema.org Event is a useful outward vocabulary for event facts such as name, start/end, location, organizer, event status, and audience. It does not replace CivicCal's source identity, observation, revision, evidence, or approval records.

## 3. Mapping policy

Create explicit, tested mappings between CivicCal fields and external vocabularies.

- Map only fields with a defensible semantic equivalent.
- Preserve original CivicCal values when a target vocabulary is broader, narrower, or ambiguous.
- Do not infer missing values to satisfy a target schema.
- Do not treat a publisher's statement as independently verified fact.
- Preserve source attribution and links in every outward representation where supported.
- Keep extension fields namespaced and documented if/when CivicCal must expose concepts that the standard vocabulary does not express.
- Never use a serialization format as the source of truth for identity or approval.

The first useful mapping is an event projection to Schema.org Event. It should be implemented as a pure adapter over CivicCal domain records, with mapping tests. JSON-LD can serialize that projection later; no JSON-LD runtime is needed merely to create the mapping.

## 4. Stable identifiers and relationships

CivicCal's current event IDs and identity keys remain stable internal identifiers. Source identity is scoped to the registered source. The same publisher ID used by two different sources must not collapse into one event.

Before publishing permanent public entity URIs, choose and document a stable CivicCal base domain and URI policy. Until that decision is made:
- Do not mint guessed public URLs or URNs.
- Do not expose internal database primary keys as if they were permanent semantic identifiers.
- Keep API resource identifiers stable within the existing API contract.
- Keep source URLs and publisher-provided IDs as provenance, not as a substitute for CivicCal identity.

A future MeaningWire adapter may describe relationships among organizations, sources, events, observations, revisions, and captures. It must reference CivicCal's stable identifiers and preserve source ownership; it must not perform automatic cross-source identity merging.

## 5. MeaningWire integration boundary

MeaningWire is a future semantic layer, not an MVP dependency.

The intended integration is an adapter in each direction:

1. CivicCal domain records → MeaningWire semantic representation.
2. MeaningWire-linked external entities → explicit, reviewable references in CivicCal where a real product need exists.

The adapter must be replaceable and must not leak MeaningWire-specific types into the event tracker, source capture, parser, storage contract, approval logic, or iCalendar publisher.

MeaningWire must not:
- Decide whether a source is permitted to be captured.
- Infer consent, access permission, or publication approval.
- Decide event identity or merge source records.
- Infer cancellation from absence.
- Rewrite source evidence or timestamps.
- Participate in deterministic gates through an LLM.
- Become a required service for CivicCal to ingest, query, or publish events.

CivicCal is a useful bounded proving ground for MeaningWire because it contains real identity, provenance, temporal, and relationship problems. That is a reason to keep the boundary clean, not a reason to implement a general ontology engine now.

## 6. MVP implementation sequence

1. Keep the current CivicCal normalized event model and storage contracts.
2. Continue producing iCalendar feeds as the primary subscription interface.
3. Keep the existing OpenAPI 3.1.1 contract versioned and tested.
4. Add a field mapping specification from CivicCal event records to Schema.org Event.
5. Add pure mapping tests for supported fields, omitted/unknown values, status, all-day values, and time semantics.
6. Add JSON-LD serialization only when an actual consumer or integration needs it.
7. Revisit MeaningWire integration after the database-backed domain model and public identifiers are stable.

## 7. Explicitly deferred

- RDF triple store or graph database.
- General-purpose ontology engine or universal semantic registry.
- JSON-LD as canonical storage.
- Automatic entity resolution or cross-source event merging.
- Public URI namespace commitment before the base domain policy is decided.
- MeaningWire runtime dependency or shared service.
- CloudEvents implementation before webhooks are in scope.
- API specification upgrade without compatibility review.

This decision adds no software dependency and does not authorize installations, deployments, source activation, scheduled capture, database creation, or migration.
