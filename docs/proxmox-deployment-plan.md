# Proxmox Deployment Plan

**Status:** proposed deployment target; documentation only. No guest creation, package installation, database initialization, network exposure, or deployment is authorized by this plan.

## 1. Recommendation

Deploy CivicCal as one application in a dedicated **Ubuntu Server 26.04 LTS VM** on Proxmox.

This follows the user's previously selected Ubuntu Server VM approach. Use the guest's native systemd service manager and Python runtime. Do not introduce Docker, Kubernetes, PostgreSQL, Redis, a task queue, or a reverse proxy merely to run the current single-process application.

This keeps the deployment small, inspectable, easy to back up, and consistent with CivicCal's modular-monolith architecture. Keep the application independent of Proxmox-specific features so it can be moved to another VM or host later.

## 2. Initial guest sizing (provisional)

| Resource | Initial proposal | Notes |
|---|---:|---|
| Guest | Ubuntu Server 26.04 LTS VM | Matches the previously selected VM-based Proxmox approach |
| CPU | 2 vCPU | Parsing and one-shot capture are modest workloads |
| Memory | 4 GiB | Comfortable headroom for Ubuntu Server and the application |
| OS disk | 32 GiB | Operating system, Python runtime, application checkout |
| Data volume | Separate virtual disk if storage permits; begin at 32 GiB | Raw captures and state live outside the application checkout; size can be increased |
| Network | `vmbr0`, DHCP initially | Preserve the existing network; no router or DHCP changes during initial testing; no inbound public access |

These are starting estimates, not hard requirements. Previously recorded Proxmox details include node `pve0`, bridge `vmbr0`, and `local-lvm`; storage capacity can change, so verify current availability with `pvesm status` before allocating disks. Keep the first network test on DHCP and do not change router/DHCP settings until the guest has been tested successfully.

## 3. Application layout

Keep application code separate from persistent data:

```text
/opt/civiccal/app/          # Git checkout; replaceable application code
/etc/civiccal/              # Runtime configuration; restricted permissions
/srv/civiccal/data/
  registry/                 # Source registry snapshot/configuration
  state/                    # Current JSON state and publication manifest
  captures/                 # Immutable raw capture payloads and metadata
  reports/                  # Ingestion and validation reports
  backups/                  # Local staging only; off-guest backup is separate
```

Do not put mutable state or raw captures inside the Git checkout. Do not commit private runtime data, capture archives, secrets, or local database files to GitHub.

The source registry remains human-controlled. The application may read and enforce authorization flags; it must never change access, consent, terms/robots review, or polling flags.

## 4. Runtime services

### Initial service

One systemd-managed read-only HTTP process:

- Entrypoint: `scripts/serve_api.py`
- Initial storage: existing JSON identity state and publication manifest
- Bind address: `127.0.0.1` inside the guest
- Port: `8765`
- Routes: `/health`, `/api/v1/events`, `/api/v1/openapi.json`, and source-specific `/calendars/sources/{source_id}.ics`
- Restart policy: restart on process failure
- Run as a dedicated unprivileged `civiccal` service account
- Service process receives read-only access to application data

The current API deliberately refuses non-loopback bind addresses. Do not bypass that restriction as a shortcut to remote access.

### Operator-invoked ingestion

Capture and ingestion remain explicit, one-shot operator actions. They are not a daemon, timer, cron job, or background worker. Capture is allowed only after the existing source authorization gates pass. Ingestion remains separate from publication approval.

A future operator command may run under a separate restricted execution context with write access to the capture/state directories. The HTTP service must not receive those write permissions.

## 5. Persistence decision

**Proposed first database: SQLite.** It is a good fit for one personal CivicCal instance, one application process, local storage, and a modest write rate. Keep the existing storage/domain boundaries so PostgreSQL can be added later if a real concurrency or multi-instance need appears.

However, the database is not implemented yet. The current JSON backend and migration design remain authoritative until the database adapter, migration reconciliation, parity tests, rollback, and backup/restore are implemented and reviewed.

Do not initialize a production database or migrate the current JSON state as part of guest provisioning. Database implementation is a separate approval gate.

Raw capture payloads initially remain in the filesystem archive. The database should store verified hashes and archive references, not require large binary payloads in the first migration.

## 6. Network and calendar access

Separate application hosting from remote subscription exposure.

**Phase 1 — private local validation**
- API remains loopback-only inside the guest.
- No public DNS, port forwarding, tunnel, inbound firewall opening, or reverse proxy.
- Validate health, API, source isolation, and generated ICS locally from an approved test dataset.

**Phase 2 — user-approved access design**
- Decide whether access is LAN-only, VPN-only, or reachable by external calendar subscription services.
- A subscription URL used by an external calendar provider must be reachable by that provider; a private LAN address or personal VPN alone may not satisfy that requirement.
- If remote access is approved, put TLS and access controls at a separately reviewed edge/reverse-proxy layer. Keep the application process private behind it.
- Do not assume that an unguessable URL is authentication.
- Do not expose administrative or ingestion operations through the read-only API.

No public endpoint or external calendar subscription test is authorized by this plan.

## 7. Backups and recovery

Before treating the deployment as dependable:

1. Back up the guest configuration and application version.
2. Back up the persistent data volume, including raw captures, metadata, registry, state, and publication manifest.
3. When SQLite is implemented, use a database-consistent backup method; do not rely on copying a live database file blindly.
4. Keep at least one backup outside the Proxmox guest and preferably outside the Proxmox host.
5. Document restore order and verify a restore into a separate test guest or directory.
6. Verify restored hashes, source authorization flags, approved-event manifest, and source-specific feed isolation.

A Proxmox snapshot alone is not the complete backup strategy.

## 8. Deployment sequence

| Stage | Work | Gate |
|---|---|---|
| 0 | Review this plan against the actual Proxmox node, storage, bridge, and backup destination | User review |
| 1 | Prepare a reproducible guest provisioning checklist and systemd unit | Documentation/config review |
| 2 | Create the Ubuntu Server VM and install only the required OS/Python packages | Explicit deployment approval |
| 3 | Deploy current JSON-backed application in private validation mode | Explicit deployment approval |
| 4 | Implement SQLite adapter, migration, parity checks, and rollback | Separate database approval |
| 5 | Switch API and ICS to database-backed approved records | Migration acceptance |
| 6 | Implement and test backup/restore | Recovery acceptance |
| 7 | Decide and implement LAN/VPN/public subscription access | Separate network-exposure approval |
| 8 | Test a real calendar-client subscription and subsequent approved update | End-to-end acceptance |

## 9. Explicit non-goals

This deployment does not add:
- Scheduled polling, cron, systemd timers, or unattended capture.
- Webhook delivery or task queues.
- Public directory, user accounts, or administration portal.
- Combined or cross-source feeds.
- Email ingestion.
- Automatic source authorization or publication approval.
- Public network exposure by default.

## 10. Pre-provisioning checklist

Before creating the guest, confirm:
- Target Proxmox node and available storage.
- Preferred network bridge and reserved address.
- The VM ID, current storage availability, and final virtual-disk sizing.
- Persistent data-volume location and capacity.
- Existing Proxmox backup target and retention.
- Whether the first validation is LAN-only or strictly guest-local.

Until those are confirmed and the relevant approval gates are met, this document is a deployment design—not an instruction to provision or expose services.
