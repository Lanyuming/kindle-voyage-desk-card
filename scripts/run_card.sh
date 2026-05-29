#!/usr/bin/env bash
set -euo pipefail

CONFIG_PATH="${1:-}"
if [[ -z "${CONFIG_PATH}" ]]; then
  echo "Usage: $0 /absolute/path/to/config.local.json" >&2
  exit 2
fi

HOUR=$((10#$(date +%H)))
if (( HOUR < 6 || HOUR >= 22 )); then
  echo "$(date '+%Y-%m-%d %H:%M') Outside active hours (6:00-22:00), skipping."
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-}"

if [[ -z "${PYTHON_BIN}" && -x "${PROJECT_DIR}/.venv/bin/python3" ]]; then
  PYTHON_BIN="${PROJECT_DIR}/.venv/bin/python3"
fi

if [[ -z "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="$(command -v python3)"
fi

cd "${PROJECT_DIR}"
"${PYTHON_BIN}" "${SCRIPT_DIR}/kindle_card.py" --config "${CONFIG_PATH}" --push
