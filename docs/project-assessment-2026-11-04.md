# CivicCal Project Assessment — 2026-11-04

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

Current source authorization state: 11 sources are review_required and 1 source (Mokena SD159) is blocked. All 12 have polling_enabled=false. This is the correct conservative state; source records being present does not mean capture permission has been granted.

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
| Read-only API | Local foundation | Query engine and loopback service; not database-backed/public; organization/source directory endpoints still missing |
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

These conflict with accepted decisions. The architecture is being reconciled to a modular, portable application with one independent source relay per source, no combined feed, no cross-source merging, no mailbox dependency, no unattended polling, and no selected hosting provider.

The source automation specification is a post-release proposal only. Its proposed live_capture_approved flag is not an MVP feature and must not be added by implication. No flag change itself triggers a task or network action.

## Highest-priority remaining work

1. Maintain one authoritative requirements, decision, and feature register.
2. Complete the Schema.org mapping without changing CivicCal's internal event model.
3. Audit actual code/tests against manual authorization invariants.
4. Complete source coverage/fixture validation for initial Mokena-area sources without activating unauthorized sources.
5. Finalize database schema and migration details; implementation waits for user review/target environment.
6. Implement database persistence and prove JSON-to-DB parity, rollback, and authorization preservation.
7. Make API and source-specific ICS read from the same database-backed approved records.
8. Define backup/restore and prove recovery.
9. Only after the local end-to-end loop works, separately decide whether to authorize public hosting/deployment.
10. Add webhook delivery after MVP; keep its standard contract documented.

## MVP exit test

Do not call MVP complete until demonstrated from a clean environment:
- Register one organization and multiple independent source records.
- Manually edit source authorization outside application execution.
- Ingest a representative fixture without changing protected flags.
- Persist organization, source, capture, event, observation, revision, presence/lifecycle and approval records in the database.
- Query records through the read-only API.
- Generate a source-specific ICS feed from the same database-backed approved records.
- Verify each feed excludes all other sources and unapproved events.
- Subscribe a real calendar client to a stable external endpoint and verify a subsequent approved update without duplicate churn.
- Back up and restore the database and raw archive.
- Demonstrate migration parity and rollback.
- Confirm no scheduled polling, webhook delivery, mailbox ingestion, or cross-source merge has been introduced without approval.

## Scope of this assessment

This assessment does not authorize database creation/migration, installations, dependency changes, live source capture, polling, public deployment, hosting selection, spending, or permission changes.
