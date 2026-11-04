# Source health report

**Status:** implemented as an offline, read-only diagnostic. It does not contact source websites or change source policy.

Run:

```sh
python scripts/report_source_health.py
```

Optional paths:

```sh
python scripts/report_source_health.py \
  --registry data/sources.json \
  --archive-dir data/captures \
  --output reports/source-health.json
```

The report summarizes each registered source's current policy state, whether polling is enabled, consent flags, capture count, and most recent capture metadata. It scans only the source's own archive directory.

For each archived `captured` payload, the report verifies that the referenced file exists and its SHA-256 matches the capture metadata. It also flags unreadable metadata, mismatched source IDs, unsupported metadata formats, unsafe payload references, and unexpected payload references on `not_modified` captures.

Policy states are descriptive, not permissions:
- `consent_required`: a consent-required source does not have the explicit `consent_granted=true` switch.
- The source's configured `access_status` (for example, `review_required` or `blocked`) when not approved.
- `review_incomplete`: access is marked approved but terms or robots review is incomplete.
- `approved`: source policy fields are marked approved and reviewed.

The report does not decide whether a source is legally or operationally safe to capture. The capture command independently enforces the registry's access, terms, robots, and consent gates.

Exit codes: `0` means no archive-integrity warnings, `1` means one or more warnings were found, and `2` means the registry/report could not be processed. A source with no capture history is reported as having no captures; this is not treated as a source failure.