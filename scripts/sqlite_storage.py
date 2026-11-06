"""Normalized SQLite persistence and strict import for CivicCal's legacy JSON state.

This module deliberately does not expose a whole-database JSON replacement API.
It imports existing records into relational tables while retaining original
payloads for lossless inspection and future adapter work.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE organizations (
    organization_id TEXT PRIMARY KEY,
    record_json TEXT NOT NULL
);
CREATE TABLE registry_metadata (
    singleton_id INTEGER PRIMARY KEY CHECK(singleton_id=1),
    metadata_json TEXT NOT NULL
);
CREATE TABLE sources (
    source_id TEXT PRIMARY KEY,
    organization_id TEXT,
    record_json TEXT NOT NULL,
    authorization_json TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(organization_id)
);
CREATE TABLE source_events (
    event_id TEXT PRIMARY KEY,
    identity_key TEXT NOT NULL UNIQUE,
    source_id TEXT NOT NULL,
    source_event_id TEXT,
    recurrence_instance_id TEXT,
    current_fingerprint TEXT,
    current_revision_number INTEGER NOT NULL,
    first_seen_at TEXT,
    last_seen_at TEXT,
    presence_status TEXT,
    missing_snapshot_count INTEGER NOT NULL,
    first_missing_at TEXT,
    last_missing_at TEXT,
    lifecycle_status TEXT,
    current_event_json TEXT NOT NULL,
    legacy_record_json TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES sources(source_id)
);
CREATE INDEX source_events_source_idx ON source_events(source_id);
CREATE TABLE event_observations (
    observation_id TEXT PRIMARY KEY,
    global_sequence INTEGER NOT NULL UNIQUE,
    event_id TEXT NOT NULL,
    event_sequence INTEGER NOT NULL,
    source_id TEXT NOT NULL,
    source_event_id TEXT,
    identity_key TEXT NOT NULL,
    capture_key TEXT NOT NULL,
    observed_at TEXT,
    material_fingerprint TEXT,
    event_json TEXT NOT NULL,
    UNIQUE(event_id, event_sequence),
    FOREIGN KEY(event_id) REFERENCES source_events(event_id),
    FOREIGN KEY(source_id) REFERENCES sources(source_id)
);
CREATE INDEX observations_source_capture_idx ON event_observations(source_id, capture_key);
CREATE TABLE event_revisions (
    event_id TEXT NOT NULL,
    revision_number INTEGER NOT NULL,
    observation_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL,
    observed_at TEXT,
    change_type TEXT,
    previous_fingerprint TEXT,
    values_json TEXT NOT NULL,
    record_json TEXT NOT NULL,
    PRIMARY KEY(event_id, revision_number),
    FOREIGN KEY(event_id) REFERENCES source_events(event_id),
    FOREIGN KEY(observation_id) REFERENCES event_observations(observation_id)
);
CREATE TABLE presence_observations (
    presence_observation_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    capture_key TEXT,
    observed_at TEXT,
    presence TEXT NOT NULL CHECK(presence IN ('present','missing')),
    presence_sequence INTEGER NOT NULL,
    record_json TEXT NOT NULL,
    FOREIGN KEY(event_id) REFERENCES source_events(event_id),
    FOREIGN KEY(source_id) REFERENCES sources(source_id)
);
CREATE TABLE lifecycle_transitions (
    event_id TEXT NOT NULL,
    lifecycle_sequence INTEGER NOT NULL,
    observation_id TEXT,
    record_json TEXT NOT NULL,
    PRIMARY KEY(event_id, lifecycle_sequence),
    FOREIGN KEY(event_id) REFERENCES source_events(event_id),
    FOREIGN KEY(observation_id) REFERENCES event_observations(observation_id)
);
CREATE TABLE unkeyed_observations (
    observation_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    capture_key TEXT,
    observed_at TEXT,
    record_json TEXT NOT NULL,
    FOREIGN KEY(source_id) REFERENCES sources(source_id)
);
CREATE TABLE processed_captures (
    processing_token TEXT PRIMARY KEY,
    source_id TEXT,
    capture_key TEXT,
    record_json TEXT NOT NULL
);
CREATE TABLE publication_approvals (
    event_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    approved INTEGER NOT NULL CHECK(approved IN (0,1)),
    imported_from TEXT NOT NULL,
    FOREIGN KEY(event_id) REFERENCES source_events(event_id),
    FOREIGN KEY(source_id) REFERENCES sources(source_id)
);
CREATE TABLE identity_conflicts (
    conflict_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    capture_key TEXT,
    record_json TEXT NOT NULL,
    FOREIGN KEY(source_id) REFERENCES sources(source_id)
);
CREATE TABLE migration_diagnostics (
    diagnostic_id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    record_json TEXT NOT NULL
);
"""

