# CivicCal deployment assets

These files prepare a private, single-instance systemd deployment in an unprivileged Debian 13 Proxmox LXC.

## Included

- `systemd/civiccal-api.service`: read-only HTTP service unit, loopback-bound.
- `civiccal.env.example`: runtime path and port configuration template.

## Operator-invoked iCalendar capture

The capture coordinator already exists at `scripts/capture_ics_source.py`; this deployment adds a dedicated, manually started systemd one-shot unit. It is **not** an HTTP microservice, daemon, timer, cron job, or polling worker. The unit has no `[Install]` section and is never enabled at boot.

Install the capture account and writable directories:

```sh
sudo useradd --system --home /nonexistent --shell /usr/sbin/nologin civiccal-capture
sudo install -d -o root -g civiccal-capture -m 0750 /srv/civiccal/data/registry
sudo install -d -o civiccal-capture -g civiccal-capture -m 0750 /srv/civiccal/data/captures /srv/civiccal/data/reports
sudo install -o root -g civiccal-capture -m 0640 /opt/civiccal/app/data/sources.json /srv/civiccal/data/registry/sources.json
sudo install -o root -g root -m 0644 /opt/civiccal/app/deploy/systemd/civiccal-capture@.service /etc/systemd/system/civiccal-capture@.service
sudo systemctl daemon-reload
sudo systemd-analyze verify /etc/systemd/system/civiccal-capture@.service
```

Before the first live request, inspect the exact source record in the installed registry. The capture code enforces the structured `access_status`, `terms_reviewed`, `robots_reviewed`, and consent fields. It never changes them. The current SD159 registry entry has structured `consent_required=true` and `consent_granted=true`, while its free-text notes still say consent remains false. Resolve that stale-note contradiction with the source owner/operator before capture; do not change either flag as part of deployment. The SD159 completeness profile deliberately keeps `allow_complete_snapshot=false` until the fresh feed is compared with the visible district calendar.

Start exactly one capture manually (replace the source ID only with another registered ICS source):

```sh
sudo systemctl start civiccal-capture@mokena-sd159-events-ical.service
sudo systemctl status civiccal-capture@mokena-sd159-events-ical.service --no-pager
sudo journalctl -u civiccal-capture@mokena-sd159-events-ical.service -n 80 --no-pager
```

On success, inspect:

- Raw payload and metadata: `/srv/civiccal/data/captures/mokena-sd159-events-ical/`
- Parsed/normalized report: `/srv/civiccal/data/reports/mokena-sd159-events-ical/latest.json`

The service account can write only under the capture and report directories. It reads the registry and completeness policy but cannot edit them. The API service account remains separate and read-only. A failed request leaves the previous report untouched unless the coordinator itself completed a new capture; inspect the journal and metadata before retrying.

Do not use `systemctl enable`, create a timer, or configure cron. Every capture is a deliberate one-shot operator action. The service does not ingest into identity state or publish events.

## Important current-state limitation

The current application reads JSON identity state and a publication manifest. The repository does not include production runtime state or a publication manifest, and the database adapter is not implemented. Do not start the service until the operator has provisioned valid runtime files from the documented data contracts and verified their contents.

The service unit does not create data, approve events, change source authorization, capture sources, or enable polling.

## Intended installation layout

- Application checkout: `/opt/civiccal/app`
- Runtime configuration: `/etc/civiccal/civiccal.env`
- Persistent data: `/srv/civiccal/data/`
- Service account: `civiccal:civiccal`

The application checkout and configuration should be owned by root and not writable by the service account. Persistent runtime files should be readable by the service account but should not be writable by the API process. Operator-invoked ingestion will need a separate, deliberately scoped write path; do not grant the API service write access as a shortcut.

## Manual preparation outline

1. Provision the unprivileged Debian 13 LXC and create the dedicated `civiccal` system account.
2. Check out a reviewed CivicCal commit under `/opt/civiccal/app`.
3. Create the persistent data directories and install the source registry as an operator-managed file.
4. Create and validate the initial identity-state and publication-manifest files using the current schemas. Do not invent empty shapes or copy test-only fixtures into production.
5. Copy `civiccal.env.example` to `/etc/civiccal/civiccal.env`; restrict it to root and the service group as appropriate.
6. Install `systemd/civiccal-api.service` as `/etc/systemd/system/civiccal-api.service`.
7. Before enabling it, inspect the unit, verify file ownership/permissions, and run the documented API tests against the exact runtime data.
8. Start the service only after explicit deployment approval; confirm `http://127.0.0.1:8765/health` from inside the guest.

No provisioning or install script is supplied yet because current storage capacity, container ID, mount-point allocation, and data initialization method have not been reviewed.

## Security posture

- The API binds to `127.0.0.1` only.
- The service runs as an unprivileged dedicated account.
- systemd hardening prevents writes to the application and data filesystem.
- No reverse proxy, public bind, tunnel, port forwarding, TLS termination, scheduled capture, or polling is configured.
- The source registry's access/consent/review flags remain human-controlled.
- Publication approval remains a separate operator action.
