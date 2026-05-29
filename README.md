# Kindle Voyage Desk Card

**[中文](#中文) | [English](#english)**

---

## 中文

将越狱的 Kindle Voyage 变成你的桌面信息副屏 —— 自动生成并推送包含天气、日历、待办、一言的墨水屏卡片。

![Kindle](https://img.shields.io/badge/Kindle-Voyage-black?style=flat-square&logo=amazon) ![macOS](https://img.shields.io/badge/macOS-13%2B-blue?style=flat-square&logo=apple) ![Python](https://img.shields.io/badge/Python-3.10%2B-green?style=flat-square&logo=python) ![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)

### 功能预览

卡片自动生成 1072×1448 像素的 8-bit 灰度 PNG，通过 SSH 推送到 Kindle 的 ScreenSavers Hack 屏保目录：

- **天气**：当前温度 / 体感温度 / 湿度 / AQI + 未来几小时预报 + 出行建议
- **日历**：Apple Calendar 未来 3 天日程（时间、地点）
- **待办**：Apple Reminders 待办事项（区分"今天"和"计划"，显示截止日期）
- **一言**：随机中文句子（hitokoto.cn）
- **日期**：农历日期 + 当前时间

### 兼容性

| 设备 | 支持情况 |
|------|---------|
| Kindle Voyage | ✅ 完美适配（1072×1448） |
| Kindle PaperWhite 3 | ⚠️ 需修改 canvas 尺寸为 758×1024 |
| Kindle Oasis 2/3 | ⚠️ 需修改 canvas 尺寸为 1264×1680 |
| Kindle PaperWhite 4/5 | ⚠️ 需修改 canvas 尺寸为 1072×1448（同 Voyage） |

> 所有已越狱且安装了 ScreenSavers Hack 的 Kindle 均可使用，只需调整 `config.json` 中的 `canvas.width` 和 `canvas.height`。

### Kindle 端前置要求

#### 1. 越狱

确保你的 Kindle 已经完成越狱。不同固件版本的越狱方法请参考 [MobileRead Wiki](https://wiki.mobileread.com/wiki/Kindle_Hacks)。

#### 2. 必装插件

| 插件 | 用途 | 安装方式 |
|------|------|---------|
| **MRPI** (Package Installer) | 插件安装器 | 通过 USB 拷贝到 Kindle 后安装 |
| **USBNetwork Hack** | 开启 WiFi SSH 连接 | MRPI 安装或手动安装 |
| **ScreenSavers Hack (linkss)** | 自定义屏保图片 | MRPI 安装或手动安装 |
| **File Browser** | Web 文件管理器（备用推送方式） | MRPI 安装 |

#### 3. 推荐插件

| 插件 | 用途 |
|------|------|
| KUAL (Kindle Unified Application Launcher) | 插件启动菜单 |
| Fonts Hack | 更换中文字体（如思源黑体） |
| Helper | 小工具集合 |

#### 4. 启用 SSH

```bash
# 在 Kindle 上通过 KUAL 或命令行启用 USBNetwork：
# Settings → USB Network → Enable

# 或者在 Kindle 的终端中执行：
/etc/init.d/usbnetwork start
```

#### 5. 配置 WiFi 保活（可选但推荐）

为了让 Kindle 在屏保状态下保持 WiFi 连接以便接收卡片推送：

```bash
# SSH 进入 Kindle 后创建 keep-wifi 服务
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

### macOS 端安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/Lanyuming/kindle-voyage-desk-card.git
cd kindle-voyage-desk-card
```

#### 2. 创建虚拟环境 & 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

依赖列表：
- `Pillow>=10.0.0` — 图片生成
- `requests>=2.31.0` — HTTP 请求（天气 API）

#### 3. 创建配置文件

```bash
cp config.example.json config.local.json
```

编辑 `config.local.json`：

```json
{
  "canvas": {
    "width": 1072,
    "height": 1448,
    "margin": 54
  },
  "location": {
    "name": "你的城市",
    "longitude": 0,
    "latitude": 0
  },
  "caiyun": {
    "token_env": "CAIYUN_TOKEN",
    "token": "你的彩云天气API密钥",
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

**配置项说明：**

| 字段 | 说明 |
|------|------|
| `canvas.width/height` | 输出图片像素尺寸（匹配你的 Kindle 型号） |
| `location.longitude/latitude` | 天气查询坐标（可在 [彩云天气控制台](https://dashboard.caiyunapp.com/) 获取） |
| `caiyun.token` | 彩云天气 API Token（[免费注册](https://dashboard.caiyunapp.com/v1/token)） |
| `kindle.host` | Kindle 的局域网 IP 地址 |
| `kindle.ssh_key` | SSH 私钥路径（用于免密登录 Kindle） |
| `kindle.remote_path` | 推送到 Kindle 的目标路径（ScreenSavers Hack 目录） |

#### 4. 设置 SSH 密钥（推荐）

```bash
# 生成密钥对（如果没有的话）
ssh-keygen -t ed25519 -f ~/.ssh/kindle_key -N ""

# 将公钥拷贝到 Kindle
scp -i ~/.ssh/kindle_key.pub root@<KINDLE_IP>:/tmp/authorized_keys_append
ssh root@<KINDLE_IP> 'cat /tmp/authorized_keys_append >> /root/.ssh/authorized_keys && rm /tmp/authorized_keys_append'
```

> 或者使用脚本一键配置：
> ```bash
> bash scripts/setup_kindle_ssh.sh <KINDLE_IP>
> ```

#### 5. 授权 macOS 自动化权限

首次运行时，macOS 会弹出授权对话框，需要允许以下操作：

- **系统偏好设置 → 安全性与隐私 → 完全磁盘访问权限** — 终端 / 你的 Shell 应用
- **系统偏好设置 → 安全性与隐私 → 自动化** — 授予 Python 对日历和提醒事项的访问权限

#### 6. 测试运行

```bash
# 手动生成卡片（仅本地输出，不推送）
python3 scripts/kindle_card.py --config config.local.json

# 生成并推送到 Kindle
python3 scripts/kindle_card.py --config config.local.json --push

# 强制推送（忽略内容变化检测）
python3 scripts/kindle_card.py --config config.local.json --push --force
```

#### 7. 设置定时任务（launchd）

```bash
# 编辑 launchd plist 中的路径
sed -i '' 's|/ABSOLUTE/PATH/TO|'$(pwd)'|g' launchd/com.local.kindle-voyage-card.plist

# 安装定时任务（每 15 分钟执行一次）
bash scripts/install_launchd.sh $(pwd)/config.local.json

# 或手动加载
cp launchd/com.local.kindle-voyage-card.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.local.kindle-voyage-card.plist
```

### 项目结构

```
kindle-voyage-desk-card/
├── config.example.json          # 配置文件模板
├── requirements.txt             # Python 依赖
├── .gitignore                   # Git 忽略规则
├── launchd/
│   └── com.local.kindle-voyage-card.plist   # macOS 定时任务模板
├── references/
│   └── kindle-side-notes.md     # 故障排查与 Kindle 端笔记
└── scripts/
    ├── kindle_card.py           # 核心卡片生成与推送逻辑
    ├── run_card.sh              # launchd 入口脚本（含时段过滤）
    ├── install_launchd.sh       # 一键安装 launchd 定时任务
    ├── setup_kindle_ssh.sh      # 一键配置 Kindle SSH 密钥
    └── check_kindle.sh          # Kindle 网络连通性诊断
```

### 故障排查

#### Kindle 无法连接

```bash
# 诊断网络连通性
bash scripts/check_kindle.sh <KINDLE_IP>

# 常见问题：
# 1. Kindle WiFi 已断开 → 检查 keep-wifi 服务是否运行
# 2. IP 变化 → 路由器绑定 MAC 地址
# 3. SSH 端口未开启 → 在 Kindle 上重启 usbnetwork: /etc/init.d/usbnetwork restart
```

#### 卡片不更新 / 屏保不切换

```bash
# 检查 ScreenSavers Hack 是否正常
ssh root@<KINDLE_IP> 'ls -la /mnt/us/linkss/screensavers/'

# 如果目录不存在，手动创建：
ssh root@<KINDLE_IP> 'mkdir -p /mnt/us/linkss/screensavers'

# 触发屏保刷新（电源键切换）：
ssh root@<KINDLE_IP> 'lipc-set-prop com.lab126.powerd powerButton 1'
```

#### macOS 自动化权限问题

首次运行时如果提示权限错误：

1. 打开 **系统偏好设置 → 安全性与隐私 → 隐私**
2. 找到 **完全磁盘访问权限**，添加 Terminal/iTerm2
3. 找到 **自动化**，勾选 Python 访问日历和提醒事项的权限
4. 重启终端后再次运行

更多故障排查信息请查看 [references/kindle-side-notes.md](references/kindle-side-notes.md)。

### 数据源说明

| 数据 | 来源 | 需要申请 |
|------|------|---------|
| 天气 | [彩云天气 API](https://www.caiyunapp.com/) | ✅ 免费 Token |
| 日程 | Apple Calendar（本地 AppleScript） | ❌ 本地读取 |
| 待办 | Apple Reminders（本地 AppleScript） | ❌ 本地读取 |
| 一言 | [hitokoto.cn](https://hitokoto.cn/) | ❌ 无需申请 |

### 国际用户适配（International Users）

> 本项目默认使用国内服务（彩云天气、一言）。海外用户可参考以下方案替换数据源，需自行修改 `scripts/kindle_card.py` 中的对应函数。

**天气 API 替换：OpenWeatherMap**

[OpenWeatherMap](https://openweathermap.org/api) 提供免费天气数据（免费层 1000 次/天），全球覆盖。

```bash
# 1. 注册获取 API Key（免费）
# https://home.openweathermap.org/api_keys

# 2. 在 config.local.json 中配置
export OWM_API_KEY="your_openweathermap_api_key"
```

修改 `kindle_card.py` 的 `get_weather()` 函数示例：

```python
def get_weather():
    """从 OpenWeatherMap 获取天气"""
    import os
    token = os.environ.get("OWM_API_KEY", "")
    loc = CONFIG["location"]  # 格式: "longitude,latitude"
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

**金句 API 替换：Quotable**

[Quotable API](https://github.com/lukePeavey/quotable) 提供免费英文名言接口，无需 API Key。

```python
def get_hitokoto():
    """从 Quotable 获取随机英文句子"""
    try:
        r = requests.get("https://api.quotable.io/random", timeout=5)
        data = r.json()
        return {"content": data.get("content", ""), "source": data.get("author", "")}
    except Exception:
        return {"content": "The only way to do great work is to love what you do.", "source": "Steve Jobs"}
```

**坐标查询工具**

- [OpenStreetMap Nominatim](https://nominatim.openstreetmap.org/) — 输入地名获取经纬度
- [Google Maps](https://maps.google.com) — 右键地点 → 坐标

---

<div align="center">

### 📖 [Switch to English Version](#english) | [切换到英文版本](#english)

</div>

---

## English

<div align="right">

**[中文](#中文) | [English](#english)**

</div>

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

<div align="center">

### 📖 [返回中文版本](#中文) | [Back to Chinese Version](#中文)

</div>

---

## License

[MIT License](LICENSE)

---

**Note**: This project is for personal learning and educational purposes only. Jailbreaking your Kindle may void its warranty. Use at your own risk.
