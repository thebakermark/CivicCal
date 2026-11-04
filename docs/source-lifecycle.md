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

## Scheduling

The initial design uses a simple scheduler (systemd timer or cron) that invokes a worker, processes due sources, records results, and exits.

Polling interval is source-specific and should reflect publisher update frequency and server load. Manual one-shot capture must remain distinct from scheduled polling.

No polling is enabled merely because a source is registered or has been tested.

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

The current registry, ICS importer, and HTML adapters provide foundations, not a complete general-purpose capture engine. The current importer has source-specific gates and a manual one-shot path. Preserve those controls when building the generalized interface.
