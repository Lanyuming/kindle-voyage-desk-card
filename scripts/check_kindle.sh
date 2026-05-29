#!/usr/bin/env bash
set -u

HOST="${1:-}"
PORT="${2:-22}"
EXPECTED_MAC="${3:-}"

echo "== Kindle network check =="
echo "Host: ${HOST}"
echo "Port: ${PORT}"
echo "Expected MAC: ${EXPECTED_MAC}"
echo

echo "-- Local route --"
route -n get "${HOST}" 2>/dev/null | sed -n '1,12p' || true
echo

echo "-- ARP before ping --"
arp -an | grep -i "${HOST}\|${EXPECTED_MAC}" || echo "No ARP entry yet."
echo

echo "-- Ping --"
if ping -c 3 -W 1000 "${HOST}"; then
  PING_OK=1
else
  PING_OK=0
fi
echo

echo "-- ARP after ping --"
ARP_LINE="$(arp -an | grep -i "${HOST}\|${EXPECTED_MAC}" || true)"
if [[ -n "${ARP_LINE}" ]]; then
  echo "${ARP_LINE}"
else
  echo "No ARP entry."
fi
echo

echo "-- TCP ${PORT} --"
if nc -vz -G 3 "${HOST}" "${PORT}"; then
  SSH_OK=1
else
  SSH_OK=0
fi
echo

echo "== Result =="
if [[ "${SSH_OK}" == "1" ]]; then
  echo "OK: Kindle is reachable and SSH/dropbear is listening."
  echo "Next: run scripts/kindle_card.py --config config.local.json --push"
  exit 0
fi

if echo "${ARP_LINE}" | grep -qi "incomplete" || [[ -z "${ARP_LINE}" ]]; then
  echo "NOT REACHABLE: ARP is incomplete or missing. Mac cannot see Kindle on the LAN."
  echo "Check: Kindle awake, Wi-Fi connected, same non-guest LAN, AP/client isolation disabled, correct IP binding."
  exit 2
fi

if [[ "${PING_OK}" == "1" && "${SSH_OK}" != "1" ]]; then
  echo "HOST ONLINE, SSH CLOSED: Kindle answers on LAN, but port ${PORT} is not open."
  echo "Check: start USBNetwork/dropbear on Kindle, verify SSH port and user."
  exit 3
fi

echo "UNKNOWN: Kindle may be filtered by router/firewall or asleep."
exit 4

