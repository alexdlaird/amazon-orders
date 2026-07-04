#!/usr/bin/env bash
# Replaces ==X.Y.* wildcard pin references with ==NEW_MAJOR.NEW_MINOR.* in the given files.
# For SECURITY.md, updates the supported-version table rows instead (major/minor bumps only).
# Usage: bump-wildcard-pins.sh <new_version> <file> [<file> ...]
set -euo pipefail

SED=$(command -v gsed || command -v sed)

NEW_VERSION="${1:?Usage: bump-wildcard-pins.sh <new_version> <file>...}"
shift

NEW_MAJOR_MINOR=$(echo "${NEW_VERSION}" | cut -d. -f1-2)

for f in "$@"; do
    if [[ "$(basename "$f")" == "SECURITY.md" ]]; then
        [ -f "$f" ] || continue
        grep -qF "| ${NEW_MAJOR_MINOR}.x" "$f" && continue
        $SED -i -E "s/\| [0-9]+\.[0-9]+\.x/| ${NEW_MAJOR_MINOR}.x/" "$f"
        $SED -i -E "s/\| < [0-9]+\.[0-9]+/| < ${NEW_MAJOR_MINOR}/" "$f"
        grep -qF "| ${NEW_MAJOR_MINOR}.x" "$f" || { echo "SECURITY.md supported-version bump failed"; exit 1; }
        grep -qF "| < ${NEW_MAJOR_MINOR}" "$f" || { echo "SECURITY.md less-than version bump failed"; exit 1; }
    else
        $SED -i -E "s/==[0-9]+\.[0-9]+\.[0-9]+/==${NEW_MAJOR_MINOR}.0/g" "${f}"
        $SED -i -E "s/==[0-9]+\.[0-9]+\.\*/==${NEW_MAJOR_MINOR}.*/g" "${f}"
        grep -qF "==${NEW_MAJOR_MINOR}.*" "${f}" || { echo "Wildcard pin bump failed in ${f}"; exit 1; }
    fi
done
