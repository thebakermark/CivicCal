# Cloudflare WARP egress for operator capture

## Goal

Route CivicCal's manually invoked iCalendar capture traffic through Cloudflare WARP so the district's web server sees a Cloudflare egress address rather than the household public IP.

This is transport privacy, not anonymity. Cloudflare becomes the network intermediary. WARP does not let the operator choose a country or a fixed egress IP, and the destination can still identify the client through application-level data.

## Chosen deployment boundary

Run the capture worker in a dedicated Debian 13 guest with WARP installed locally. Prefer a small VM over the previously proposed unprivileged LXC for the first deployment: WARP installs a system networking client that manages a tunnel interface and routes. A VM avoids depending on Proxmox LXC device passthrough and extra container capabilities for `/dev/net/tun` and network administration.

Do not install WARP on the Proxmox host, the household router, or unrelated CivicCal services.

Cloudflare's current Linux requirements list Debian 13, x86-64/ARM64, 3 vCPU minimum (4 recommended), 1 GB RAM minimum (2 GB recommended) for a headless server, and 250 MiB disk minimum (500 MiB recommended). Start with 3 vCPU, 2 GB RAM, and 8–16 GB disk if the host has capacity. These are Cloudflare's client requirements, not a measured CivicCal workload estimate.

## Install the headless client

Use Cloudflare's official APT repository and signing key. On Debian 13 (Trixie):

```sh
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -d -m 0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg \
  | sudo gpg --yes --dearmor -o /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ trixie main" \
  | sudo tee /etc/apt/sources.list.d/cloudflare-client.list >/dev/null
sudo apt-get update
sudo apt-get install -y cloudflare-mesh
```

The headless `cloudflare-mesh` package includes the WARP daemon and CLI without the graphical interface. Cloudflare documents the GUI-capable `cloudflare-warp` package separately; do not install both flavors.

## Register and connect

Run the consumer WARP client in traffic-and-DNS mode (not DNS-only):

```sh
sudo warp-cli registration new
sudo warp-cli mode warp+doh
sudo warp-cli connect
warp-cli status
curl -fsS https://www.cloudflare.com/cdn-cgi/trace | grep -E '^(ip|warp)='
```

A successful trace must include `warp=on`. Record the reported `ip=` value for comparison with the household WAN IP, but do not commit that address to the repository. The source should see a Cloudflare egress address. WARP is not a country-selection VPN and the egress address may change.

If the installed CLI reports a different command syntax, stop and consult `warp-cli --help` and the current Cloudflare Linux client documentation rather than guessing.

## Capture must fail closed

A WARP connection check is necessary but not sufficient. Before enabling live capture:

1. Verify WARP is connected after a guest reboot.
2. Verify `warp=on` from the same guest and under the same network namespace that runs the capture.
3. Verify the trace's public IP is not the household WAN IP.
4. Confirm DNS resolution is also using the WARP path.
5. Stop WARP and verify the capture worker cannot reach the district feed directly.
6. Restore WARP and verify a single controlled HTTPS request succeeds.
7. Inspect route and firewall behavior after restart and tunnel loss.

Do not treat a preflight trace alone as a kill switch. The final service needs an enforced fail-closed egress policy so a WARP outage cannot silently fall back to the household WAN. Build and test that policy in the isolated guest before the first district request. Do not apply firewall/routing changes to Proxmox or the home router.

The systemd capture unit should also perform a WARP-connected preflight before invoking `capture_ics_source.py`. If the preflight fails, it must exit nonzero without making a request. Do not weaken the existing source registry authorization checks.

## Operational limits

- WARP does not provide anonymity, a static IP, or a guaranteed geographic exit location.
- Cloudflare can observe the source IP connecting to its network and the traffic metadata it processes.
- The district sees the Cloudflare egress address, not the household public IP, when the tunnel is active.
- Never use DNS-only mode for this goal; it does not tunnel the HTTPS request.
- Never add a public HTTP/SOCKS proxy listener.
- Do not store credentials, registration tokens, or device identifiers in Git.
- Do not enable automatic calendar polling. The capture remains a manually started one-shot action.
- Do not alter source consent, approval, terms, robots, or polling flags as part of WARP setup.

## First-live-capture gate

The current Mokena SD159 source registry has a structured consent/notes contradiction documented in [the capture coordinator guide](ics-capture-coordinator.md). WARP setup does not resolve it. The operator/source owner must reconcile that discrepancy before the first live district request. The source's structured flags must not be changed as part of this networking work.
