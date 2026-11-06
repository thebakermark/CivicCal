# Cloudflare WARP egress for operator capture

## Goal and privacy boundary

Route CivicCal's manually invoked iCalendar capture traffic through Cloudflare WARP so the district's web server sees a Cloudflare egress address rather than the household public IP.

This is transport privacy, not anonymity. Cloudflare becomes the network intermediary. WARP does not let the operator choose a country or a fixed egress IP, and the destination can still identify the client through application-level data.

## Proxmox enforcement design

Use Proxmox as the isolation boundary, not as the WARP tunnel endpoint:

- Put the CivicCal capture worker on a dedicated, isolated virtual network.
- Give the worker no direct path to the household LAN or WAN.
- Its only permitted next hop should be a dedicated WARP gateway guest.
- Apply a VM-level Proxmox outbound policy to the worker that permits only the gateway's private address (plus only the minimum local services actually required, if any). Default-deny all other IPv4 and IPv6 egress.
- On the gateway guest, use a guest firewall with default-deny forwarding. Forward capture-worker traffic only through the WARP tunnel interface; never fall back to the gateway's ordinary WAN-facing interface.
- Keep the gateway's own WARP bootstrap/orchestration traffic distinct from forwarded capture traffic. Cloudflare documents that device orchestration HTTPS connections operate outside the WARP tunnel; this does not mean forwarded worker traffic should be allowed to use the ordinary interface.

**Important compatibility gate:** Cloudflare documents WARP as a client that creates a virtual interface and changes the local device's routing table and firewall. The documentation reviewed does not establish consumer WARP on Linux as a supported router/gateway for forwarding traffic from another machine. Therefore, the gateway design is a candidate to test, not a validated deployment recipe. Before relying on it, prove that forwarded traffic from the worker is carried through the WARP interface and that tunnel loss causes a hard drop. If the client does not correctly carry forwarded traffic, do not work around it by opening ordinary gateway egress; reassess the design.

Proxmox VE's VM firewall supports incoming and outgoing rules for a VM. VM-zone forwarded rules are not supported. VNet-level forwarding rules require the newer nftables-based `proxmox-firewall`; upstream Proxmox documentation still labels that backend a technology preview and not suitable for production. Do not enable the nftables backend solely for this project. Use the VM's own IN/OUT policy for the capture-worker-to-gateway restriction, and keep forwarding enforcement inside the gateway guest until the installed PVE 9.2.9 environment has been inspected.

Do not change the Proxmox host's default networking, household bridges, router, or unrelated guests. Do not install WARP on the Proxmox host.

## WARP guest operating system and sizing

Use a dedicated Debian 13 (Trixie) VM for the gateway candidate. Cloudflare currently lists Debian 13 as supported, with AMD64/x86-64 or ARM64, 3 vCPU minimum (4 recommended), 1 GB RAM minimum (2 GB recommended for a headless server), and 250 MiB disk minimum (500 MiB recommended). These are client requirements, not a measured workload estimate. The earlier proposed starting point of 3 vCPU, 2 GB RAM, and 8–16 GB disk is a sizing proposal only; confirm host capacity before creating anything.

## Install source and package choice

Use Cloudflare's official APT repository and signing key for Debian 13. The documented Debian installation currently installs `cloudflare-warp`:

```sh
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -d -m 0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg \
  | sudo gpg --yes --dearmor -o /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ trixie main" \
  | sudo tee /etc/apt/sources.list.d/cloudflare-client.list >/dev/null
sudo apt-get update
sudo apt-get install -y cloudflare-warp
```

Cloudflare's package staging documentation describes a separate headless `cloudflare-mesh` flavor beginning with version 2026.9, but the production repository instructions reviewed here still document `cloudflare-warp`. Do not depend on the headless flavor until Cloudflare documents and publishes it in the production GA repository for Debian 13. Do not install both flavors.

## Register and connect

For consumer WARP, use traffic-and-DNS mode (not DNS-only):

```sh
sudo warp-cli registration new
sudo warp-cli mode warp+doh
sudo warp-cli connect
warp-cli status
curl -fsS https://www.cloudflare.com/cdn-cgi/trace | grep -E '^(ip|warp)='
```

A successful local-client trace must include `warp=on`. Record the reported `ip=` value for comparison with the household WAN IP, but do not commit that address to the repository. The source should see a Cloudflare egress address. WARP is not a country-selection VPN and the egress address may change.

If the installed CLI reports different command syntax, stop and consult `warp-cli --help` and the current Cloudflare Linux client documentation rather than guessing.

## Fail-closed validation gate

A successful trace from the gateway itself is necessary but does not prove that forwarded worker traffic uses WARP. Before any live district request:

1. Verify WARP is connected after a gateway reboot.
2. From the capture worker, make a controlled request through the gateway and verify its observed public egress is not the household WAN IP.
3. Capture/inspect gateway routing and firewall counters to prove the worker's forwarded packets exit through the WARP tunnel interface, not the ordinary WAN interface.
4. Stop/disconnect WARP while leaving the gateway's ordinary network link up. Verify the worker cannot reach the public internet or district feed.
5. Verify both IPv4 and IPv6 fail closed; no alternate IPv6 route may bypass the tunnel.
6. Reboot the gateway and worker and repeat the disconnect test.
7. Restore WARP and verify one controlled HTTPS request succeeds through the tunnel.

Do not treat a preflight trace alone as a kill switch. Do not enable live capture until the forwarding and tunnel-loss tests pass. If forwarded traffic bypasses WARP or cannot be carried by the client, stop and redesign rather than allowing direct WAN fallback.

The systemd capture unit should also perform a WARP-connected preflight before invoking `capture_ics_source.py`. That preflight is a secondary guard, not the network kill switch. If it fails, it must exit nonzero without making a request. Do not weaken the existing source registry authorization checks.

## Operational limits

- WARP does not provide anonymity, a static IP, or a guaranteed geographic exit location.
- Cloudflare can observe the source IP connecting to its network and traffic metadata it processes.
- The district sees the Cloudflare egress address only when the capture request actually traverses the WARP tunnel.
- Never use DNS-only mode for this goal; it does not tunnel the HTTPS request.
- Never add a public HTTP/SOCKS proxy listener.
- Do not store credentials, registration tokens, or device identifiers in Git.
- Do not enable automatic calendar polling. The capture remains a manually started one-shot action.
- Do not alter source consent, approval, terms, robots, or polling flags as part of WARP setup.

## First-live-capture gate

The current Mokena SD159 source registry has a structured consent/notes contradiction documented in [the capture coordinator guide](ics-capture-coordinator.md). WARP setup does not resolve it. The operator/source owner must reconcile that discrepancy before the first live district request. The source's structured flags must not be changed as part of this networking work.
