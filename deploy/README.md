# CivicCal deployment assets

These files prepare a private, single-instance systemd deployment in an unprivileged Debian 13 Proxmox LXC.

## Included

- `systemd/civiccal-api.service`: read-only HTTP service unit, loopback-bound.
- `systemd/civiccal-capture@.service`: manually invoked, hardened one-shot capture job.
- `civiccal.env.example`: runtime path and port configuration template.

## Capture runner

See [the one-shot capture runner guide](../docs/capture-runner.md) for the execution contract, security boundary, installation commands, validation steps, and rollback.

The capture job is not enabled and has no timer. It reads the registry and policy, writes only to the raw capture and report directories, and reuses the existing ICS coordinator. It does not publish or change authorization flags.

## API deployment

The current application reads JSON identity state and a publication manifest. The repository does not include production runtime state or a publication manifest, and the database adapter is not implemented. Do not start the API until the operator has provisioned valid runtime files from the documented data contracts and verified their contents.

The API service unit does not create data, approve events, change source authorization, capture sources, or enable polling.

## Intended installation layout

- Application checkout: `/opt/civiccal/app`
- Runtime configuration: `/etc/civiccal/civiccal.env`
- Persistent data: `/srv/civiccal/data/`
- API service account: `civiccal:civiccal`
- Capture service account: `civiccal-capture:civiccal-capture`

Keep the application checkout and configuration root-owned and not writable by either service account. The API process is read-only. The capture process may write only to its capture and report directories.

No provisioning or install script is supplied because current storage capacity, container ID, mount-point allocation, and data initialization method have not been reviewed.
