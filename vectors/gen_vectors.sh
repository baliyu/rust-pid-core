#!/usr/bin/env bash
# Builds the C core with the undefined-behaviour sanitiser and dumps replay vectors.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
CORE="${CORE_DIR:-/mnt/c/stm32-pid-control-lab/core}"
TMP="$(mktemp -d)"
gcc -O1 -g -Wall -Wextra -Wshadow -fsanitize=undefined -fno-sanitize-recover=all \
    -I "$CORE" "$CORE/pid.c" "$CORE/supervisor.c" "$CORE/control.c" "$HERE/gen.c" -o "$TMP/gen"
"$TMP/gen" > "$HERE/vectors.csv"
echo "c_core_commit=$(git -C "$CORE/.." rev-parse HEAD)" > "$HERE/PROVENANCE.txt"
rm -rf "$TMP"