AUTH_FIELDS = (
    "access_status", "terms_reviewed", "robots_reviewed",
    "consent_required", "consent_granted", "polling_enabled",
)


class MigrationError(ValueError):
    """Input state is ambiguous, inconsistent, or unsafe to migrate."""


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _required_text(record: dict, key: str, context: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise MigrationError(f"{context}: {key} must be a non-empty string")
    return value


def _load_json(path: str | Path, label: str) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationError(f"Cannot read {label}: {exc}") from exc


def initialize_database(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA)
    connection.execute(
        "INSERT OR REPLACE INTO schema_meta(key,value) VALUES('schema_version',?)",
        (str(SCHEMA_VERSION),),
    )
    connection.commit()


def _validate_registry(registry: Any) -> tuple[dict[str, dict], dict[str, dict]]:
    if not isinstance(registry, dict):
        raise MigrationError("Source registry must be an object")
    orgs = registry.get("organizations")
    sources = registry.get("source_records")
    if not isinstance(orgs, list) or not isinstance(sources, list):
        raise MigrationError("Registry must contain organizations[] and source_records[]")
    organizations = {}
    for row in orgs:
        if not isinstance(row, dict):
            raise MigrationError("Invalid organization record")
        oid = _required_text(row, "id", "organization")
        if oid in organizations:
            raise MigrationError(f"Duplicate organization ID: {oid}")
        organizations[oid] = row
    source_map = {}
    for row in sources:
        if not isinstance(row, dict):
            raise MigrationError("Invalid source record")
        sid = _required_text(row, "id", "source")
        if sid in source_map:
            raise MigrationError(f"Duplicate source ID: {sid}")
        org_id = row.get("organization_id")
        if org_id is not None and org_id not in organizations:
            raise MigrationError(f"Source {sid} references unknown organization {org_id}")
        source_map[sid] = row
    return organizations, source_map


def import_json_documents(
    connection: sqlite3.Connection,
    registry: dict,
    identity_state: dict,
    publication_manifest: dict,
    input_labels: dict[str, str] | None = None,
) -> dict:
    """Import three explicit legacy documents atomically into an empty DB."""
    labels = input_labels or {}
    organizations, sources = _validate_registry(registry)
    if not isinstance(identity_state, dict) or identity_state.get("format") != "civiccal.identity-state.v1":
        raise MigrationError("Identity state must use civiccal.identity-state.v1")
    if not isinstance(identity_state.get("events"), dict):
        raise MigrationError("Identity state events must be an object")
    if not isinstance(publication_manifest, dict):
        raise MigrationError("Publication manifest must be an object")
    approved = publication_manifest.get("approved_event_ids")
    if not isinstance(approved, list) or any(not isinstance(x, str) or not x for x in approved):
        raise MigrationError("Publication manifest approved_event_ids must be strings")
    if len(set(approved)) != len(approved):
        raise MigrationError("Publication manifest contains duplicate event IDs")

    counts = {}
    try:
        initialize_database(connection)
        connection.execute("BEGIN IMMEDIATE")
        if connection.execute("SELECT COUNT(*) FROM source_events").fetchone()[0]:
            raise MigrationError("Target database already contains event data")
        for oid, row in organizations.items():
            connection.execute("INSERT INTO organizations VALUES(?,?)", (oid, _dump(row)))
        connection.execute("INSERT INTO registry_metadata VALUES(1,?)", (_dump(registry),))
        for sid, row in sources.items():
            auth = {field: row[field] for field in AUTH_FIELDS if field in row}
            connection.execute(
                "INSERT INTO sources VALUES(?,?,?,?)",
                (sid, row.get("organization_id"), _dump(row), _dump(auth)),
            )

        events_by_key = identity_state["events"]
        event_ids = {}
        for key, row in events_by_key.items():
            if not isinstance(row, dict):
                raise MigrationError(f"Event {key} must be an object")
            event_id = _required_text(row, "event_id", f"event {key}")
            identity_key = _required_text(row, "identity_key", f"event {event_id}")
            source_id = _required_text(row, "source_id", f"event {event_id}")
            if key != identity_key:
                raise MigrationError(f"Event key and identity_key differ for {event_id}")
            if source_id not in sources:
                raise MigrationError(f"Event {event_id} references unknown source {source_id}")
            if event_id in event_ids:
                raise MigrationError(f"Duplicate event ID {event_id}")
            current = row.get("current")
            if not isinstance(current, dict):
                raise MigrationError(f"Event {event_id} has no current event object")
            revisions = row.get("revisions", [])
            if not isinstance(revisions, list):
                raise MigrationError(f"Event {event_id} revisions must be an array")
            current_revision = row.get("current_revision_number", len(revisions))
            if not isinstance(current_revision, int) or current_revision < 0:
                raise MigrationError(f"Event {event_id} has invalid current revision number")
            if current_revision != len(revisions):
                raise MigrationError(f"Event {event_id} current revision number does not match revision history")
            connection.execute(
                """INSERT INTO source_events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (event_id, identity_key, source_id, row.get("source_event_id"),
                 row.get("recurrence_instance_id"), row.get("current_fingerprint"),
                 current_revision, row.get("first_seen_at"), row.get("last_seen_at"),
                 row.get("presence_status", "present"), row.get("missing_snapshot_count", 0),
                 row.get("first_missing_at"), row.get("last_missing_at"),
                 row.get("lifecycle_status"), _dump(current), _dump(row)),
            )
            event_ids[key] = (event_id, row, source_id)
        counts["organizations"] = len(organizations)
        counts["sources"] = len(sources)
        counts["events"] = len(event_ids)

        observation_map = {}
        observations = identity_state.get("observations", [])
        if not isinstance(observations, list):
            raise MigrationError("observations must be an array")
        by_id = {}
        for row in observations:
            if not isinstance(row, dict):
                raise MigrationError("Observation must be an object")
            oid = _required_text(row, "observation_id", "observation")
            if oid in by_id:
                raise MigrationError(f"Duplicate observation ID {oid}")
            by_id[oid] = row
        for identity_key, (event_id, event_row, source_id) in event_ids.items():
            refs = event_row.get("observation_ids", [])
            if not isinstance(refs, list):
                raise MigrationError(f"Event {event_id} observation_ids must be an array")
            for seq, oid in enumerate(refs, 1):
                obs = by_id.get(oid)
                if obs is None:
                    raise MigrationError(f"Event {event_id} references missing observation {oid}")
                if obs.get("identity_key") != identity_key or obs.get("source_id") != source_id:
                    raise MigrationError(f"Observation {oid} has conflicting event/source ownership")
                if oid in observation_map:
                    raise MigrationError(f"Observation {oid} is referenced more than once")
                observation_map[oid] = (event_id, seq)
        if set(by_id) != set(observation_map):
            orphaned = sorted(set(by_id) - set(observation_map))
            raise MigrationError(f"Unreferenced global observations: {orphaned[:5]}")
        for global_seq, (oid, obs) in enumerate(by_id.items(), 1):
            event_id, event_seq = observation_map[oid]
            connection.execute(
                "INSERT INTO event_observations VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (oid, global_seq, event_id, event_seq, obs["source_id"],
                 obs.get("source_event_id"), obs["identity_key"],
                 str(obs.get("capture_key", "")), obs.get("observed_at"),
                 obs.get("material_fingerprint"), _dump(obs.get("event", {}))),
            )
        counts["observations"] = len(by_id)

        revision_count = 0
        lifecycle_count = 0
        for identity_key, (event_id, event_row, _) in event_ids.items():
            revisions = event_row.get("revisions", [])
            for expected, rev in enumerate(revisions, 1):
                if not isinstance(rev, dict) or rev.get("revision") != expected:
                    raise MigrationError(f"Event {event_id} revision sequence is invalid")
                obs_id = rev.get("observation_id")
                if obs_id not in observation_map or observation_map[obs_id][0] != event_id:
                    raise MigrationError(f"Revision for {event_id} references an invalid observation")
                connection.execute(
                    "INSERT INTO event_revisions VALUES(?,?,?,?,?,?,?,?,?)",
                    (event_id, expected, obs_id, _required_text(rev, "fingerprint", event_id),
                     rev.get("observed_at"), rev.get("change_type"), rev.get("previous_fingerprint"),
                     _dump(rev.get("values", {})), _dump(rev)),
                )
                revision_count += 1
            lifecycle = event_row.get("lifecycle_history", [])
            if not isinstance(lifecycle, list):
                raise MigrationError(f"Event {event_id} lifecycle_history must be an array")
            for seq, item in enumerate(lifecycle, 1):
                obs_id = item.get("observation_id") if isinstance(item, dict) else None
                if obs_id is not None and (obs_id not in observation_map or observation_map[obs_id][0] != event_id):
                    raise MigrationError(f"Lifecycle record for {event_id} references invalid observation")
                connection.execute(
                    "INSERT INTO lifecycle_transitions VALUES(?,?,?,?)",
                    (event_id, seq, obs_id, _dump(item)),
                )
                lifecycle_count += 1
        counts["revisions"] = revision_count
        counts["lifecycle_transitions"] = lifecycle_count

        presence = identity_state.get("presence_observations", [])
        if not isinstance(presence, list):
            raise MigrationError("presence_observations must be an array")
        seen_presence = set()
        for seq, row in enumerate(presence, 1):
            if not isinstance(row, dict):
                raise MigrationError("Presence observation must be an object")
            source_id = row.get("source_id")
            identity_key = row.get("identity_key")
            event_info = event_ids.get(identity_key)
            event_id = event_info[0] if event_info else None
            if event_id is None:
                # Never guess identity from title/date or publisher ID.
                raise MigrationError("Presence observation has no resolvable identity_key")
            if source_id != event_info[2]:
                raise MigrationError("Presence observation source does not own its event")
            material = _dump(row)
            presence_id = row.get("presence_observation_id") or "pres_" + hashlib.sha256(
                f"{seq}:{material}".encode("utf-8")
            ).hexdigest()[:24]
            presence_value = row.get("presence")
            if presence_value not in {"present", "missing"}:
                raise MigrationError(f"Invalid presence value {presence_value!r}")
            connection.execute(
                "INSERT INTO presence_observations VALUES(?,?,?,?,?,?,?,?)",
                (presence_id, event_id, source_id, row.get("capture_key"),
                 row.get("observed_at"), presence_value, seq, material),
            )
        counts["presence_observations"] = len(presence)

        # Nested missing/reappearance history is a mirror of global presence
        # rows. Preserve unmatched nested items as diagnostics; do not double count.
        global_presence = [_dump(x) for x in presence]
        mirror_count = 0
        for identity_key, (event_id, event_row, _) in event_ids.items():
            history = event_row.get("missing_observation_history", [])
            if not isinstance(history, list):
                raise MigrationError(f"Event {event_id} missing_observation_history must be an array")
            for item in history:
                if _dump(item) not in global_presence:
                    diagnostic_id = "diag_" + hashlib.sha256(
                        f"{event_id}:{_dump(item)}".encode("utf-8")
                    ).hexdigest()[:24]
                    connection.execute(
                        "INSERT OR IGNORE INTO migration_diagnostics VALUES(?,?,?)",
                        (diagnostic_id, "unmatched_nested_presence_mirror",
                         _dump({"event_id": event_id, "identity_key": identity_key, "record": item})),
                    )
                    mirror_count += 1
        counts["unmatched_presence_mirrors"] = mirror_count

        unkeyed = identity_state.get("unkeyed_observations", [])
        if not isinstance(unkeyed, list):
            raise MigrationError("unkeyed_observations must be an array")
        for row in unkeyed:
            if not isinstance(row, dict):
                raise MigrationError("Unkeyed observation must be an object")
            source_id = _required_text(row, "source_id", "unkeyed observation")
            if source_id not in sources:
                raise MigrationError(f"Unkeyed observation references unknown source {source_id}")
            oid = _required_text(row, "observation_id", "unkeyed observation")
            connection.execute(
                "INSERT INTO unkeyed_observations VALUES(?,?,?,?,?)",
                (oid, source_id, row.get("capture_key"), row.get("observed_at"), _dump(row)),
            )
        counts["unkeyed_observations"] = len(unkeyed)

        tokens = identity_state.get("processed_captures", [])
        if not isinstance(tokens, list) or any(not isinstance(x, str) or not x for x in tokens):
            raise MigrationError("processed_captures must be an array of non-empty tokens")
        for token in tokens:
            connection.execute(
                "INSERT INTO processed_captures VALUES(?,?,?,?)",
                (token, None, None, _dump({"legacy_token": token})),
            )
        counts["processed_captures"] = len(tokens)

        for event_id in approved:
            row = next((e for e in event_ids.values() if e[0] == event_id), None)
            if row is None:
                raise MigrationError(f"Approved event {event_id} is missing from identity state")
            connection.execute(
                "INSERT INTO publication_approvals VALUES(?,?,1,?)",
                (event_id, row[2], labels.get("manifest", "publication manifest")),
            )
        counts["publication_approvals"] = len(approved)
        counts["migration_diagnostics"] = mirror_count
        connection.commit()
        return counts
    except Exception:
        connection.rollback()
        raise


def migrate_files(database_path: str | Path, registry_path: str | Path,
                  state_path: str | Path, manifest_path: str | Path) -> dict:
    db_path = Path(database_path)
    if db_path.exists():
        raise MigrationError("Refusing to overwrite an existing database file; choose a new path")
    registry = _load_json(registry_path, "source registry")
    state = _load_json(state_path, "identity state")
    manifest = _load_json(manifest_path, "publication manifest")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        result = import_json_documents(
            connection, registry, state, manifest,
            {"registry": str(registry_path), "state": str(state_path),
             "manifest": str(manifest_path)},
        )
    except Exception:
        connection.close()
        # A failed first migration must not leave a half-initialized target
        # that would block a clean retry. Existing non-empty DBs were refused.
        db_path.unlink(missing_ok=True)
        raise
    connection.close()
    return result
