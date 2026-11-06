# CivicCal SQLite server

This deployment target is a private, single-instance Debian 13 LXC. The API
reads the normalized SQLite database and exposes only read-only event JSON and
source-specific ICS feeds. It binds to 127.0.0.1.

## Current implementation

- `scripts/migrate_json_to_sqlite.py` imports explicitly selected registry,
  identity-state, and publication-manifest files into a new SQLite database.
- `scripts/serve_sqlite_api.py` serves the database-backed read-only API.
- `/health` reports the selected storage backend.
- `/api/v1/events` queries approved events from SQLite.
- `/calendars/sources/{source_id}.ics` renders only approved events belonging
  to that source.
- No capture, polling, scheduler, approval mutation, or public bind is included.

## Intended layout

- Application: `/opt/civiccal/app`
- Service configuration: `/etc/civiccal/civiccal-sqlite.env`
- Persistent database: `/srv/civiccal/data/civiccal.sqlite`
- Service account: `civiccal:civiccal`

The service account receives read-only access to the database. It cannot change
source authorization, event records, or publication approvals.

## Offline migration

Run the importer as an operator, not as the API service account:

```sh
python3 scripts/migrate_json_to_sqlite.py \
  --database /srv/civiccal/data/civiccal.sqlite \
  --registry /srv/civiccal/data/registry/sources.json \
  --state /srv/civiccal/data/state/identity.json \
  --manifest /srv/civiccal/data/publication/source.json
```

The target database must be new. The importer does not fetch sources or publish
anything. It preserves existing event IDs, identity keys, observations,
revisions, source authorization flags, and the current publication approval
set. If validation fails, no migrated records are committed.

Before using real household data, make a verified backup of all three input
documents and their capture archives. The database migration does not copy raw
capture payloads; those remain in their existing archive location.

## Manual service preparation

1. Create the dedicated `civiccal` system account.
2. Install the reviewed application checkout under `/opt/civiccal/app`.
3. Create the database using the explicit migration command above.
4. Copy `civiccal-sqlite.env.example` to
   `/etc/civiccal/civiccal-sqlite.env` and set root ownership and restrictive
   permissions.
5. Install `systemd/civiccal-sqlite-api.service` as
   `/etc/systemd/system/civiccal-sqlite-api.service`.
6. Grant the service account read access to the database and its parent
   directories, but no write access.
7. Review the exact unit, database, file permissions, and API tests.
8. Enable or start the service only after explicit deployment approval.

No Proxmox container is provisioned by this repository change. Container ID,
storage allocation, backup schedule, host firewall, and any LAN/remote access
remain separate operator decisions.
