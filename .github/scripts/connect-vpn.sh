#!/usr/bin/env bash
# Routes the runner's traffic through a WireGuard VPN, so Amazon sees the VPN's IP instead of GitHub's.
# The config comes from the WIREGUARD_CONFIG environment variable (the contents of a wg-quick .conf file),
# and must include a DNS line, since the runner's own resolver isn't reachable through the tunnel.
# Usage: WIREGUARD_CONFIG="..." connect-vpn.sh
set -euo pipefail

if [ -z "${WIREGUARD_CONFIG:-}" ]; then
    echo "::error::VPN enabled but VPN_WIREGUARD_CONFIG is empty. Set the VPN_WIREGUARD_CONFIG repo secret or disable the toggle."
    exit 1
fi

DNS_SERVERS=$(printf '%s\n' "${WIREGUARD_CONFIG}" | sed -n -E 's/^[[:space:]]*DNS[[:space:]]*=[[:space:]]*//p' | head -1 | tr ',' ' ')
if [ -z "${DNS_SERVERS}" ]; then
    echo "::error::VPN_WIREGUARD_CONFIG has no DNS line, which is required to resolve hosts through the tunnel."
    exit 1
fi

sudo apt-get update -qq
sudo apt-get install -y -qq wireguard-tools

DIRECT_IP=$(curl -fsS --max-time 10 https://api.ipify.org)

# The runner agent holds long-lived connections to GitHub, which break if their return path suddenly changes to the
# VPN's IP, leaving the step hanging after it finishes. Routes in the main table with a prefix length above 0 stay
# ahead of the tunnel's default route (wg-quick suppresses only the main table's default), so those connections are
# pinned to the original gateway. Everything opened after this goes through the tunnel.
read -r GATEWAY DEVICE < <(ip -4 route show default | awk '{for (i = 1; i < NF; i++) {if ($i == "via") g = $(i + 1); if ($i == "dev") d = $(i + 1)} print g, d; exit}')
if [ -z "${GATEWAY:-}" ] || [ -z "${DEVICE:-}" ]; then
    echo "::error::Couldn't find the runner's default route, so its existing connections can't be kept off the tunnel."
    exit 1
fi
AGENT_PEERS=$(ss -H -tn state established | awk '$4 !~ /^\[/ {sub(/:[0-9]+$/, "", $4); print $4}' | grep -v -E '^(127\.|0\.)' | sort -u)
if [ -z "${AGENT_PEERS}" ]; then
    echo "::error::Found no established connections to keep off the tunnel, so the runner agent would lose contact with GitHub."
    exit 1
fi
for peer in ${AGENT_PEERS}; do
    sudo ip route replace "${peer}/32" via "${GATEWAY}" dev "${DEVICE}"
done
echo "Kept $(printf '%s\n' "${AGENT_PEERS}" | wc -l | tr -d ' ') existing connection(s) off the tunnel."

# wg-quick hands a DNS line to resolvconf, which the runner doesn't have, so DNS is set with resolvectl instead
printf '%s\n' "${WIREGUARD_CONFIG}" | grep -v -E '^[[:space:]]*DNS[[:space:]]*=' | sudo tee /etc/wireguard/wg0.conf > /dev/null
sudo chmod 600 /etc/wireguard/wg0.conf
sudo wg-quick up wg0
# shellcheck disable=SC2086
sudo resolvectl dns wg0 ${DNS_SERVERS}
sudo resolvectl domain wg0 "~."

if ! getent hosts www.amazon.com > /dev/null; then
    echo "::error::VPN connected, but DNS doesn't resolve through it. Check the DNS line in VPN_WIREGUARD_CONFIG."
    exit 1
fi

if ! VPN_IP=$(curl -fsS --max-time 10 https://api.ipify.org); then
    echo "::error::VPN connected, but there's no internet access through it. Check the VPN server in VPN_WIREGUARD_CONFIG."
    exit 1
fi
if [ "${VPN_IP}" == "${DIRECT_IP}" ]; then
    echo "::error::VPN connected, but the egress IP didn't change, so traffic isn't going through the tunnel."
    exit 1
fi

echo "VPN connected, and the egress IP changed."
