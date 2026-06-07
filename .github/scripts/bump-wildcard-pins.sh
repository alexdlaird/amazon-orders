#!/usr/bin/env bash
# Replaces ==X.Y.* wildcard pin references with ==NEW_MAJOR.NEW_MINOR.* in the given files.
# Usage: bump-wildcard-pins.sh <new_version> <file> [<file> ...]
set -euo pipefail

NEW_VERSION="${1:?Usage: bump-wildcard-pins.sh <new_version> <file>...}"
shift

NEW_MAJOR_MINOR=$(echo "${NEW_VERSION}" | cut -d. -f1-2)

for f in "$@"; do
    sed -i -E "s/==[0-9]+\.[0-9]+\.\*/==${NEW_MAJOR_MINOR}.*/g" "${f}"
    grep -qF "==${NEW_MAJOR_MINOR}.*" "${f}" || { echo "Wildcard pin bump failed in ${f}"; exit 1; }
done
