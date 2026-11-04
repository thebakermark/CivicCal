# One-shot Capture Coordinator

## Purpose

`scripts/capture_coordinator.py` connects the existing source registry, raw capture archive, Village HTML adapter, event normalizer, and snapshot completeness validator into one manually initiated run.

It currently supports only `village-of-mokena-events`, because that source has a known listing-to-detail-page shape. It does not guess how other publishers paginate.

## Run

From the repository root:

```sh
python scripts/capture_coordinator.py \
  --source-id village-of-mokena-events \
  --archive-dir data/captures \
  --output data/processed/village-events.json
```

The command first applies the normal source registry eligibility gates. The Village source is currently `review_required`, so the command will stop before making a network request until its registry gates are deliberately resolved. This documentation does not authorize a live capture.

Optional bounds:

- `--max-pages` (default 20): maximum listing pages to traverse.
- `--max-details` (default 500): maximum linked event-detail pages to retrieve.
- `--timeout` (default 20 seconds): per-request timeout, bounded to 1–120 seconds by the underlying capture utility.

## Workflow

1. Load exactly one source and its source-specific completeness profile.
2. Validate the initial listing URL against the profile's host/path allowlist.
3. Capture the listing page using the existing HTTPS-only capture utility and content-addressed archive.
4. Parse the listing with `scripts/parse_village.py`.
5. Queue only explicit `rel="next"` links and extracted `calendarView.aspx?cid=...` detail links.
6. Validate every queued URL against the same source allowlist before requesting it.
7. Follow pagination with cycle detection and a page limit.
8. Capture and parse each unique detail ID, checking that the returned event ID matches the linked ID.
9. Normalize each event while retaining its individual capture provenance.
10. Assemble the snapshot manifest and run the existing completeness validator.
11. Write one JSON result containing normalized events, page-level parser output, raw-capture metadata references, manifest, completeness decision, and warnings.

Every successful page response is archived as a raw content-addressed payload plus timestamped metadata. The coordinator does not overwrite the source registry.

## Safety and completeness

- Redirect destinations are checked against the source-specific allowlist before following the redirect.
- Only credential-free HTTPS URLs on the configured hosts and exact paths are accepted.
- The existing source access and consent gates remain mandatory.
- A failed page, unparsed page, missing detail, page limit, detail limit, or pagination cycle prevents a complete snapshot.
- The coordinator never infers cancellation or deletion from an event missing from the current result.
- Current Village policy keeps `allow_complete_snapshot: false`; therefore a successful run still reports `unknown` until real archived captures establish the publisher's actual pagination and coverage behavior.
- The coordinator does not schedule itself, poll automatically, write a database, merge duplicates, or publish feeds/webhooks.

## Current boundary

This is an initial coordinator for the Village MunicipalCMS listing/detail pattern. The Park District editorial page is not a complete organization-wide calendar, and the Summit Hill sources are single-feed ICS sources; neither is routed through this HTML coordinator. Future coordinators should be separate adapters selected by explicit source policy, not inferred from a URL or a successful HTTP response.
