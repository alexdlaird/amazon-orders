#!/usr/bin/env bash
# Runs the given command through the VPN that connect-vpn.sh set up, or directly if there isn't one.
# Both sudo calls keep the environment (secrets, config) and the rest is set explicitly, since sudo drops PATH and
# LD_LIBRARY_PATH, which the Python from setup-python needs.
# Usage: vpn-exec.sh <command> [args...]
set -euo pipefail

if [ -e /var/run/netns/vpn ]; then
    exec sudo -E ip netns exec vpn sudo -E -u "$(id -un)" env "PATH=${PATH}" "HOME=${HOME}" \
        "LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-}" "$@"
fi

exec "$@"
