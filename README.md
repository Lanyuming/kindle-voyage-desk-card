# Kindle Voyage Desk Card

将越狱的 Kindle Voyage 变成你的桌面信息副屏 —— 自动生成并推送包含天气、日历、待办、一言的墨水屏卡片。

![Kindle Desk Card](https://img.shields.io/badge/Kindle-Voyage-black?style=flat-square&logo=amazon) ![macOS](https://img.shields.io/badge/macOS-13%2B-blue?style=flat-square&logo=apple) ![Python](https://img.shields.io/badge/Python-3.10%2B-green?style=flat-square&logo=python)

## 效果预览

卡片自动生成 1072×1448 像素的 8-bit 灰度 PNG，通过 SSH 推送到 Kindle 的 ScreenSavers Hack 屏保目录，内容包括：

- **天气**：当前温度/体感温度/湿度/AQI + 未来几小时预报 + 出行建议
- **日历**：Apple Calendar 未来 3 天日程（时间、地点）
- **待办**：Apple Reminders 待办事项（区分"今天"和"计划"，显示截止日期）
- **一言**：随机中文句子（hitokoto.cn）
- **日期**：农历日期 + 当前时间

## 兼容性

| 设备 | 支持情况 |
|------|---------|
| Kindle Voyage | ✅ 完美适配（1072×1448） |
| Kindle PaperWhite 3 | ⚠️ 需修改 canvas 尺寸为 758×1024 |
| Kindle Oasis 2/3 | ⚠️ 需修改 canvas 尺寸为 1264×1680 |
| Kindle PaperWhite 4/5 | ⚠️ 需修改 canvas 尺寸为 1072×1448（同 Voyage） |

> 所有已越狱且安装了 ScreenSavers Hack 的 Kindle 均可使用，只需调整 `config.json` 中的 `canvas.width` 和 `canvas.height`。

## Kindle 端前置要求

在开始之前，你的 Kindle 必须完成以下准备：

### 1. 越狱

确保你的 Kindle 已经完成越狱。不同固件版本的越狱方法请参考 [MobileRead Wiki](https://wiki.mobileread.com/wiki/Kindle_Hacks)。

### 2. 必装插件

| 插件 | 用途 | 安装方式 |
|------|------|---------|
| **MRPI** (Package Installer) | 插件安装器 | 通过 USB 拷贝到 Kindle 后安装 |
| **USBNetwork Hack** | 开启 WiFi SSH 连接 | MRPI 安装或手动安装 |
| **ScreenSavers Hack (linkss)** | 自定义屏保图片 | MRPI 安装或手动安装 |
| **File Browser** | Web 文件管理器（备用推送方式） | MRPI 安装 |

### 3. 推荐插件

| 插件 | 用途 |
|------|------|
| KUAL (Kindle Unified Application Launcher) | 插件启动菜单 |
| Fonts Hack | 更换中文字体（如思源黑体） |
| Helper | 小工具集合 |

### 4. 启用 SSH

```bash
# 在 Kindle 上通过 KUAL 或命令行启用 USBNetwork：
# Settings → USB Network → Enable

# 或者在 Kindle 的终端中执行：
/etc/init.d/usbnetwork start
```

### 5. 配置 WiFi 保活（可选但推荐）

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

## macOS 端安装步骤

### 1. 克隆项目

```bash
git clone https://github.com/<your-username>/kindle-voyage-desk-card.git
cd kindle-voyage-desk-card
```

### 2. 创建虚拟环境 & 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

依赖列表：
- `Pillow>=10.0.0` — 图片生成
- `requests>=2.31.0` — HTTP 请求（天气 API）

### 3. 创建配置文件

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
    "longitude": 116.6563,
    "latitude": 39.9087
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

#### 配置项说明

| 字段 | 说明 |
|------|------|
| `canvas.width/height` | 输出图片像素尺寸（匹配你的 Kindle 型号） |
| `location.longitude/latitude` | 天气查询坐标（可在 [彩云天气控制台](https://dashboard.caiyunapp.com/) 获取） |
| `caiyun.token` | 彩云天气 API Token（[免费注册](https://dashboard.caiyunapp.com/v1/token)） |
| `kindle.host` | Kindle 的局域网 IP 地址 |
| `kindle.ssh_key` | SSH 私钥路径（用于免密登录 Kindle） |
| `kindle.remote_path` | 推送到 Kindle 的目标路径（ScreenSavers Hack 目录） |

### 4. 设置 SSH 密钥（推荐）

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

### 5. 授权 macOS 自动化权限

首次运行时，macOS 会弹出授权对话框，需要允许以下操作：

- **系统偏好设置 → 安全性与隐私 → 完全磁盘访问权限** — 终端 / 你的 Shell 应用
- **系统偏好设置 → 安全性与隐私 → 自动化** — 授予 Python 对日历和提醒事项的访问权限

### 6. 测试运行

```bash
# 手动生成卡片（仅本地输出，不推送）
python3 scripts/kindle_card.py --config config.local.json

# 生成并推送到 Kindle
python3 scripts/kindle_card.py --config config.local.json --push

# 强制推送（忽略内容变化检测）
python3 scripts/kindle_card.py --config config.local.json --push --force
```

### 7. 设置定时任务（launchd）

```bash
# 编辑 launchd plist 中的路径
sed -i '' 's|/ABSOLUTE/PATH/TO|'$(pwd)'|g' launchd/com.local.kindle-voyage-card.plist

# 安装定时任务（每 15 分钟执行一次）
bash scripts/install_launchd.sh $(pwd)/config.local.json

# 或手动加载
cp launchd/com.local.kindle-voyage-card.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.local.kindle-voyage-card.plist
```

## 项目结构

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

## 故障排查

### Kindle 无法连接

```bash
# 诊断网络连通性
bash scripts/check_kindle.sh <KINDLE_IP>

# 常见问题：
# 1. Kindle WiFi 已断开 → 检查 keep-wifi 服务是否运行
# 2. IP 变化 → 路由器绑定 MAC 地址
# 3. SSH 端口未开启 → 在 Kindle 上重启 usbnetwork: /etc/init.d/usbnetwork restart
```

### 卡片不更新 / 屏保不切换

```bash
# 检查 ScreenSavers Hack 是否正常
ssh root@<KINDLE_IP> 'ls -la /mnt/us/linkss/screensavers/'

# 如果目录不存在，手动创建：
ssh root@<KINDLE_IP> 'mkdir -p /mnt/us/linkss/screensavers'

# 触发屏保刷新（电源键切换）：
ssh root@<KINDLE_IP> 'lipc-set-prop com.lab126.powerd powerButton 1'
```

### macOS 自动化权限问题

首次运行时如果提示权限错误：

1. 打开 **系统偏好设置 → 安全性与隐私 → 隐私**
2. 找到 **完全磁盘访问权限**，添加 Terminal/iTerm2
3. 找到 **自动化**，勾选 Python 访问日历和提醒事项的权限
4. 重启终端后再次运行

更多故障排查信息请查看 [references/kindle-side-notes.md](references/kindle-side-notes.md)。

## 数据源说明

| 数据 | 来源 | 需要申请 |
|------|------|---------|
| 天气 | [彩云天气 API](https://www.caiyunapp.com/) | ✅ 免费 Token |
| 日程 | Apple Calendar（本地 AppleScript） | ❌ 本地读取 |
| 待办 | Apple Reminders（本地 AppleScript） | ❌ 本地读取 |
| 一言 | [hitokoto.cn](https://hitokoto.cn/) | ❌ 无需申请 |

## License

MIT License

---

**注意**：本项目仅供个人学习交流使用。Kindle 越狱可能影响设备保修，请自行承担风险。
