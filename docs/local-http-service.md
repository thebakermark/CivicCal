# Local read-only HTTP service

**Status:** implemented for local development; not deployed or exposed to a network.

`scripts/serve_api.py` wraps the existing approved-event JSON query and iCalendar projection with Python's standard-library HTTP server. It reads the identity-state and publication-manifest JSON files on each request, so it reflects updated files without a database or process restart.

## Run locally

```sh
python scripts/serve_api.py \
  --state data/state/identity.json \
  --manifest data/publication/community.json \
  --host 127.0.0.1 \
  --port 8765
```

The server refuses non-loopback bind addresses. It is read-only: POST, PUT, and DELETE are not supported. This is a development interface, not a production deployment configuration.

## Routes

| Method and path | Purpose |
|---|---|
| `GET /health` | Minimal service health response |
| `GET /api/v1/events` | Approved events with date, source, category, text, and pagination filters |
| `GET /calendars/community.ics` | Approved community iCalendar feed |
| `GET /api/v1/openapi.json` | Machine-readable OpenAPI document |

Supported event query parameters: `start_date`, `end_date`, `source_id`, `category`, `q`, `limit` (1–100), and `offset` (zero-based). Date bounds are inclusive and apply to the event's published start date.

## HTTP behavior

- JSON uses `application/json`; calendar feeds use `text/calendar`.
- ETags are generated from response bytes and `If-None-Match` is honored with `304 Not Modified`.
- `Last-Modified` reflects the latest observed revision among explicitly approved events when available.
- Cache policy is currently `public, max-age=60` for this local read-only prototype.
- Invalid queries return `400`; missing or invalid data files return `503`; unknown routes return `404`.
- Query strings are not written to the default request log.

## Publication boundary

Both JSON and ICS routes use the same explicit `approved_event_ids` manifest. Records absent from that manifest are not returned, even if they exist in identity state. Internal source payloads, capture headers, and organizer contact details are not part of the public projection.

## Deliberate omissions

No public bind, TLS, authentication, admin routes, organization/source feed variants, individual-event retrieval, rate limiting, webhook delivery, scheduler, or deployment configuration is included. Those require separate design and explicit approval. This server is a local integration harness for validating the API and feed contracts before selecting a database or hosting model.

## Tests

`tests/test_serve_api.py` exercises approved-only responses, filters, ICS output, ETag/304 behavior, invalid queries, unknown routes, health, and OpenAPI discovery.