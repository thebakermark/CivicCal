# Processing Pipeline

## Pipeline boundaries

CivicCal separates retrieval, parsing, normalization, reconciliation, storage, and publication. Each stage has a clear input and output so failures can be retried without repeating successful earlier work.

```
Source registry
    |
Capture scheduler / manual capture
    |
Raw capture archive + response metadata
    |
Parser / source adapter
    |
Source observations
    |
Normalization + validation
    |
Identity and reconciliation
    |
Canonical events + revisions + review candidates
    |
Publication projections
    +--> JSON API
    +--> iCalendar feeds
    +--> Webhook outbox
```

## Stage 1: Capture

The capture engine retrieves source content according to the source record. It records the response, headers, timestamp, payload hash, and outcome. An unchanged response (HTTP 304 or matching payload hash) can skip downstream parsing.

## Stage 2: Parse

A parser converts raw source content into source observations. It must:
- Be deterministic for a given payload and parser version.
- Preserve source identifiers and original values.
- Emit structured warnings for unsupported or malformed fields.
- Never silently invent missing event details.
- Avoid writing canonical records directly.

Use format-level parsers where possible and source-specific adapters only where the publisher's markup requires them.

## Stage 3: Normalize

Normalization maps source observations into CivicCal's canonical vocabulary:
- Date/time semantics and timezone status.
- All-day and timed events.
- Locations and links.
- Registration details and deadlines.
- Categories, audience, and status.
- Recurrence and exception metadata.

Keep original source strings alongside normalized values.

## Stage 4: Validate

Validation checks structural and semantic consistency:
- Required identity/title data.
- Valid date/time representations.
- End not before start where both are supplied.
- Explicit timezone semantics.
- URL validity and safe schemes.
- Plausible but not over-restrictive date ranges.
- Registration deadline not accidentally treated as event date.
- No source fields silently dropped.

Warnings should not automatically discard useful events. Fatal parsing errors should be isolated to the affected record or capture where possible.

## Stage 5: Reconcile

Compare new observations with prior observations for the same source:
- New source event.
- Unchanged event.
- Material update.
- Explicit cancellation.
- Missing from current capture.
- Ambiguous identity or possible duplicate.

Use stable source identifiers first. Fallback matching must be deterministic and produce review candidates when uncertain.

## Stage 6: Persist

Write source observations, canonical event changes, revisions, and audit records transactionally. Reprocessing the same capture should be idempotent.

## Stage 7: Publish

Generate read-only API and feed projections from stored canonical data. Publication must not mutate source observations. Webhook messages are created through a transactional outbox so a database commit cannot be lost between persistence and notification.

## Failure isolation

- A single bad event must not invalidate unrelated valid events in the same feed.
- A failed source must not erase previously stored events.
- A failed publisher must not prevent other sources from processing.
- Repeated processing of the same capture must not create duplicate revisions.
- Parser upgrades should be replayable against archived captures.

## Determinism

No LLM is required for capture eligibility, parsing, identity, deduplication decisions, cancellation, or publication. Optional future classification or assisted review must be advisory and must not silently alter source facts.
