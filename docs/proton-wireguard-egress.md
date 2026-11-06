# Proton VPN WireGuard egress for CivicCal capture

## Goal

Route only CivicCal's manually invoked iCalendar capture traffic through the user's existing Proton VPN subscription using a dedicated WireGuard gateway. The district should see Proton VPN egress rather than the household public IP.

This is transport privacy, not anonymity. Proton is the VPN provider and can observe connection metadata. The destination can still identify the client through application-level data. Proton egress addresses may be shared or change; do not assume a fixed IP or geographic exit.

## Existing infrastructure context

The household already uses Proton VPN with WireGuard through Gluetun for an isolated media workload. Keep that workload independent. Do not attach CivicCal to the media stack's Gluetun container or reuse its active WireGuard client configuration. Generate a separate Proton WireGuard configuration for the CivicCal gateway so the two tunnels have independent keys, lifecycle, and failure domains.

## Proposed network topology

Use a dedicated small Debian gateway VM with two virtual NICs:

- WAN-side NIC: connected to the existing Proxmox uplink bridge so the gateway can establish its encrypted WireGuard session to Proton.
- Capture-side NIC: connected only to a new isolated Proxmox bridge/VNet shared with the CivicCal capture worker.

The capture worker has only the isolated capture-side NIC. It has no second NIC, no direct household-LAN route, and no direct WAN route. Its default gateway is the private address of the Proton gateway VM.

Enforcement is layered:

1. Proxmox VM-level outbound policy on the capture worker allows only the gateway's private IP and denies other IPv4 and IPv6 destinations.
2. The gateway guest's nftables policy defaults to dropping forwarded traffic. It accepts capture-subnet traffic only from the capture-side NIC and forwards it only out the WireGuard interface (for example, `wg0`).
3. The gateway performs source NAT/masquerading for the capture subnet only when packets leave through `wg0`.
4. No forwarding rule permits capture-subnet traffic to leave through the gateway's WAN-side NIC.
5. The gateway's own host traffic may reach the Proton WireGuard endpoint through its WAN NIC to establish/maintain the tunnel. This exception is for the gateway's tunnel transport, not for forwarded capture traffic.
6. IPv6 is either routed through the Proton tunnel end-to-end or explicitly disabled/blocked on the capture segment and gateway forwarding path. Never leave an untested IPv6 route that can bypass the VPN.

This keeps the Proxmox host, home router, household bridge, and unrelated guests out of the VPN routing path.

## Proton WireGuard configuration

Generate a dedicated configuration in the Proton account portal:

1. Sign in to the Proton account.
2. Open Downloads → WireGuard configuration.
3. Create a new configuration with a distinct name such as `civiccal-gw`.
4. Select Router as the platform/device type when offered.
5. Choose a server and desired VPN options; do not enable port forwarding because CivicCal only needs outbound HTTPS.
6. Download the generated `.conf` file.

Proton documents that its WireGuard configurations can be used with third-party WireGuard clients, including router clients. Proton's Linux guide documents use with `wg-quick`. Use a newly generated config for this gateway; do not copy the active media-stack key/configuration.

Treat the downloaded file as a secret: it contains the WireGuard private key. Transfer it directly to the gateway through a secure operator-controlled method, store it outside the repository with root-only permissions (for example, mode `0600`), and never place it in Git, logs, screenshots, or deployment artifacts. Do not paste the config or private key into chat.

Proton's current WireGuard configs support IPv6. Inspect the generated `AllowedIPs` and DNS values rather than assuming their contents. For a full-tunnel design, the allowed destinations must cover both IPv4 and IPv6 default routes (typically `0.0.0.0/0, ::/0`) or IPv6 must be deliberately blocked at the gateway and capture segment. The generated file is authoritative for the endpoint, keys, addresses, and DNS settings.

## Gateway implementation approach

Prefer the standard Linux WireGuard implementation (`wireguard-tools` / `wg-quick`) plus nftables on the dedicated Debian gateway. This avoids adding another orchestration layer and keeps the tunnel and packet-forwarding rules inspectable.

Do not copy a generic `wg-quick` kill-switch snippet and assume it protects forwarded traffic. The gateway needs explicit nftables forwarding policy for the capture subnet. A host-output kill switch and a forwarded-traffic kill switch are different controls.

Required policy shape (not a ready-to-run ruleset):

- Default-drop the gateway's forwarded traffic.
- Permit established/related return traffic.
- Permit new forwarding from the capture NIC/subnet to `wg0`.
- Deny forwarding from the capture NIC/subnet to the WAN NIC, including IPv4 and IPv6.
- Masquerade only the capture subnet when the output interface is `wg0`.
- Permit the gateway's own WireGuard UDP transport to the Proton endpoint over the WAN NIC.
- Restrict management access to the gateway from the trusted admin network only; do not expose a public management listener.
- Keep DNS for the capture worker on the tunnel path. Do not provide a fallback resolver that sends DNS to the ordinary WAN.

The exact nftables rules, interface names, subnets, DNS design, and Proxmox firewall rules must be derived from a read-only inventory of the installed PVE 9.2.9 host and selected Debian gateway network configuration. Do not guess interface names or paste this policy into a live host.

## Fail-closed validation gate

Do not run the first live district capture until all tests pass:

1. Confirm the gateway establishes the Proton WireGuard tunnel and its own public egress differs from the household WAN address.
2. From the capture worker, make a controlled HTTPS request through the gateway and confirm the observed public egress is Proton, not the household WAN.
3. Verify gateway nftables counters show forwarded capture packets leaving through `wg0`.
4. Disconnect or stop WireGuard while leaving the gateway's WAN NIC connected. Confirm the capture worker cannot reach any public IPv4 or IPv6 destination.
5. Confirm DNS from the capture worker also fails closed during tunnel loss; no resolver may fall back to the WAN.
6. Reboot the gateway and capture worker and repeat the tunnel-loss test.
7. Restore WireGuard and confirm one controlled HTTPS request succeeds through Proton.
8. Inspect routes and firewall counters to prove there is no WAN forwarding path for the capture subnet.

A successful request while connected is not enough. The disconnect test is the proof of the kill switch. If any packet escapes through the gateway WAN interface, stop and correct the policy before live capture.

The systemd capture unit may also perform a WireGuard-interface/preflight check before invoking `capture_ics_source.py`. Treat that as a secondary guard only; nftables forwarding policy is the network enforcement boundary. If preflight fails, the one-shot capture must exit nonzero without making a request.

## Operational limits and safeguards

- Proton VPN hides the household public IP from the destination only when the capture request actually traverses the Proton tunnel.
- Proton can observe connection metadata; this is not anonymity.
- Do not enable port forwarding; no inbound connection is required.
- Do not expose a public HTTP/SOCKS proxy.
- Do not store WireGuard private keys or full configuration files in Git.
- Keep CivicCal capture manual and one-shot. Do not enable calendar polling, cron, or a timer.
- Do not change source consent, approval, terms, robots, or polling flags as part of VPN setup.
- Do not install or configure WireGuard on the Proxmox host or home router.
- Do not reuse the media-stack WireGuard key/config or alter its Gluetun/qBittorrent routing.

## First-live-capture gate

The current Mokena SD159 source registry has a structured consent/notes contradiction documented in [the capture coordinator guide](ics-capture-coordinator.md). Proton VPN setup does not resolve it. The operator/source owner must reconcile that discrepancy before the first live district request. Do not change the source's structured flags as part of this networking work.
