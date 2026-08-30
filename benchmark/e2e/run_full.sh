#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

cmd=(
  python3 rerun_e2e_gem.py
  --scripts-dir scripts
  --work-dir runs/full
  --run-generation
  --elvex-bin "${ELVEX_BIN:-elvex}"
  --max-length "${ELVEX_MAX_LENGTH:-80}"
)

if [[ -n "${ELVEX_MAX_TIME:-}" ]]; then
  cmd+=(--max-time "$ELVEX_MAX_TIME")
fi
if [[ -n "${ELVEX_MAX_ITEMS:-}" ]]; then
  cmd+=(--max-items-elvex "$ELVEX_MAX_ITEMS")
fi

exec "${cmd[@]}"
