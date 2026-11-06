# CivicCal Project Assessment — 2026-11-06

## Executive assessment

CivicCal has a substantial ingestion foundation and a clear product direction. It is not yet the intended MVP. The largest missing pieces are database-backed persistence, lossless migration, API/ICS delivery from the database, a real externally reachable source-specific subscription endpoint, and demonstrated backup/restore.

The largest documentation risk was architecture drift: the old architecture described cloud hosting, combined feeds, mailbox integrations, scheduled polling, and cross-source canonicalization that no longer match accepted decisions. The architecture has been reconciled and decisions centralized.

## Intended product

The user selects organizations and desired event calendars; CivicCal helps identify and verify their official sources, captures and preserves permitted event information, stores it with provenance/history in a database, and provides a stable iCalendar subscription URL for each selected source plus a private read-only API.

## Registry coverage snapshot

The checked-in source registry currently contains **24 organization records and 12 independent source records**.

Organization verification status:
- 5 official sites identified.
- 1 feed verification required.
- 18 organization identities/channels still require verification.

Registered sources:
- Village of Mokena events.
- Mokena Community Public Library events and library board meetings.
- Mokena Community Park District events and board meetings.
- Mokena SD 159 events feed.
- Summit Hill SD 161 district events, Indian Trail, Dr. Julian Rogus, Hilda Walker, Summit Hill Jr. High, and Mary Drew calendars.

Current source authorization state: all 12 source records have access_status=approved. All 12 have terms_reviewed=true and robots_reviewed=true. SD159 is the only source with polling_enabled=true; its consent_required and consent_granted fields are both true. These are registry values only: they do not start a scheduler or authorize unattended polling. Source-level event_access remains mixed or unknown for some records, so approved registry status is not proof that every event is public or publishable.

## Current audit findings — 2026-11-06

The current completeness-policy file on main contains 10 profiles and is missing profiles for both Mokena Library events and SD159. The accompanying audit branch adds an SD159 profile scoped only to the official district Events iCalendar export, using single_feed, requiring the feed role, and retaining allow_complete_snapshot=false. This enables policy validation without asserting feed completeness. The Mokena Library profile remains outstanding. SD159's archived feed still requires comparison with the district's visible calendar; the separately reviewed 2026–27 PDF does not establish ICS scope or completeness.

The ICS coordinator records the HTTP Content-Type and validates UTF-8 plus a VCALENDAR envelope. It does not reject a structurally valid feed solely because the server labels it application/octet-stream. Regression tests have been added for text/calendar and application/octet-stream. Authorization immutability and archived ICS-to-identity ingestion/idempotency tests have also been added. These tests are not marked verified until a clean CI run passes. The current pull-request workflow stops at source-registry validation before reaching the test step: the existing SD159 registry record has polling_enabled=true but lacks poll_interval_minutes and last_verified_at, which the validator requires when polling is enabled. This is a pre-existing main-branch inconsistency; the protected source record was not changed, and the test step was skipped.

## Assessment

| Capability | Assessment | Reason |
|---|---|---|
| Organization discovery | Partial | Registry has candidates; candidate listing is not verification |
| Independent source registration | Foundation present | Separate source IDs exist; scope/coverage still need per-source validation |
| Human-controlled authorization | Foundation present | Capture checks gates; no-write invariant needs code/test audit |
| One-shot capture | Implemented foundation | HTTP/ICS utilities exist; permitted live captures remain gated |
| Parse/normalize | Implemented foundation | ICS/HTML parsers and adapters; representative fixture coverage is incomplete |
| Provenance/raw evidence | Foundation present | Archives/metadata exist; retention, integrity and backup policy incomplete |
| Identity/history | Implemented in JSON | Stable IDs, observations, revisions, presence/lifecycle; DB pending |
| Publication approval | Implemented in JSON | Manual source-scoped approval/revocation; persistent audit history pending |
| Database | Not implemented | JSON state remains current backend; DB required for MVP |
| Read-only API | Local foundation | Query engine and loopback service; not database-backed; private/local use is the intended scope |
| Source-specific ICS | Offline/local foundation | Generator and loopback route; external stable URL not deployed |
| Calendar-client subscription | Not proven | No verified external endpoint/client end-to-end test |
| Webhooks | Spec only/deferred | Not needed for first useful calendar release |
| Polling/scheduler | Deferred | Intentionally excluded from MVP |
| Backup/restore | Not demonstrated | Recovery remains an MVP gap |
| MeaningWire | Future-compatible only | No runtime/dependency; correct MVP boundary |

## Scope alignment findings

The prior architecture described:
- Cloudflare Workers/D1/R2 as assumed target.
- Scheduled GitHub Actions polling.
- Gmail/Microsoft/IMAP mailbox ingestion.
- Community, organization, and category feeds.
- Cross-source canonical event merging.

These conflict with accepted decisions. The architecture is being reconciled to a personal-use, modular, portable application with one independent source relay per selected source, no combined feed, no cross-source merging, no mailbox dependency, no unattended polling, and no selected hosting provider. A public resident-facing directory or community service is not part of the product.

The source automation specification is a post-release proposal only. Its proposed live_capture_approved flag is not an MVP feature and must not be added by implication. No flag change itself triggers a task or network action.

## Highest-priority remaining work

1. Run the full test suite from a clean checkout and verify the newly added MIME, authorization-invariant, and archived ICS integration tests.
2. Complete source-specific evidence review without live retrieval unless separately authorized; keep snapshot completeness disabled until source coverage is demonstrated.
3. Finalize the SQLite schema and storage adapter.
4. Implement JSON-to-database migration, preserving stable IDs, observations, revisions, presence history, and publication approvals; prove parity and rollback.
5. Make the API and each independent ICS feed read from the same database-backed approved records.
6. Add operational readiness checks and validate source isolation, cache behavior, and error handling.
7. Define backup scope and retention; back up registry, database, raw captures, reports, and publication approvals; prove restore.
8. Only after the local service and recovery path are proven, separately decide the permitted access path for the user's calendar client.

## MVP exit test

Do not call MVP complete until demonstrated from a clean environment:
- Register one organization and multiple independent source records.
- Manually edit source authorization outside application execution.
- Ingest a representative fixture without changing protected flags.
- Persist organization, source, capture, event, observation, revision, presence/lifecycle and approval records in the database.
- Query records through the read-only API.
- Generate a source-specific ICS feed from the same database-backed approved records.
- Verify each feed excludes all other sources and unapproved events.
- Subscribe the user's calendar client to the intended stable endpoint and verify a subsequent approved update without duplicate churn.
- Back up and restore the database and raw archive.
- Demonstrate migration parity and rollback.
- Confirm no scheduled polling, webhook delivery, mailbox ingestion, or cross-source merge has been introduced without approval.

## Scope of this assessment

This assessment does not authorize database creation/migration, installations, dependency changes, live source capture, polling, public deployment, hosting selection, spending, or permission changes.
