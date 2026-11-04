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
- The manifest has the expected format and contains no duplicate or invalid IDs.

Unknown sources, unknown events, ambiguous identities, source mismatches, and malformed manifests are rejected without writing. Approve and revoke are idempotent. Writes use a temporary file and atomic replacement; the command changes only the manifest.

This is a manual publication decision, not an automated quality judgment. The operator must review the source record and its details before approving. The command does not infer approval from source permissions, title, organizer, parser confidence, or capture status.

## Strict separation of controls

- Source access, terms, robots, and written-consent flags govern whether capture is permitted.
- `polling_enabled` governs future polling configuration; it does not trigger work in the MVP.
- The publication manifest governs which already-stored event IDs are exposed through API and ICS.
- Approving an event does not activate a source, authorize a capture, change polling, or publish/deploy the service.
- Revoking an event removes it from subsequent API/ICS responses but leaves the stored record and revision history intact.

The current manifest is a file-backed MVP control. Concurrent edits are not coordinated; use one operator at a time until the database-backed approval store is implemented.
