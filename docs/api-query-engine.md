# Read-only JSON query projection

**Status:** offline query engine implemented; no HTTP API server is deployed.

`scripts/query_events.py` builds a deterministic `civiccal.api-events.v1` response from the source-scoped identity state and the same explicit publication manifest used by the iCalendar publisher.

## Command

```sh
python scripts/query_events.py \
  data/state/identity.json \
  data/publication/community.json \
  --start-date 2026-11-01 \
  --end-date 2026-11-30 \
  --limit 50 \
  --offset 0 \
  --output data/published/community-events.json
```

## Filters

- `start_date` and `end_date`: inclusive date bounds applied to the event's published local/date value, not UTC conversion.
- `source_id`: exact registered source identifier.
- `category`: exact case-insensitive category match.
- `q`: case-insensitive substring search over title and description.
- `limit`: 1–100; default 50.
- `offset`: zero-based; default 0.

Results sort by event date and then stable CivicCal event ID. Pagination reports total matching records and the next offset.

## Publication and privacy boundary

Only event IDs explicitly listed in `civiccal.publication-manifest.v1` are queryable. The projection uses a field allowlist and deliberately excludes raw `source_record`, capture headers, internal observations, identity keys, revision history, and administrative metadata. The publisher's current event fields are returned with stable event ID, source ID, revision number, and lifecycle status.

The query engine does not approve events, modify identity state, merge duplicates, infer dates, or perform network access. The publication manifest is the shared gate for JSON and iCalendar projections.

## Service boundary

This is a file-based query engine, not an HTTP API. Routing, authentication for administrative operations, HTTP caching/ETags, OpenAPI serving, rate limiting, and deployment remain future service-layer work. The query logic is independent of the deferred database choice.

## Tests

`tests/test_query_events.py` covers approval filtering, inclusive date filtering, source/category/text filters, stable ordering, pagination, invalid query inputs, missing approved IDs, and exclusion of internal source payloads.