# Source Authorization Control Boundary

**Status:** mandatory design invariant. This document clarifies the authority model for current JSON configuration and any future database-backed implementation.

## 1. Human-controlled authorization

Authorization flags are changed manually by an authorized human operator in the source registry/configuration process.

CivicCal application code may read, validate, display, and enforce those values. It must not grant, revoke, infer, or silently alter authorization.

This applies to current JSON configuration and future database-backed storage. Moving configuration into a database does not transfer decision-making authority to the application.

## 2. Read-and-enforce only

Application behavior is limited to:

- read authorization and policy flags;
- validate that required approvals are present;
- refuse an operation when a required flag is absent, false, malformed, or ambiguous;
- report which prerequisite is missing;
- record operational facts such as capture outcomes and processing timestamps without changing authorization.

The application must not provide a runtime administrative operation, API route, CLI command, scheduled task, migration, or background worker that changes authorization flags.

## 3. Protected fields

The following fields are human-controlled authorization/configuration values and must never be changed by normal application execution:

- `access_status`
- `terms_reviewed`
- `robots_reviewed`
- `consent_required`
- `consent_granted`
- `polling_enabled`

Any additional field that grants permission, records consent, waives a policy gate, or enables automated access is subject to the same rule.

In particular:

- `polling_enabled` remains false unless a human manually changes it after the required review.
- `consent_granted` remains false until the required written consent has actually been received and a human manually records that decision.
- A flag change does not itself initiate capture, polling, scheduling, or publication.
- A one-shot capture still requires an explicit operator invocation and all eligibility checks.

## 4. Database implications

The future database may store these values so the application can enforce them. It must not expose a general-purpose application write path for them.

For the initial database design:

- treat protected fields as operator-managed configuration;
- provide read/query access to the capture and ingestion code;
- do not include them in ordinary event-ingestion update statements;
- do not change them during migration, normalization, defaulting, repair, or cutover;
- import their existing values exactly, including false values and review-required states;
- fail closed if a required value is missing or malformed;
- require a separate, explicitly approved human-operated configuration procedure for any future change in how these values are edited.

No automated migration may promote a source to approved, mark terms/robots reviewed, grant consent, or enable polling.

## 5. Tests and review

Before a database implementation is accepted, tests must demonstrate:

1. Ingestion cannot change protected authorization fields.
2. Reprocessing a capture cannot change protected authorization fields.
3. Migration preserves the exact values and does not enable a source.
4. Missing or malformed required flags cause capture to fail closed.
5. No application API, CLI, worker, or scheduled task offers an authorization-changing operation.
6. Updating ordinary operational metadata does not overwrite concurrent or manually edited authorization configuration.

## 6. Existing behavior

The current `capture_source.py` reads the source registry and enforces access status, terms review, robots review, and written consent where required. It does not write changes to the registry. The source registry remains a manually edited control surface.

## 7. Related architecture

- [Database schema and migration design](database-schema-and-migration.md)
- [Storage contracts](storage-contracts.md)
- [Roadmap](roadmap.md)
