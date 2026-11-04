# Storage Interface (Database Deferred)

## Decision

CivicCal will remain database-independent until the project is reviewed on the user laptop. No SQLite or PostgreSQL schema, installation, migration, or deployment is part of this milestone.

The code now has a small replaceable persistence boundary for identity state. The current implementation is a local JSON file. A later backend can implement the same interface without changing event parsing, normalization, or identity rules.

## Contract

scripts/storage.py defines IdentityStateStore:
- load_identity_state() returns the previous state object, or None when no state exists.
- save_identity_state(state) persists a complete replacement state.

The contract intentionally exposes CivicCal state, not SQL queries, table names, transactions, or vendor-specific features. Keep domain decisions in the processing layer and persistence mechanics in the backend.

## Current backend: JSON

JsonFileIdentityStateStore:
- Reads and writes UTF-8 JSON.
- Creates parent directories when saving.
- Uses a temporary file and atomic replacement to avoid leaving a partially written state file.
- Preserves Unicode and produces readable, consistently formatted JSON.
- Does not provide multi-process locking or concurrent-writer coordination. Run one identity-state writer at a time.

Example:

```python
from scripts.storage import JsonFileIdentityStateStore

store = JsonFileIdentityStateStore("data/identity/state.json")
state = store.load_identity_state()
# Pass state to process_normalized(...)
# After successful processing:
store.save_identity_state(updated_state)
```

The command-line identity tracker uses this adapter by default. Its existing --state and --state-output options remain unchanged.

## Future backend requirements

A replacement backend must preserve these behaviors:
1. Return the same logical state contract.
2. Preserve source-scoped event identity and append-only revisions.
3. Make processing of the same capture idempotent.
4. Preserve observations, unkeyed records, and identity conflicts.
5. Never infer cancellation/deletion from an event missing in a capture.
6. Avoid cross-source merges.
7. Make writes durable and define concurrency/transaction behavior.
8. Support export/import or a documented migration path.

Possible future implementations include SQLite, PostgreSQL, or another local/self-hosted store. The choice is deliberately open until reviewed on the target laptop and server hardware.

## Current limits

This is an interface boundary, not a full persistence layer for the entire ingestion pipeline. Raw capture files and parser/normalization outputs continue to use their existing file-based formats. No database has been installed, initialized, or deployed.
