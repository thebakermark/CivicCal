# Manual event publication approval

## Purpose

An event is publishable only when its ID is explicitly present in the publication manifest. This is a separate, deliberate operator decision; ingestion, source registration, and successful parsing never approve an event automatically.

Use `scripts/set_publication.py` to approve or revoke one stored event without editing JSON by hand.

## Approve one event

```sh
python scripts/set_publication.py \
  --registry data/sources.json \
  --identity-state data/state/identity.json \
  --manifest data/publication/source.json \
  --source-id village-of-mokena-events \
  --event-id evt_0123456789abcdef01234567 \
  --action approve
```

## Revoke one event

Use the same command with `--action revoke`. Revocation removes only that event ID from the manifest. It does not delete the event, alter its history, or change any other source's events.

## Safety behavior

Before changing the manifest, the command verifies:

- The source ID exists exactly once in the source registry.
- The event ID exists exactly once in identity state.
- The event's stored `source_id` exactly matches the requested source ID.
- Identity records have unique event IDs and non-empty source ownership.
- The manifest has the expected format, contains no duplicate IDs, and every existing approval still resolves to a stored event whose source remains registered exactly once.

Unknown sources, unknown events, ambiguous identities, source mismatches, and malformed manifests are rejected without writing. Approve and revoke are idempotent. Writes use a temporary file and atomic replacement; the command changes only the manifest.

This is a manual publication decision, not an automated quality judgment. The operator must review the source record and its details before approving. The command does not infer approval from source permissions, title, organizer, parser confidence, or capture status.

## Where source approval flags live

Edit the source record in `data/sources.json`, inside the top-level `source_records` array. Find the exact record by its `id`; do not edit an organization entry in the separate `organizations` array when changing source permissions.

| Field | Meaning | Required state for capture |
|---|---|---|
| `access_status` | General source-access decision | `approved` |
| `terms_reviewed` | Applicable terms have been reviewed | `true` |
| `robots_reviewed` | Applicable robots rules have been reviewed | `true` |
| `consent_required` | Source requires additional written consent | `true` when applicable |
| `consent_granted` | Required written consent has actually been received | `true` when `consent_required` is true |
| `polling_enabled` | Operator's future polling configuration | Remains `false` unless separately and deliberately enabled |

For example, the Mokena School District 159 record is `mokena-sd159-events-ical` in `data/sources.json`. Its current `access_status` is `blocked`, `consent_required` is `true`, `consent_granted` is `false`, and `polling_enabled` is `false`. Do not change those values unless the required written consent and separate review decisions have actually been completed. The source-capture gate is implemented in `scripts/capture_source.py` (`load_source`).

These are source-level capture controls. They are separate from the event-level publication manifest described below.

## Strict separation of controls

- Source access, terms, robots, and written-consent flags govern whether capture is permitted.
- `polling_enabled` governs future polling configuration; it does not trigger work in the MVP.
- The publication manifest governs which already-stored event IDs are exposed through API and ICS.
- Approving an event does not activate a source, authorize a capture, change polling, or publish/deploy the service.
- Revoking an event removes it from subsequent API/ICS responses but leaves the stored record and revision history intact.

The current manifest is a file-backed MVP control. Concurrent edits are not coordinated; use one operator at a time until the database-backed approval store is implemented.
