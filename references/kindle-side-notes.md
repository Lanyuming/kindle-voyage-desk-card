# Kindle-side notes

## Goal

The Kindle should remain a normal reader. The macOS machine only replaces a screensaver PNG. When Kindle sleeps, the jailbreak/custom screensaver plugin displays that PNG. When Kindle wakes, the native reader continues normally.

## Kindle Voyage details

- Recommended image size: `1072x1448` portrait.
- Image mode: 8-bit grayscale PNG.
- Prefer high-contrast typography and thick dividers.
- Keep one image in the configured screensaver directory and overwrite it with a fixed filename.

## SSH key setup outline

From macOS:

```bash
ssh-copy-id root@<KINDLE_IP>
ssh root@<KINDLE_IP> 'mkdir -p /mnt/us/linkss/screensavers'
```

If `ssh-copy-id` is unavailable, manually append your macOS public key to the Kindle SSH `authorized_keys` file according to your installed SSH package/dropbear setup.

## Keep Wi-Fi awake

Kindle jailbreak setups differ. The important requirement is that Wi-Fi and SSH are reachable during the times macOS pushes the file. If Wi-Fi sleeps while Kindle is suspended, the launchd job will simply fail until the Kindle is reachable again.

## Common remote paths

Try the path matching your screensaver plugin:

- `/mnt/us/linkss/screensavers/deskcard.png`
- `/mnt/us/extensions/linkss/screensavers/deskcard.png`
- `/mnt/us/screensavers/deskcard.png`
- Any custom directory selected by the screensaver plugin.

## Coexistence with native reader and Android/CrackKDroid

This workflow does not replace the native reader and does not need a resident Kindle process. It only updates a file on the visible USB storage partition or plugin directory. Sleep and wake behavior remains controlled by Kindle firmware/screensaver plugin.

## Troubleshooting

- If the image does not change, verify the plugin watches the exact directory and filename.
- If scp fails, test `ssh root@<KINDLE_IP>` from macOS first.
- If the card is distorted, use `1072x1448` for Kindle Voyage instead of `758x1024`.
- If Chinese text renders as boxes, set `fonts.regular` and `fonts.bold` in config to a CJK font on macOS.

## LAN diagnosis used in this setup

The Mac can be on 5 GHz Wi-Fi and the Kindle can be on 2.4 GHz Wi-Fi as long as both SSIDs are bridged into the same LAN. Problems usually come from guest-network isolation, AP/client isolation, the Kindle being asleep, or dropbear not running.

Run from the project directory:

```bash
scripts/check_kindle.sh <KINDLE_IP> 22 <MAC_ADDRESS>
```

Current observed pattern for this Kindle:

```text
ARP sees <KINDLE_IP> at <MAC_ADDRESS>
ping receives no replies
TCP 22 times out
```

This means the IP/MAC binding is known, but the Kindle is not accepting LAN traffic on SSH. Most likely next steps are:

1. Wake the Kindle and open Wi-Fi settings so the radio stays active.
2. Verify the router shows the Kindle as online, not merely bound/reserved.
3. Disable guest-network/AP/client isolation between 5 GHz and 2.4 GHz SSIDs.
4. Start the Kindle jailbreak USBNetwork/dropbear service from KUAL or the installed launcher.
5. If using USBNetwork, ensure Wi-Fi SSH/dropbear is enabled, not only USB networking.

---

## Emergency recovery playbook

When the Kindle is in a broken state (screen flickering, unresponsive, WiFi down), follow this sequence.

### Step 1: Force reboot

Hold power button for 20 seconds. Wait for the tree loading screen, then the home page.

### Step 2: Connect WiFi

After reboot, manually connect WiFi in Settings. The IP is bound to MAC on the router (`<KINDLE_IP>`).

### Step 3: Verify SSH

```bash
ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -o ConnectTimeout=10 -o BatchMode=yes \
    -i <SSH_KEY>.pem root@<KINDLE_IP> "echo OK"
```

