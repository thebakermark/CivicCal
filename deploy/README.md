# CivicCal deployment assets

These files prepare a private, single-instance systemd deployment on a Debian 13 Proxmox guest. The recommended guest is an unprivileged LXC.

## Included

- `systemd/civiccal-api.service`: read-only HTTP service unit, loopback-bound.
- `civiccal.env.example`: runtime path and port configuration template.

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

1. Provision the Debian guest and create the dedicated `civiccal` system account.
2. Check out a reviewed CivicCal commit under `/opt/civiccal/app`.
3. Create the persistent data directories and install the source registry as an operator-managed file.
4. Create and validate the initial identity-state and publication-manifest files using the current schemas. Do not invent empty shapes or copy test-only fixtures into production.
5. Copy `civiccal.env.example` to `/etc/civiccal/civiccal.env`; restrict it to root and the service group as appropriate.
6. Install `systemd/civiccal-api.service` as `/etc/systemd/system/civiccal-api.service`.
7. Before enabling it, inspect the unit, verify file ownership/permissions, and run the documented API tests against the exact runtime data.
8. Start the service only after explicit deployment approval; confirm `http://127.0.0.1:8765/health` from inside the guest.

No provisioning or install script is supplied yet because the target Proxmox node, storage, bridge, guest ID, and data initialization method have not been reviewed.

## Security posture

- The API binds to `127.0.0.1` only.
- The service runs as an unprivileged dedicated account.
- systemd hardening prevents writes to the application and data filesystem.
- No reverse proxy, public bind, tunnel, port forwarding, TLS termination, scheduled capture, or polling is configured.
- The source registry's access/consent/review flags remain human-controlled.
- Publication approval remains a separate operator action.
