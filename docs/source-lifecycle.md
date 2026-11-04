# Source Lifecycle and Capture Contract

## Purpose

Define how CivicCal discovers, registers, captures, and monitors publisher-controlled event sources. Source handling must be reusable across publishers and auditable after failures.

## Source record

Each source should have, at minimum:

- `source_id`: immutable CivicCal identifier.
- `organization_id`: publisher/organization identifier.
- `display_name`: human-readable source name.
- `source_type`: `ics`, `rss`, `atom`, `json_api`, `jsonld_html`, `html_adapter`, or explicitly scoped `email`.
- `url`: canonical source URL, where applicable.
- `status`: `discovered`, `review_required`, `approved`, `paused`, `blocked`, or `retired`.
- `polling_enabled`: explicit operational switch; default false for newly discovered sources.
- `poll_interval` and scheduling policy.
- `timezone_policy`: source-declared, explicit configured IANA zone, or unresolved.
- `geographic_scope` and content scope.
- `terms_reviewed`, `robots_reviewed`, and any source-specific consent flags when applicable.
- `created_at`, `updated_at`, `last_success_at`, `last_attempt_at`, and health state.
- Notes, evidence URLs, and operator decisions.

The registry describes the source and its operating policy. It is not itself proof that an event was captured or validated.

## Discovery and onboarding

1. Find the publisher's official events page or feed.
2. Prefer publisher-provided ICS, RSS, Atom, or documented public API when available.
3. Identify whether separate calendars exist for departments, campuses, schools, or event categories.
4. Record the exact endpoint and how it was verified.
5. Determine source format and whether an adapter is needed.
6. Record timezone behavior and any ambiguity.
7. Record relevant source access/consent settings.
8. Add a registry record in a non-active review state.
9. Capture a bounded sample only when the source's configured gates permit it.
10. Create a fixture and adapter tests before relying on the source in routine ingestion.

Do not infer an endpoint ID from a neighboring ID. Do not treat a visible page as proof that its ICS endpoint has the same content.

## Capture interface

The first implementation is `scripts/capture_source.py`. It is a manual, one-source-at-a-time HTTP capture command. It supports the registry's HTTP source types (ICS, RSS, Atom, JSON API, and HTML) and deliberately does not parse events, update the registry, publish content, or schedule polling.

Example:

```sh
python scripts/capture_source.py --source-id example-source --archive-dir data/captures
```

For a later capture, pass the previous metadata file with `--previous-metadata`; CivicCal sends its ETag and Last-Modified values as conditional request headers. A 304 response is recorded as an unchanged capture and does not create a payload file. For a paginated listing or linked detail page, `--request-url` may be used only when the requested HTTPS host and exact path appear in that source's `data/source-completeness.json` allowlist. Set `--page-role` to `listing`, `detail`, or `feed` so the archived capture can be audited and entered into a snapshot manifest. This is still one page per command; it is not an automatic crawler.

Successful response bodies are stored by SHA-256 under `<archive>/<source-id>/`, with a JSON metadata sidecar. The tool enforces HTTPS, blocks non-HTTPS redirect targets before following them, rejects credential-bearing URLs, applies a 20 MiB response limit, and uses a bounded request timeout. Existing source eligibility and the explicit written-consent switch are preserved. This is not a polling worker.

A capture adapter should accept a source record and a capture context and return:

- Raw response bytes or a durable raw-payload reference.
- Requested URL and final URL.
- HTTP status and response headers.
- Capture timestamp.
- Content type and content length.
- ETag and Last-Modified, when supplied.
- Payload hash.
- Fetch duration and retry information.
- Warnings or failure classification.

Adapters should not write canonical events directly. Capture and parsing are separate stages.

## HTTP behavior

- HTTPS by default; exceptions require an explicit documented decision.
- Use a descriptive CivicCal User-Agent with a project contact or repository URL.
- Set connection and read timeouts.
- Enforce configurable response-size limits.
- Respect redirects according to a documented policy; never forward credentials across origins.
- Use conditional GET with ETag and/or Last-Modified.
- Apply per-host rate limits, jitter, bounded retries, and exponential backoff.
- Treat 304 Not Modified as a successful unchanged capture.
- Distinguish transient errors, permanent errors, malformed content, and policy-disabled sources.
- Do not retry indefinitely.

## MVP manual operation and post-release automation

For the MVP, source operation is manual. An operator changes the explicit registry flags and separately initiates any permitted one-shot capture. Changing a flag does not trigger a task, network request, capture, or polling activation.

`polling_enabled` remains false by default. A true value is configuration only until a polling scheduler is implemented and the operator explicitly enables it under the documented readiness gates. No background polling is part of the MVP.

After release, CivicCal may add a deterministic reconciler and durable task queue to detect configuration changes and identify required work. That enhancement is specified separately in `docs/source-automation.md`. It must not be treated as implemented MVP behavior. Any future worker must re-read the current registry and recheck all access, terms, robots, consent, and explicit approval gates immediately before network access.

## Raw capture archive

Store each distinct successful response (or a content-addressed reference to it) with capture metadata. Preserve enough information to reproduce parsing and investigate source changes.

Avoid storing credentials or unrelated personal information. Define retention and storage limits before production operation.

## Source health

Track:
- Last attempt and last successful capture.
- Last content change.
- Consecutive failures.
- Last HTTP status.
- Parser/adapter warnings.
- Average response size and duration.
- Current operational state.

A source can be healthy even when unchanged. A source can be failing even when its last known events remain published.

## Email sources

Email is optional and must be explicitly scoped. Register the mailbox/folder and sender or message rules. Never scan a personal inbox indiscriminately. Keep credentials outside the source registry and logs.

## Existing CivicCal behavior

The source registry, ICS importer, HTML adapters, and one-shot capture command provide the current foundation. Capture and parsing remain separate. The capture command has automated unit tests for eligibility gates, written consent, conditional headers, HTTP 304, content hashing, raw archive writes, and unsafe redirects. Source completeness is validated separately through `scripts/validate_snapshot.py` and `data/source-completeness.json`; every current live profile remains disabled pending real captured-page verification. Automatic multi-page crawling and detail-page retrieval are not implemented. Scheduled polling, retries/backoff, per-host rate limiting, database-backed source health, and retention management are also not implemented.