If SSH times out but the Kindle shows WiFi connected, the keep-wifi service may be interfering. Try FileBrowser at `http://<KINDLE_IP>` as a fallback.

### Step 4: Stop the offending service

```bash
ssh ... root@<KINDLE_IP> "initctl stop keep-wifi"
```

Then verify the powerd state is stable:

```bash
ssh ... root@<KINDLE_IP> "for i in 1 2 3 4 5; do lipc-get-prop com.lab126.powerd state; sleep 2; done"
```

If the state stays constant (either `active` or `screenSaver`), the service was the cause.

---

## Known bugs and fixes

### Bug: Screen keeps toggling between screensaver and home

**Root cause:** The `keep-wifi` upstart service was blindly executing `lipc-set-prop com.lab126.wifid enable 1` every 30 seconds. Even when WiFi was already connected, this command resets the wifid state machine, which in turn triggers powerd to flip between `active` and `screenSaver`.

**Wrong keep-wifi.conf (causes toggling):**

```conf
script
    while true; do
        lipc-set-prop com.lab126.wifid enable 1 2>/dev/null || true
        sleep 30
    done
end script
```

**Correct keep-wifi.conf (conditional, only re-enables if disabled):**

```conf
start on started wifid
stop on stopping wifid

env WIFI_CHECK_INTERVAL=60

respawn
respawn limit 3 300

script
    while true; do
        WIFI_STATE=$(lipc-get-prop com.lab126.wifid enable 2>/dev/null || echo "0")
        if [ "$WIFI_STATE" != "1" ]; then
            lipc-set-prop com.lab126.wifid enable 1 2>/dev/null || true
        fi
        sleep $WIFI_CHECK_INTERVAL
    done
end script
```

**How to deploy:**

```bash
# Copy to Kindle
scp -i <SSH_KEY>.pem keep-wifi.conf root@<KINDLE_IP>:/mnt/us/linkss/keep-wifi.conf

# Apply on Kindle
ssh ... root@<KINDLE_IP> "
    initctl stop keep-wifi
    mount -o rw,remount /
    cp /mnt/us/linkss/keep-wifi.conf /etc/upstart/keep-wifi.conf
    initctl reload-configuration
    initctl start keep-wifi
"
```

### Bug: `initctl restart powerd` does not actually restart powerd

**Root cause:** Upstart considers the service already running and skips the restart. The old powerd process keeps its stale state.

**Fix:** Kill the process first, then start:

```bash
kill -9 $(pidof powerd) 2>/dev/null || true
sleep 2
initctl start powerd 2>/dev/null || true
```

**Do NOT use:** `initctl restart powerd`

### Bug: CVM (Java UI) segfault after repeated powerd/framework restarts

**Root cause:** Kindle Voyage has only ~500MB RAM. Repeatedly killing and restarting powerd/framework causes memory leaks. When free RAM drops below ~15MB, the CVM process segfaults, and the UI becomes unresponsive (no home page, no screensaver toggle).

**Symptoms:**

- `ps | grep cvm` shows nothing (process name is actually `/usr/java/bin/cvm`)
- `/var/log/messages` shows `segfault` entries for `AWT-EventQueue`, `Image Fetcher`, etc.
- `lipc-set-prop com.lab126.powerd powerButton 1` has no effect

**Fix:** Force reboot the Kindle (hold power 20s). After reboot, free RAM should be ~60MB+.

### Bug: Screensavers directory missing after reboot

**Root cause:** The `/mnt/us/linkss/screensavers/` directory is not created by the linkss plugin by default. It must be created manually.

**Fix:** Add `mkdir -p /mnt/us/linkss/screensavers` to autostart.sh and deploy_all.sh.

### Bug: Todo list missing "Today"/"Planned" section headers

**Root cause:** The rendering code used a single `in_today` toggle variable instead of two independent flags. When only "planned" items existed, the "Planned" header was never shown because `in_today` started as `True`.

**Fix:** Use `today_header_shown` and `plan_header_shown` as independent boolean flags.

