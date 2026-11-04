# Storage Interface (Database Deferred)

## Decision

CivicCal remains database-independent in runtime code until implementation is explicitly approved. A logical database schema and migration design are now documented, but no SQL schema, database dependency, database file, migration script, or deployment has been created.

The current implementation has a small replaceable persistence boundary for identity state. The current backend is a local JSON file. A later backend must preserve the domain behavior without making parsing, normalization, identity, or publication logic depend on a specific database engine.

See [Database Schema and JSON Migration Design](database-schema-and-migration.md) for the proposed logical entities, relationships, transaction boundaries, migration sequence, and cutover tests.

## Current contract

`scripts/storage.py` defines `IdentityStateStore`:

- `load_identity_state()` returns the previous state object, or `None` when no state exists.
- `save_identity_state(state)` persists a complete replacement state.

The contract intentionally exposes CivicCal state, not SQL queries, table names, or vendor-specific features. Keep domain decisions in the processing layer and persistence mechanics in the backend.

This is currently a narrow identity-state boundary, not yet a complete repository interface for organizations, sources, captures, event observations, revisions, or publication approvals. The database implementation phase will need to introduce those domain operations deliberately. Do not force all database entities into this two-method interface, and do not leak SQL into pipeline code.

## Current backend: JSON

`JsonFileIdentityStateStore`:

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

The command-line identity tracker uses this adapter by default. Its existing `--state` and `--state-output` options remain unchanged.

## Future backend requirements

A replacement backend must preserve these behaviors:

1. Preserve source-scoped event identity and stable event IDs.
2. Preserve append-only revisions and every source observation, including unchanged observations.
3. Make processing of the same capture idempotent.
4. Preserve unkeyed observations, identity conflicts, and presence history.
5. Never infer cancellation/deletion from an event missing in a capture.
6. Avoid cross-source merges.
7. Preserve original source data, provenance, and temporal semantics.
8. Make writes durable and define transaction/concurrency behavior.
9. Keep publication approval separate, explicit, and source-scoped.
10. Support export/import, backup/restore, and a documented rollback path.

SQLite is the likely first embedded/local implementation; PostgreSQL remains a possible later backend. The final engine and versions are intentionally deferred until implementation is reviewed against the target laptop/server environment.

## Current limits

This interface is not a full persistence layer for the entire ingestion pipeline. Raw capture files and parser/normalization outputs continue to use their existing file-based formats. No database has been installed, initialized, or deployed.