# Source Completeness and Pagination

## Purpose

A successful HTTP response is not proof that CivicCal has received every page or every event represented by a source. This contract separates:

1. Capture success (did each requested page download?)
2. Parse success (did each page parse?)
3. Pagination completion (were all pages in the configured listing traversed?)
4. Detail coverage (were all event links discovered in listings resolved?)
5. Source scope (what exact publisher listing does the result represent?)

Only a source-specific policy that explicitly permits completeness can produce `snapshot.completeness: "complete"` for the identity tracker.

## Source-specific policy

Policies live in `data/source-completeness.json`. Each profile defines:

- The exact source ID and scope.
- Pagination strategy: `single_feed`, `single_page`, or `rel_next`.
- Required page roles.
- Whether listing detail links must reconcile with successfully parsed detail pages.
- Whether complete snapshots are currently permitted.

All current profiles have `allow_complete_snapshot: false`. This is deliberate:

- Village of Mokena: its listing/detail relationship and real pagination markup still need validation from archived live pages.
- Mokena Park District: its page is a curated Upcoming Events editorial listing, not the full program, class, sports, or facility schedule. The checked-in fixture is representative, not a complete capture.
- Summit Hill ICS calendars: actual feed payloads have not yet been archived and checked against the visible publisher calendars.

No current live source is authorized by this file to mark previously observed events missing.

## Village pagination discovery

`scripts/parse_village.py` now reports links with HTML `rel="next"` as pagination candidates. It always reports `terminal_page_confirmed: false`. Finding no `rel="next"` link is not proof that there are no more pages; the publisher may use another paging mechanism or a bounded date window.

The Village parser continues to treat calendar listing pages as indexes. Each discovered `calendarView.aspx?cid=...` link must be captured and parsed as an event detail page. Listing grid positions are not used to invent event dates.

## Snapshot manifest

After pages have been captured and parsed, a deterministic manifest records the evidence. The manifest is an explicit record of the page set, not a crawler instruction.

Example shape:

```json
{
  "format": "civiccal.snapshot-manifest.v1",
  "source_id": "village-of-mokena-events",
  "pagination": {
    "strategy": "rel_next",
    "expected_page_count": 2,
    "observed_page_count": 2,
    "terminal_page_confirmed": true,
    "pending_next_urls": []
  },
  "pages": [
    {
      "role": "listing",
      "url": "https://www.mokena.gov/calendar.aspx",
      "capture_outcome": "captured",
      "http_status": 200,
      "parse_status": "success",
      "content_sha256": "<64-character-payload-hash>",
      "source_event_ids": [],
      "discovered_detail_ids": ["30642", "30379"]
    },
    {
      "role": "detail",
      "url": "https://mokenail.municipalone.com/calendarView.aspx?cid=30642",
      "capture_outcome": "captured",
      "http_status": 200,
      "parse_status": "success",
      "content_sha256": "<64-character-payload-hash>",
      "source_event_ids": ["30642"]
    },
    {
      "role": "detail",
      "url": "https://mokenail.municipalone.com/calendarView.aspx?cid=30379",
      "capture_outcome": "captured",
      "http_status": 200,
      "parse_status": "success",
      "content_sha256": "<64-character-payload-hash>",
      "source_event_ids": ["30379"]
    }
  ]
}
```

The example illustrates the manifest contract; its page count and URLs are not a claim that a complete live Village capture has been performed. When source access gates permit capture, each page can be archived individually using the allowlisted `--request-url` option, for example:

```sh
python scripts/capture_source.py --source-id village-of-mokena-events \\
  --request-url 'https://mokenail.municipalone.com/calendarView.aspx?cid=30642' \\
  --page-role detail --archive-dir data/captures
```

The actual Village source is still `review_required`, so this example does not authorize or enable a network request. The source policy allowlist limits the host and exact path; it does not override source eligibility or consent gates. For a real manifest, `expected_page_count` and `observed_page_count` must both equal the number of supplied page records. Listing pages provide `discovered_detail_ids`; detail pages provide the publisher IDs actually parsed.

For a single ICS feed, use one `feed` page record and include its parsed publisher IDs in `source_event_ids`. A single response is not automatically complete: the source policy must allow it and the manifest must confirm successful capture and parsing.

## Validation and handoff

Run the offline validator against a normalized event document and a manifest:

```sh
python scripts/validate_snapshot.py normalized.json \
  --manifest snapshot-manifest.json \
  --policies data/source-completeness.json \
  --output normalized-with-snapshot.json
```

The validator checks:

- Exactly one source policy exists for the normalized source.
- The manifest uses the expected pagination strategy.
- Expected, observed, and supplied page counts agree.
- The terminal page is explicitly confirmed and no next-page URLs remain.
- Every page has HTTPS provenance, a SHA-256 hash, successful HTTP 200 capture, and successful parse status.
- Required page roles are present.
- For Village-style sources, every discovered detail ID has a matching parsed detail page, with no unexplained detail IDs.
- An empty result has an explicit `empty_snapshot_confirmed: true` assertion.

The resulting `snapshot` object is attached to the normalized document and can be passed to `scripts/track_event_identity.py`. A source policy that is disabled yields `unknown`, even if the manifest otherwise looks complete. Incomplete evidence yields `partial`.

## Safety rules

- A missing `rel="next"` link never establishes a terminal page.
- A failed, 304, or unparsed page blocks completeness.
- An undiscovered or unprocessed detail link blocks completeness.
- A zero-event parse is not proof of an empty publisher calendar.
- Completeness applies only to the exact scope written in the source policy, not every event the organization may publish elsewhere.
- No absence assertion cancels or deletes an event. It creates only a presence observation.
- The validator is offline. It does not fetch pages, follow links, enable polling, alter source policies, or publish events.

## Current implementation boundary

The Village parser can identify explicit `rel="next"` links and recognizes a terminal page only when the publisher's explicit `rel="last"` link points to the page currently being parsed. The manifest validator can then verify a fully enumerated page set. CivicCal does not yet automatically crawl those next-page links or fetch all detail URLs. Page capture remains a controlled, one-shot operation, but the capture command can now archive an explicitly allowlisted page URL from the same source profile. The next implementation step is a source-policy-driven page capture coordinator, after the actual pagination and allowed host/path patterns have been verified from saved publisher pages.
