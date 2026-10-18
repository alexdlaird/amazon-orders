#!/usr/bin/env bash
# Sets up a WireGuard VPN, so Amazon sees the VPN's IP instead of GitHub's. The tunnel lives in its own network
# namespace, so the runner agent keeps its normal connection to GitHub, and only the commands started with
# vpn-exec.sh go through the VPN.
# The config comes from the WIREGUARD_CONFIG environment variable (the contents of a wg-quick .conf file), and must
# include Address and DNS lines, since the namespace has neither an address nor a resolver of its own.
# Usage: WIREGUARD_CONFIG="..." connect-vpn.sh
set -euo pipefail

NAMESPACE=vpn
CONFIG_PATH=/etc/wireguard/wg0.conf

if [ -z "${WIREGUARD_CONFIG:-}" ]; then
    echo "::error::VPN enabled but VPN_WIREGUARD_CONFIG is empty. Set the VPN_WIREGUARD_CONFIG repo secret or disable the toggle."
    exit 1
fi

config_value() {
    printf '%s\n' "${WIREGUARD_CONFIG}" | sed -n -E "s/^[[:space:]]*$1[[:space:]]*=[[:space:]]*//p" | head -1 | tr ',' ' '
}

ADDRESSES=$(config_value Address)
DNS_SERVERS=$(config_value DNS)
if [ -z "${ADDRESSES}" ] || [ -z "${DNS_SERVERS}" ]; then
    echo "::error::VPN_WIREGUARD_CONFIG needs both an Address and a DNS line."
    exit 1
fi

retry() {
    for _ in 1 2 3; do
        "$@" && return 0
        sleep 3
    done
    return 1
}

in_vpn() {
    sudo ip netns exec "${NAMESPACE}" "$@"
}

sudo apt-get update -qq
sudo apt-get install -y -qq wireguard-tools

DIRECT_IP=$(curl -fsS --max-time 10 https://api.ipify.org)

sudo mkdir -p /etc/wireguard
printf '%s\n' "${WIREGUARD_CONFIG}" | sudo tee "${CONFIG_PATH}" > /dev/null
sudo chmod 600 "${CONFIG_PATH}"

# The interface is created in the host namespace and then moved, so its encrypted traffic still leaves through the
# host's own network, and only what runs inside the namespace is routed into it
sudo ip netns add "${NAMESPACE}"
sudo ip link add wg0 type wireguard
sudo ip link set wg0 netns "${NAMESPACE}"
sudo wg-quick strip "${CONFIG_PATH}" | in_vpn wg setconf wg0 /dev/stdin
for address in ${ADDRESSES}; do
    sudo ip -n "${NAMESPACE}" address add "${address}" dev wg0
done
sudo ip -n "${NAMESPACE}" link set wg0 mtu 1420 up
sudo ip -n "${NAMESPACE}" link set lo up
sudo ip -n "${NAMESPACE}" route add default dev wg0

# ip netns exec bind-mounts everything under /etc/netns/<name>/ over /etc/, so this replaces the namespace's resolver
sudo mkdir -p "/etc/netns/${NAMESPACE}"
for server in ${DNS_SERVERS}; do
    echo "nameserver ${server}"
done | sudo tee "/etc/netns/${NAMESPACE}/resolv.conf" > /dev/null

if ! retry in_vpn getent hosts www.amazon.com > /dev/null; then
    echo "::error::VPN connected, but DNS doesn't resolve through it. Check the DNS line in VPN_WIREGUARD_CONFIG."
    exit 1
fi

if ! VPN_IP=$(retry in_vpn curl -fsS --max-time 10 https://api.ipify.org); then
    echo "::error::VPN connected, but there's no internet access through it. Check the VPN server in VPN_WIREGUARD_CONFIG."
    exit 1
fi
if [ "${VPN_IP}" == "${DIRECT_IP}" ]; then
    echo "::error::VPN connected, but the egress IP didn't change, so traffic isn't going through the tunnel."
    exit 1
fi

echo "VPN connected, and the egress IP changed."
