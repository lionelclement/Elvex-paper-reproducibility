#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

exec python3 rerun_e2e_gem.py \
  --scripts-dir scripts \
  --work-dir runs/smoke \
  --max-items 3 \
  --run-generation \
  --elvex-bin "${ELVEX_BIN:-elvex}" \
  --max-time "${ELVEX_MAX_TIME:-30}"
