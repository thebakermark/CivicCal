# Source Automation — Deferred and Not Approved

**Status:** not part of the MVP; no automation implementation is authorized by this document.

## Current rule

Source operation is manual:

1. An authorized human manually edits source authorization flags in the registry.
2. Changing a flag has no side effect.
3. The operator separately invokes a permitted one-shot capture.
4. Capture code reads and enforces the current flags but never writes them.

No flag change may trigger a task, network request, capture, polling, publication, or other automated action.

## Protected authorization fields

At minimum:

- access_status
- terms_reviewed
- robots_reviewed
- consent_required
- consent_granted
- polling_enabled

Python, the application, a migration, or a background process must never change these fields. They remain manually edited by a human. See [Source Authorization Control Boundary](source-authorization-boundary.md).

## Deferred possibilities

A future proposal may consider operational monitoring or scheduled polling, but it must be separately scoped and explicitly accepted before implementation. Such a proposal must not:
- edit authorization flags;
- infer consent or approval;
- treat a flag edit as an instruction to perform work;
- enable polling by default;
- grant permission or publish events;
- use an LLM to make policy decisions.

No filesystem watcher, registry reconciler, task queue, background worker, or polling scheduler is part of the current project scope.

## Related decisions

See [Decision Register](decision-register.md), especially DEC-005 through DEC-007.