### Bug: Planned todo items missing date labels

**Root cause:** `get_reminders()` discarded the due date when building the result list: `for _, t in upcoming_items`.

**Fix:** Return tuples `("●", title, None)` for today and `("○", title, "06-02")` for planned items. Render the date in light gray on the right side of planned items.

---

## Key Kindle system commands

### powerd state management

```bash
# Check current state (active = home, screenSaver = sleeping, readyToSuspend = about to sleep)
lipc-get-prop com.lab126.powerd state

# Toggle between active and screenSaver (like pressing power button)
lipc-set-prop com.lab126.powerd powerButton 1

# Prevent screensaver (1 = block, 0 = allow)
lipc-set-prop -i com.lab126.powerd preventScreenSaver 0

# Check preventScreenSaver value
lipc-get-prop com.lab126.powerd preventScreenSaver
```

### Service management

```bash
# List running upstart services
initctl list | grep 'start/running'

# Stop/start a service
initctl stop keep-wifi
initctl start keep-wifi

# Reload config after changing .conf files
initctl reload-configuration

# Check service status
initctl status keep-wifi
```

### Process inspection

```bash
# Find CVM process (name is /usr/java/bin/cvm, not just "cvm")
ps -ef | grep cvm | grep -v grep
# Or check by PID from logs
cat /proc/<PID>/cmdline | tr '\0' ' '

# Check memory
cat /proc/meminfo | head -3

# Check for segfaults
cat /var/log/messages | grep -i segfault | tail -5
```

### Screensaver refresh

```bash
# Refresh linkss screensaver (picks up new images from /mnt/us/linkss/screensavers/)
/mnt/us/linkss/bin/linkss

# Full refresh sequence: update image + refresh + trigger screensaver
scp bg_ss00.png root@<KINDLE_IP>:/mnt/us/linkss/screensavers/bg_ss00.png
ssh ... "/mnt/us/linkss/bin/linkss; lipc-set-prop com.lab126.powerd powerButton 1"
```

### WiFi management

```bash
# Check WiFi status
lipc-get-prop com.lab126.wifid enable
# Returns "1" if enabled, "0" if disabled

# Enable WiFi
lipc-set-prop com.lab126.wifid enable 1

# Check IP
ifconfig wlan0 | grep 'inet addr'
```

---

## FileBrowser fallback

When SSH is unavailable but the Kindle has WiFi and FileBrowser running, you can use the FileBrowser HTTP API:

```bash
# Login (replace username/password with your FileBrowser credentials)
TOKEN=$(curl -s -X POST "http://<KINDLE_IP>/api/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"<FB_USER>","password":"<FB_PASS>"}')

# Upload a file
curl -X PUT "http://<KINDLE_IP>/api/resources/linkss/keep-wifi.conf" \
    -H "Content-Type: text/plain" \
    -H "X-Auth: $TOKEN" \
    --data-binary @keep-wifi.conf

# List directory
curl -s "http://<KINDLE_IP>/api/resources/linkss/" \
    -H "X-Auth: $TOKEN" | python3 -m json.tool
```

Note: FileBrowser's command execution API (`POST /api/command`) is unreliable on Kindle. Prefer SSH for running commands.

---

## Stable state reference

After all fixes, a healthy Kindle desk-card setup should show:

| Check | Expected |
|-------|----------|
| `lipc-get-prop com.lab126.powerd state` | `active` or `screenSaver` (stable, not toggling) |
| `initctl status keep-wifi` | `start/running` |
| `cat /etc/upstart/keep-wifi.conf` | Conditional WiFi check (not blind `enable 1`) |
| `ls /mnt/us/linkss/screensavers/` | Contains `bg_ss00.png` |
| `cat /proc/meminfo \| head -1` | MemTotal ~514724 kB, MemFree > 50000 kB |
| `ps -ef \| grep cvm` | CVM process running |
| `ifconfig wlan0 \| grep inet` | `<KINDLE_IP>` |
