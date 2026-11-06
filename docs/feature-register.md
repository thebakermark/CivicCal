# CivicCal Feature Register

This is the implementation tracker. Product requirements and accepted decisions live in Product Requirements and Decision Register. This register answers what exists, what is incomplete, and what evidence is needed before calling it done.

**Last audited:** 2026-11-06  
**Rule:** Implemented means code exists; verified means relevant automated tests/CI or an explicit end-to-end check demonstrate the acceptance behavior. A document is not implementation.

| ID | Feature | Current state | Evidence / gap | Next completion gate |
|---|---|---|---|---|
| F-001 | Organization/source registry | Implemented foundation | data/sources.json, JSON Schema, validator | Audit every source identity, scope, and evidence |
| F-002 | Manual authorization gates | Implemented foundation | capture_source.py checks access, terms, robots, consent; test_capture_source.py verifies protected registry fields remain unchanged during source loading | Extend invariant coverage to every future persistence/migration path; preserve in DB |
| F-003 | One-shot HTTP/HTML capture | Implemented | Capture utility and tests; completeness separate | Verify permitted live captures only after human authorization |
| F-004 | One-shot ICS capture/import | Implemented foundation | ICS coordinator/importer/parser; tests cover registered text/calendar and valid ICS labeled application/octet-stream | Validate source coverage and temporal fidelity; test results still require a clean CI run |
| F-005 | Raw capture archive/provenance | Implemented foundation | Capture metadata and archive files | Define retention, integrity verification, backup/restore |
| F-006 | HTML/ICS parsing | Implemented foundation | ICS, Park District, Village parser fixtures plus Mokena Library manual-snapshot normalization; archived ICS-to-identity integration test added | Add authorized raw HTML/feed fixtures for remaining sources; manual snapshots are not parser fixtures; verify clean CI run |
| F-007 | Event normalization | Implemented foundation | Normalizer and tests | Audit field completeness and temporal edge cases |
| F-008 | Stable source-scoped identity | Implemented | Identity tracker and tests | Preserve exact IDs through DB migration |
| F-009 | Observations/revisions/presence/lifecycle | Implemented in JSON | Tracker and relational design docs | Implement relational persistence after approval; parity tests |
| F-010 | Duplicate candidate detection | Implemented foundation | Candidate finder; no auto-merge | Review workflow only if needed for MVP |
| F-011 | Manual publication approval | Implemented | set_publication.py, manifest, tests | Persist current approval + audit history in DB |
| F-012 | Source-specific ICS generation | Implemented offline | publish_ics.py; tests | Recurrence/update/cancellation interoperability validation |
| F-013 | Read-only JSON query API | Implemented local foundation | Query engine + loopback server | DB-backed queries, OpenAPI contract parity, public delivery only after approval |
| F-014 | Source-specific HTTP ICS route | Implemented local foundation | Loopback route in serve_api.py | DB-backed route; stable external URL requires approved deployment |
| F-015 | Schema.org mapping | Implemented foundation | `scripts/schemaorg.py`, `tests/test_schemaorg.py`; pure, non-mutating Event projection | Expand mapping coverage as the domain model matures; verify time and recurrence interoperability |
| F-016 | Database persistence | Designed, not implemented | Schema, storage contracts, JSON mapping, event history design | User review, then implementation/migration in target environment |
| F-017 | Migration and rollback | Designed, not implemented | JSON migration map and schema doc | Executable dry-run, parity report, backup/restore, explicit cutover approval |
| F-018 | Source health reporting | Implemented offline foundation | Health report and tests | Persist run history and operational health in DB |
| F-019 | Backup/restore | Not implemented as service | No verified end-to-end backup/restore | Define backup scope and demonstrate clean restore |
| F-020 | Public deployment/remote access | Not implemented; approval required | Current server loopback only | Separate deployment design and explicit approval |
| F-021 | Stable external subscriptions | Not complete | ICS generation works; route loopback-only | Deployed source URL and real calendar-client subscription test |
| F-022 | Webhook delivery | Deferred | Contract document only | After MVP API/ICS/database loop |
| F-023 | Automated polling/scheduler | Deferred; not MVP | One-shot manual capture only | Do not implement without new explicit approval |
| F-024 | Email/mailbox ingestion | Deferred; not MVP | Old architecture references are superseded | Separate explicit decision and authorization |
| F-025 | User-facing web UI/accounts | Deferred; not MVP | No implementation | Revisit only after core service works |
| F-026 | MeaningWire adapter | Future-compatible only | Semantic boundary documented | Wait for MeaningWire contracts and separate approval |

## Feature status definitions

- **Not started:** no meaningful code or design.
- **Designed:** contract/specification exists, code not implemented.
- **Implemented foundation:** partial implementation exists; acceptance is incomplete.
- **Implemented:** code exists for the defined scope.
- **Verified:** acceptance behavior has test or operational evidence.
- **Deferred:** intentionally outside current release.
- **Blocked:** cannot proceed until a named dependency or decision is resolved.

## Change tracking

For every accepted feature addition/change:
1. Add or update a requirement ID in product-requirements.md.
2. Add a decision-register entry if it changes an accepted product decision.
3. Add/update a row here with status and evidence.
4. Link implementation and test files.
5. Update roadmap only if sequence or release scope changes.
6. Never mark verified based solely on documentation or unexecuted tests.
