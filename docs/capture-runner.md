# CivicCal one-shot capture runner

**Status:** implementation proposal on a feature branch. The runner is not deployed or executed against a live source by this change.

## Decision

Use a systemd **oneshot job**, not a continuously running microservice. CivicCal's architecture explicitly keeps capture operator-invoked and avoids schedulers, daemons, queues, and polling in the MVP. A resident HTTP service would add attack surface without improving this task.

The runner reuses `scripts/capture_ics_source.py` and the existing RFC 5545 parser, normalizer, source authorization checks, redirect allowlist, raw archive, and completeness validator. It adds an isolated execution boundary and a durable per-run JSON report.

## Files

- `scripts/run_capture_job.py`: validates the source ID, loads the source through existing authorization gates, runs one capture, and writes an atomic report.
- `deploy/systemd/civiccal-capture@.service`: hardened systemd template unit.
- `tests/test_run_capture_job.py`: unit tests for ID validation, report output, and read-only registry behavior.

No HTTP listener, API endpoint, timer, cron entry, or persistent worker is introduced.

## Execution contract

A run:

1. Accepts exactly one registered source ID.
2. Reads the source registry and completeness policy.
3. Requires existing access, terms, robots, and consent gates to pass.
4. Requires an ICS source and exactly one `single_feed` policy profile.
5. Makes one HTTPS request through the existing allowlisted redirect handler.
6. Archives raw response bytes and metadata using the existing content-addressed archive.
7. Validates the VCALENDAR envelope, parses, normalizes, and checks snapshot completeness.
8. Writes one JSON report under the reports directory.
9. Exits non-zero on any capture, policy, parsing, or write failure.

The runner never edits source registry or completeness policy. It never enables polling, changes approvals, marks events approved, merges events, or publishes events. An incomplete/unknown snapshot remains incomplete/unknown.

## Runtime layout

- Checkout: `/opt/civiccal/app`
- Python environment: `/opt/civiccal/venv`
- Registry: `/srv/civiccal/data/registry/sources.json`
- Raw captures: `/srv/civiccal/data/captures/`
- Reports: `/srv/civiccal/data/reports/`
- Service account: `civiccal-capture`

The completeness policy is read from the reviewed application checkout at `data/source-completeness.json`. Keep it versioned and read-only.

## Proxmox deployment

This change does not provision a guest, install packages, alter Proxmox, or open network ports. After the feature branch is reviewed and merged, deployment requires the separately authorized Proxmox step.

Suggested initial target is the existing planned unprivileged Debian 13 LXC, not a new microservice VM. Confirm the current guest ID and storage before any provisioning; do not assume the earlier proposed CT sizing/storage remains available.

### 1. Prepare the runtime

From the LXC console as an administrator, after deployment approval:

```sh
apt-get update
apt-get install --yes python3
useradd --system --home /nonexistent --shell /usr/sbin/nologin civiccal-capture
install -d -o root -g civiccal-capture -m 0750 /srv/civiccal/data/registry
install -d -o civiccal-capture -g civiccal-capture -m 0750 /srv/civiccal/data/captures
install -d -o civiccal-capture -g civiccal-capture -m 0750 /srv/civiccal/data/reports
```

Install a reviewed checkout at `/opt/civiccal/app`, owned by root and not writable by the capture account. Copy the human-reviewed source registry to `/srv/civiccal/data/registry/sources.json`, owned by root and readable by the capture group. Do not create or alter approval flags during this copy.

### 2. Verify Python import and tests

The current project uses the Python standard library for this capture path. From the checkout:

```sh
python3 -m unittest tests.test_capture_ics_source tests.test_run_capture_job
```

Create the runtime interpreter path expected by the unit:

```sh
python3 -m venv /opt/civiccal/venv
```

No third-party package installation is required for the capture runner itself. The unit executes the runner as a module from the repository root so Python resolves the `scripts` package reliably.

### 3. Install the systemd unit

```sh
install -o root -g root -m 0644 deploy/systemd/civiccal-capture@.service /etc/systemd/system/civiccal-capture@.service
systemctl daemon-reload
systemd-analyze verify /etc/systemd/system/civiccal-capture@.service
```

Do **not** enable the unit. It is intentionally operator-triggered.

### 4. Run one operator-triggered capture

First validate the source registry and policy in a controlled test environment. The following command makes a real HTTPS request and must only be run after the source's current authorization record and consent have been reviewed:

```sh
systemctl start civiccal-capture@mokena-sd159-events-ical.service
systemctl status civiccal-capture@mokena-sd159-events-ical.service
journalctl -u civiccal-capture@mokena-sd159-events-ical.service --no-pager
```

The systemd unit supplies the repository working directory and the runner's default registry, archive, and report paths. It does not run automatically after boot and has no timer.

### 5. Verify output

Check that a new raw payload and metadata exist under:

```
/srv/civiccal/data/captures/mokena-sd159-events-ical/
```

Check the JSON report under:

```
/srv/civiccal/data/reports/
```

Verify HTTP status, content type, final URL, capture time, SHA-256, event count, parser warning count, completeness blockers, and source ID. Compare the report's SHA-256 to the raw payload file. Preserve the original capture even if parsing fails.

A successful HTTP retrieval is not proof of complete event coverage. Do not treat absence as cancellation, do not merge duplicate candidates, and do not publish based on capture success.

## Acceptance checklist

- [ ] Existing capture and normalization tests pass.
- [ ] New runner tests pass.
- [ ] Systemd unit passes `systemd-analyze verify`.
- [ ] Service account cannot write application code, registry, or completeness policy.
- [ ] Service account can write only capture and report directories.
- [ ] Invalid source IDs are rejected before any path is created.
- [ ] Unapproved or consent-required sources fail before network access.
- [ ] HTTPS redirects outside the source allowlist are rejected.
- [ ] `text/calendar` response is archived and parsed.
- [ ] Non-calendar payload, invalid UTF-8, oversized response, timeout, HTTP error, and malformed ICS fail safely.
- [ ] Report and raw archive hashes agree.
- [ ] No timer, cron, polling, publication, or approval mutation exists.

## Current SD159 caution

The source registry is the authority. The source entry and its notes have previously been observed to disagree about consent/polling state. Do not resolve that discrepancy by editing flags in code or by trusting prose notes. Before the first live invocation, inspect the exact deployed registry record and obtain the human operator's confirmation that its consent and access state are accurate. The runner enforces the actual fields through `load_source`.

## Rollback

Stop any running oneshot job, remove the systemd unit file, run `systemctl daemon-reload`, and remove the runner script only through a reviewed code rollback. Do not delete raw captures or reports as part of rollback; they are evidence and may be needed for reconciliation.
