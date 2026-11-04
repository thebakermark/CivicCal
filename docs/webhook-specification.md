# Webhook Specification

## Status

Planned integration interface. Webhooks are not required for the first usable calendar release; stable ICS feeds and the read-only API come first.

## Purpose

Notify external applications when published events are created, materially updated, cancelled, or restored. A webhook is a notification mechanism, not a replacement for the API or calendar feeds.

## Event envelope

Use CloudEvents as the starting envelope. Each notification should include:
- `specversion`
- `id`: unique notification ID.
- `source`: CivicCal event or service URI.
- `type`: documented event type.
- `subject`: affected CivicCal resource.
- `time`: notification creation time.
- `datacontenttype`
- `data`: event ID, revision, change summary, and retrieval URL.

Initial event types:
- `org.civiccal.event.created`
- `org.civiccal.event.updated`
- `org.civiccal.event.cancelled`
- `org.civiccal.event.restored`

The event data should avoid copying unnecessary personal information. Consumers can fetch the full current representation from the API.

## Subscription management

A subscriber should be able to:
- Register an HTTPS endpoint.
- Select event types and optional organization/category filters.
- Verify endpoint ownership.
- Rotate or revoke its signing secret.
- Pause, resume, and delete the subscription.
- Inspect recent delivery outcomes.

Subscriber management is an authenticated administrative function and is not part of the anonymous public API.

## Request signing

Sign the exact request body using HMAC-SHA256 and a per-subscription secret. Include a timestamp and signature header. Document canonicalization, encoding, timestamp tolerance, and secret rotation. Receivers must be able to reject stale or invalid signatures.

Never store secrets in plaintext or include them in logs.

## Delivery semantics

- At-least-once delivery; consumers must be idempotent.
- Stable notification ID across retries.
- Bounded exponential retry with jitter.
- Record attempt number, response status, latency, and next retry time.
- Pause or disable endpoints after repeated permanent failures, with visible operator status.
- Provide manual redelivery for authorized operators.
- Do not promise exactly-once delivery.

## Reliability

Create webhook outbox records in the same database transaction as the event revision. A separate worker delivers pending messages. This prevents a crash between committing an event and scheduling its notification from losing the notification.

## Security

- HTTPS only.
- Validate DNS/IP targets to mitigate SSRF and block loopback, link-local, private, and metadata-service destinations unless explicitly allowed by deployment policy.
- Revalidate destination addresses at delivery time to reduce DNS rebinding risk.
- Limit response time and response size.
- Never follow redirects to unvalidated destinations.
- Rate-limit registration and delivery.
- Keep secrets out of URLs and logs.

## Initial scope boundary

No webhook UI or delivery worker is needed before API and ICS publishing are dependable. Keep the envelope and outbox design documented now so later implementation does not require redesigning event storage.
