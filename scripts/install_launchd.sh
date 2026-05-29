#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PLIST_NAME="com.local.kindle-voyage-card"
PLIST_SRC="${PROJECT_DIR}/launchd/${PLIST_NAME}.local.plist"
PLIST_DST="${HOME}/Library/LaunchAgents/${PLIST_NAME}.plist"

echo "=== Kindle Voyage Desk Card - Install LaunchDaemon ==="
echo ""

if [[ ! -f "${PLIST_SRC}" ]]; then
  echo "ERROR: ${PLIST_SRC} not found" >&2
  exit 1
fi

echo "Unloading existing service (if any)..."
launchctl unload "${PLIST_DST}" 2>/dev/null || true

echo "Installing plist..."
cp "${PLIST_SRC}" "${PLIST_DST}"

echo "Loading service..."
launchctl load "${PLIST_DST}"

echo ""
echo "Verifying..."
if launchctl list | grep -q "${PLIST_NAME}"; then
  echo "SUCCESS: Service installed and running!"
  echo "  Interval: 900s (15 minutes)"
  echo "  Config:   ${PROJECT_DIR}/config.local.json"
  echo "  Stdout:   ${PROJECT_DIR}/out/launchd.out.log"
  echo "  Stderr:   ${PROJECT_DIR}/out/launchd.err.log"
else
  echo "WARNING: Service may not be running. Check with: launchctl list | grep kindle"
fi

echo ""
echo "To uninstall:"
echo "  launchctl unload ${PLIST_DST}"
echo "  rm ${PLIST_DST}"
