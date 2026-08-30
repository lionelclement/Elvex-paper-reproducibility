#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

exec python3 rerun_e2e_gem.py \
  --scripts-dir scripts \
  --work-dir runs/full \
  "$@"
