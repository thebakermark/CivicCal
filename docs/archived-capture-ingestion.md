# Archived Capture Ingestion

## Purpose

`scripts/ingest_capture.py` is the first single-command bridge from an archived source response to CivicCal's persistent identity state. It joins the existing parser, normalization, identity/revision, and storage layers.

It operates only on an existing capture. It does not contact the source, change source permissions, approve events, or publish feeds.

## Run

After a source has been captured through the permitted one-shot capture process:

```sh
python scripts/ingest_capture.py \
  --source-id village-of-mokena-events \
  --capture-metadata data/captures/village-of-mokena-events/capture-<timestamp>-<hash>.json \
  --adapter village \
  --state data/identity/state.json
```

The capture metadata must refer to an archived payload whose SHA-256 matches the recorded digest. The source ID must match both the capture and exactly one source registry entry. The selected adapter must match the registered source type.

## Pipeline

1. Resolve the source in `data/sources.json`.
2. Read capture metadata and verify the archived payload hash.
3. Select the explicit or automatic parser.
4. Parse the archived payload offline.
5. Normalize event fields while preserving the original parser record and capture provenance.
6. Track source-scoped event identity, observations, and revisions.
7. Atomically save the updated identity state through the current JSON storage adapter.
8. Emit a report with parsed/normalized counts, review flags, new events, revisions, unchanged events, and unresolved identities.

The same capture is idempotent: processing it again does not create duplicate events or revisions.

## Publication boundary

Ingestion is deliberately separate from publication. The command does not add event IDs to the approval manifest. The JSON API and ICS publisher continue to expose only explicitly approved event IDs.

## Current storage and limitations

The command currently persists the identity state to the replaceable JSON-file backend. It is not the final database implementation. The database choice and migration remain deferred for review on the user's laptop.

- No network access during ingestion.
- No automatic polling or scheduling.
- No approval or publication.
- No cross-source event merging.
- Events without stable publisher IDs are retained as unkeyed observations for review.
- A missing event is not automatically cancelled or deleted.
- This command ingests one archived capture at a time; source discovery and permitted capture remain separate steps.
