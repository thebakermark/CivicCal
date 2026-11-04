# Source automation and task reconciliation

## Purpose

CivicCal should react to source configuration changes without relying on an operator to remember the next step. When an operational flag changes, monitoring determines whether work is now required, records a durable task, and lets a separate worker execute it only after rechecking all safety gates.

This is deterministic workflow automation. No LLM is used to decide eligibility, consent, task creation, or execution.

## Core model

- **Registry = desired state.** It records what the operator has approved or requested.
- **Monitor/reconciler = decision engine.** It compares desired state with source readiness and existing task/history.
- **Task queue = durable work record.** It records what needs to happen, why, and under which configuration version.
- **Workers = execution.** They perform capture, parsing, validation, or scheduler changes only after rechecking current policy.
- **Source state = observed facts.** Captures, validation results, health, and scheduler state are not inferred from registry flags.

A flag change is a signal to evaluate, not an instruction to blindly execute.

## Required monitoring behavior

Run reconciliation:
1. Immediately after a registry change made through a CivicCal command or API.
2. On application startup.
3. On a periodic safety interval, so missed filesystem notifications cannot leave the system stale.

For manually edited JSON files, compute a stable fingerprint of normalized source configuration. A filesystem watcher may trigger faster reconciliation, but it is only an optimization; periodic fingerprint comparison is authoritative.

Reconcile each source independently. Never infer approval or readiness from another source belonging to the same organization.

## Flag-to-action rules

| Changed condition | Reconciler action | Automatic network access? |
|---|---|---|
| Source registered or endpoint changed | Validate registry fields and endpoint; create review/validation tasks as appropriate | No |
| `access_status` becomes `approved` | Evaluate terms, robots, consent, source completeness, and parser readiness; create `capture_once` task only when all required gates pass and explicit live-capture approval is present | Only when the task worker executes after rechecking |
| `live_capture_approved` becomes `true` | Evaluate all capture gates; enqueue one initial capture if no successful capture exists for the current source configuration | Only after worker recheck |
| `polling_enabled` becomes `true` | Create `polling_enable_check`; validate prior capture, parser, source health, interval, host limits, and all permissions; activate schedule only when ready | No capture merely from the flag change |
| `polling_enabled` becomes `false` | Disable future scheduled runs and cancel queued polling tasks | No |
| Consent or access approval is withdrawn | Immediately suspend future capture and polling; cancel queued network tasks; mark in-flight work for safe cancellation where possible | No new requests |
| Parser or completeness profile changes | Invalidate affected validation fingerprint and enqueue revalidation; require recapture if the changed contract requires new evidence | Only after normal gates |
| Source is paused, blocked, or retired | Suspend automation and cancel queued work; preserve archive and event history | No |

The explicit `live_capture_approved` flag is a proposed addition to the registry. Until it is implemented, do not treat `access_status=approved` alone as a new independent approval mechanism; retain existing capture-script gates and require an operator-initiated one-shot command.

For consent-required sources such as Mokena SD159, written consent is an additional gate. It never replaces access approval, terms review, robots review, or explicit live-capture approval.

## Task record

Each task should include:

- Immutable task ID.
- Source ID and action type.
- Triggering configuration fingerprint.
- Idempotency key.
- Creation and update timestamps.
- Status: `pending`, `running`, `blocked`, `succeeded`, `failed`, `cancelled`, or `superseded`.
- Attempt count and next eligible attempt time.
- Structured prerequisite results and blocker explanations.
- Execution result, capture reference, and error classification.

Use an idempotency key derived from source ID, action type, and the relevant configuration fingerprint. Repeated reconciliation must update or reuse an existing task rather than enqueue duplicate work. A materially newer configuration may supersede an older pending task.

## Worker safety contract

A task worker must re-read the current source registry and task immediately before execution. It must revalidate:
- Source ID resolves to exactly one registry record.
- Source is not paused, blocked, or retired.
- Access approval and terms/robots review are current.
- Any required written consent is explicitly granted and documented.
- Explicit live-capture approval is present for network capture.
- Polling is enabled and all polling readiness checks pass for scheduled polling.
- Endpoint, source type, host/path allowlist, and parser configuration are valid.

If a gate fails, mark the task `blocked` with a human-readable reason. Never silently override a flag or infer permission. If approval is withdrawn while a task is queued, cancel it. If withdrawn during a request, stop before any subsequent request and record what already occurred.

## Polling readiness

Polling activation requires:
1. Explicit live-capture approval.
2. Required written consent, where applicable.
3. Terms and robots review complete.
4. A successful archived initial capture.
5. Parser/adapter validation against a real source fixture.
6. Source completeness policy verified for the intended capture scope.
7. Event provenance and source ownership validated.
8. Source-specific ICS/API projection tested.
9. A valid polling interval and per-host rate-limit policy.
10. No unresolved blocking source-health condition.

A request to enable polling creates a readiness task. The scheduler must not add the source until the readiness task succeeds. If any prerequisite later becomes false, the monitor suspends the schedule.

## Operator visibility

Provide a source automation status view showing, per source:
- Current configured flags.
- Current effective state (review required, capture eligible, capture pending, captured, validation pending, polling blocked, polling active, paused, etc.).
- Pending and recent tasks.
- Exact blockers and the flag or evidence needed to resolve each blocker.
- Last capture, last successful poll, and last error.

The operator should be able to pause a source immediately and inspect why a task did or did not run.

## Storage and implementation sequence

The task queue and configuration-change history must be durable and transactional. Keep the interface storage-independent now; implement the persistent task store alongside the selected database backend rather than using an in-memory queue that can lose work on restart.

Recommended sequence:
1. Define source configuration fingerprints and task contracts.
2. Implement deterministic reconciliation with unit tests.
3. Add durable task storage and idempotency.
4. Add worker execution with gate revalidation.
5. Add polling scheduler integration and pause/cancel behavior.
6. Add source automation status reporting.
7. Test approval, revocation, duplicate reconciliation, restarts, and failure recovery.

## Non-goals and safeguards

- No automatic approval, consent granting, or terms interpretation.
- No LLM in workflow decisions.
- No cross-source approval inheritance.
- No event auto-approval or publication as a side effect of capture.
- No deletion of archives or event history when a source is disabled.
- No automatic network access from the registry monitor itself.
- No public deployment or unattended polling until explicitly authorized.
