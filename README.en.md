# Kindle Voyage Desk Card

**[中文](README.md) | [English](README.en.md)**

---

Turn your jailbroken Kindle Voyage into a desktop information sub-display — automatically generate and push e-ink cards with weather, calendar, to-do items, and daily quotes.

![Kindle](https://img.shields.io/badge/Kindle-Voyage-black?style=flat-square&logo=amazon) ![macOS](https://img.shields.io/badge/macOS-13%2B-blue?style=flat-square&logo=apple) ![Python](https://img.shields.io/badge/Python-3.10%2B-green?style=flat-square&logo=python) ![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

### Preview

The card is auto-generated as a 1072×1448 pixel 8-bit grayscale PNG and pushed via SSH to the Kindle's ScreenSavers Hack directory:

- **Weather**: Current temp / feels-like temp / humidity / AQI + hourly forecast + travel suggestions
- **Calendar**: Apple Calendar events for the next 3 days (time, location)
- **To-dos**: Apple Reminders tasks (grouped by "Today" and "Planned", showing due dates)
- **Quote**: Random Chinese sentence (hitokoto.cn)
- **Date**: Lunar date + current time

### Compatibility

| Device | Status |
|--------|--------|
| Kindle Voyage | ✅ Native support (1072×1448) |
| Kindle PaperWhite 3 | ⚠️ Change `canvas` size to 758×1024 |
| Kindle Oasis 2/3 | ⚠️ Change `canvas` size to 1264×1680 |
| Kindle PaperWhite 4/5 | ⚠️ Change `canvas` size to 1072×1448 (same as Voyage) |

> All jailbroken Kindles with ScreenSavers Hack installed can use this project. Just adjust `canvas.width` and `canvas.height` in your `config.json`.

### Prerequisites on Kindle

#### 1. Jailbreak

Make sure your Kindle is already jailbroken. Refer to [MobileRead Wiki](https://wiki.mobileread.com/wiki/Kindle_Hacks) for device-specific instructions.

#### 2. Required Plugins

| Plugin | Purpose | Install Via |
|--------|---------|------------|
| **MRPI** (Package Installer) | Plugin installer | Copy via USB, then install on Kindle |
| **USBNetwork Hack** | Enable WiFi SSH access | Install via MRPI or manually |
| **ScreenSavers Hack (linkss)** | Custom screensaver images | Install via MRPI or manually |
| **File Browser** | Web file manager (fallback push method) | Install via MRPI |

#### 3. Recommended Plugins

| Plugin | Purpose |
|--------|---------|
| KUAL (Kindle Unified Application Launcher) | Plugin launcher menu |
| Fonts Hack | Replace Chinese fonts (e.g., Source Han Sans) |
| Helper | Utility toolkit |

#### 4. Enable SSH

```bash
# Enable USBNetwork via KUAL or command line:
# Settings → USB Network → Enable

# Or run in Kindle terminal:
/etc/init.d/usbnetwork start
```

#### 5. WiFi Keep-Alive (Recommended)

To keep WiFi connected while in screensaver mode so the card can be pushed:

```bash
# SSH into Kindle, then create the keep-wifi service:
cat > /etc/init/keep-wifi.conf << 'EOF'
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
EOF

initctl start keep-wifi
```

### Installation on macOS

#### 1. Clone the Repository

```bash
git clone https://github.com/Lanyuming/kindle-voyage-desk-card.git
cd kindle-voyage-desk-card
```

#### 2. Create Virtual Environment & Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Dependencies:
- `Pillow>=10.0.0` — Image generation
- `requests>=2.31.0` — HTTP requests (weather API)

#### 3. Create Configuration File

```bash
cp config.example.json config.local.json
```

Edit `config.local.json`:

```json
{
  "canvas": {
    "width": 1072,
    "height": 1448,
    "margin": 54
  },
  "location": {
    "name": "Your City",
    "longitude": 0,
    "latitude": 0
  },
  "caiyun": {
    "token_env": "CAIYUN_TOKEN",
    "token": "your-caiyun-api-token",
    "timeout_seconds": 8
  },
  "apple": {
    "calendar_days": 3,
    "max_events": 8,
    "max_reminders": 7,
    "icalbuddy_path": "icalBuddy"
  },
  "kindle": {
    "host": "192.168.x.x",
    "user": "root",
    "port": 22,
    "remote_path": "/mnt/us/linkss/screensavers/deskcard.png",
    "ssh_key": "/path/to/your/kindle_key.pem",
    "ignore_push_errors": true
  },
  "output": {
    "png": "out/deskcard.png",
    "log": "out/kindle-card.log"
  }
}
```

**Configuration Reference:**

| Field | Description |
|-------|-------------|
| `canvas.width/height` | Output image pixel dimensions (match your Kindle model) |
| `location.longitude/latitude` | Weather query coordinates (get from [Caiyun Dashboard](https://dashboard.caiyunapp.com/)) |
| `caiyun.token` | Caiyun Weather API Token ([free registration](https://dashboard.caiyunapp.com/v1/token)) |
| `kindle.host` | Kindle's LAN IP address |
| `kindle.ssh_key` | Path to SSH private key (for passwordless login) |
| `kindle.remote_path` | Target path on Kindle (ScreenSavers Hack directory) |

#### 4. Set Up SSH Keys (Recommended)

```bash
# Generate key pair (if you don't have one)
ssh-keygen -t ed25519 -f ~/.ssh/kindle_key -N ""

# Copy public key to Kindle
scp -i ~/.ssh/kindle_key.pub root@<KINDLE_IP>:/tmp/authorized_keys_append
ssh root@<KINDLE_IP> 'cat /tmp/authorized_keys_append >> /root/.ssh/authorized_keys && rm /tmp/authorized_keys_append'
```

> Or use the helper script:
> ```bash
> bash scripts/setup_kindle_ssh.sh <KINDLE_IP>
> ```

#### 5. Grant macOS Automation Permissions

On first run, macOS will prompt for authorization:

- **System Preferences → Security & Privacy → Full Disk Access** — Add Terminal / your shell app
- **System Preferences → Security & Privacy → Automation** — Grant Python access to Calendar and Reminders

#### 6. Test Run

```bash
# Generate card locally (no push)
python3 scripts/kindle_card.py --config config.local.json

# Generate and push to Kindle
python3 scripts/kindle_card.py --config config.local.json --push

# Force push (skip change detection)
python3 scripts/kindle_card.py --config config.local.json --push --force
```

#### 7. Set Up Scheduled Task (launchd)

```bash
# Edit paths in launchd plist
sed -i '' 's|/ABSOLUTE/PATH/TO|'$(pwd)'|g' launchd/com.local.kindle-voyage-card.plist

# Install scheduled task (runs every 15 minutes)
bash scripts/install_launchd.sh $(pwd)/config.local.json

# Or load manually
cp launchd/com.local.kindle-voyage-card.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.local.kindle-voyage-card.plist
```

### Project Structure

```
kindle-voyage-desk-card/
├── config.example.json          # Configuration template
├── requirements.txt             # Python dependencies
├── .gitignore                   # Git ignore rules
├── launchd/
│   └── com.local.kindle-voyage-card.plist   # macOS launchd template
├── references/
│   └── kindle-side-notes.md     # Troubleshooting & Kindle notes
└── scripts/
    ├── kindle_card.py           # Core card generation & push logic
    ├── run_card.sh              # launchd entry script (with time filtering)
    ├── install_launchd.sh       # One-click launchd installer
    ├── setup_kindle_ssh.sh      # One-click Kindle SSH key setup
    └── check_kindle.sh          # Kindle network connectivity diagnostic
```

### Troubleshooting

#### Cannot Connect to Kindle

```bash
# Diagnose network connectivity
bash scripts/check_kindle.sh <KINDLE_IP>

# Common issues:
# 1. Kindle WiFi disconnected → Check if keep-wifi service is running
# 2. IP changed → Bind MAC address in router settings
# 3. SSH port not open → Restart usbnetwork on Kindle: /etc/init.d/usbnetwork restart
```

#### Card Not Updating / Screensaver Not Switching

```bash
# Check if ScreenSavers Hack is working
ssh root@<KINDLE_IP> 'ls -la /mnt/us/linkss/screensavers/'

# If directory doesn't exist, create it:
ssh root@<KINDLE_IP> 'mkdir -p /mnt/us/linkss/screensavers'

# Trigger screensaver refresh (power button toggle):
ssh root@<KINDLE_IP> 'lipc-set-prop com.lab126.powerd powerButton 1'
```

#### macOS Automation Permission Errors

If you get permission errors on first run:

1. Open **System Preferences → Security & Privacy → Privacy**
2. Find **Full Disk Access**, add Terminal/iTerm2
3. Find **Automation**, check Python access for Calendar and Reminders
4. Restart terminal and try again

See [references/kindle-side-notes.md](references/kindle-side-notes.md) for more troubleshooting details.

### Data Sources

| Data | Source | API Key Required |
|------|--------|-----------------|
| Weather | [Caiyun Weather API](https://www.caiyunapp.com/) | ✅ Free token |
| Calendar | Apple Calendar (local AppleScript) | ❌ Local read |
| To-dos | Apple Reminders (local AppleScript) | ❌ Local read |
| Quote | [hitokoto.cn](https://hitokoto.cn/) | ❌ No key needed |

### For International Users

> This project defaults to Chinese services (Caiyun Weather, hitokoto). Users outside China can adapt it using the alternatives below by modifying `scripts/kindle_card.py`.

**Weather: OpenWeatherMap**

[OpenWeatherMap](https://openweathermap.org/api) offers free weather data (1000 calls/day on free tier), with global coverage.

```bash
# 1. Get a free API key
# https://home.openweathermap.org/api_keys

# 2. Set as environment variable
export OWM_API_KEY="your_openweathermap_api_key"
```

Replace `get_weather()` in `kindle_card.py`:

```python
def get_weather():
    """Fetch weather from OpenWeatherMap"""
    import os
    token = os.environ.get("OWM_API_KEY", "")
    loc = CONFIG["location"]  # format: "longitude,latitude"
    lon, lat = loc.split(",")
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units=metric&appid={token}"
    r = requests.get(url, timeout=10)
    data = r.json()
    return {
        "temp": int(data["main"]["temp"]),
        "desc": data["weather"][0]["main"],
        "icon": "*",
        "humidity": f"{data['main']['humidity']}%",
        "wind": f"{data['wind']['speed']:.0f}km/h",
        "aqi": None,
        "apparent": int(data["main"]["feels_like"]),
        "suggestion": "Check the weather outside!"
    }
```

**Quote: Quotable API**

[Quotable](https://github.com/lukePeavey/quotable) provides free random quotes, no API key required.

```python
def get_hitokoto():
    """Fetch a random quote from Quotable"""
    try:
        r = requests.get("https://api.quotable.io/random", timeout=5)
        data = r.json()
        return {"content": data.get("content", ""), "source": data.get("author", "")}
    except Exception:
        return {"content": "The only way to do great work is to love what you do.", "source": "Steve Jobs"}
```

**Coordinate Lookup Tools**

- [OpenStreetMap Nominatim](https://nominatim.openstreetmap.org/) — Search a place name to get coordinates
- [Google Maps](https://maps.google.com) — Right-click → coordinates

---

## License

[MIT License](LICENSE)

---

**Note**: This project is for personal learning and educational purposes only. Jailbreaking your Kindle may void its warranty. Use at your own risk.
