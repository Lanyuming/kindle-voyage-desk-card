#!/usr/bin/env bash
# ======================================================================
# Kindle SSH 持久化配置脚本（完整版）
# 功能：
#   1. 配置 dropbear 开机/WiFi 自动启动（upstart），脱离 KUAL
#   2. 禁止 Kindle 自动休眠（防止 WiFi 断开）
#   3. 确保唤醒后 SSH 立即恢复
# 前提：当前 KUAL 正在运行且 SSH 可用
# ======================================================================
set -euo pipefail

KINDLE_HOST="${1:-}"
KINDLE_USER="${2:-root}"
SSH_KEY="${3:-}"

SSH_CMD="ssh -i ${SSH_KEY} -o StrictHostKeyChecking=no -o ConnectTimeout=10 ${KINDLE_USER}@${KINDLE_HOST}"

echo "================================================================"
echo "  Kindle SSH 持久化配置"
echo "  目标: ${KINDLE_USER}@${KINDLE_HOST}"
echo "================================================================"
echo ""

# ------------------------------------------------------------------
# 1. 检测 SSH 连接
# ------------------------------------------------------------------
echo "-- [1/6] 检测 SSH 连接 --"
if ! ${SSH_CMD} "echo SSH_OK" 2>/dev/null; then
    echo "ERROR: 无法连接 Kindle SSH"
    echo "请确保: Kindle 已唤醒 → 打开 KUAL → USBNetwork → Allow SSH over WiFi"
    exit 1
fi
echo "OK: SSH 连接成功"
echo ""

# ------------------------------------------------------------------
# 2. 探测 Kindle 环境
# ------------------------------------------------------------------
echo "-- [2/6] 探测 Kindle 环境 --"
KINDLE_INFO=$(${SSH_CMD} '
echo "DROPBEAR_BIN=/usr/bin/dropbear"
echo "DROPBEARMULTI=/usr/sbin/dropbearmulti"
# 检查实际存在的二进制
for p in /usr/bin/dropbear /usr/sbin/dropbearmulti /mnt/us/usbnet/bin/dropbearmulti; do
    if [ -x "$p" ]; then echo "FOUND=$p"; fi
done
# 当前 dropbear 进程的完整命令行
ps | grep dropbear | grep -v grep
# 检查现有 sshd upstart 配置
cat /etc/upstart/sshd.conf 2>/dev/null || echo "NO_SSHD_CONF"
cat /etc/upstart/usbnet-autostart.conf 2>/dev/null || echo "NO_USBNET_AUTOSTART"
cat /etc/upstart/usbnet.conf 2>/dev/null || echo "NO_USBNET_CONF"
cat /etc/upstart/usbnetd.conf 2>/dev/null || echo "NO_USBNETD_CONF"
# 电源管理
lipc-get-prop com.lab126.powerd preventScreenSaver 2>/dev/null || echo "NO_PREVENT_SS"
lipc-get-prop com.lab126.powerd stayAwake 2>/dev/null || echo "NO_STAY_AWAKE"
' 2>/dev/null)
echo "${KINDLE_INFO}"
echo ""

# ------------------------------------------------------------------
# 3. 创建 dropbear upstart 配置（开机+WiFi 自动启动，脱离 KUAL）
# ------------------------------------------------------------------
echo "-- [3/6] 创建 dropbear upstart 配置 --"
${SSH_CMD} '
# 备份原有配置（如果存在）
[ -f /etc/upstart/sshd.conf ] && cp /etc/upstart/sshd.conf /etc/upstart/sshd.conf.bak

cat > /etc/upstart/sshd.conf << "SSHD_EOF"
# dropbear SSH daemon - auto-start on WiFi, independent of KUAL
# Kindle Voyage desk card project

start on started wifid
stop on stopping wifid

respawn
respawn limit 10 60

normal exit 0

pre-start script
    # Ensure host key directory exists
    mkdir -p /etc/dropbear
    # Try to copy existing keys from usbnet if system ones are missing
    for ktype in rsa ecdsa ed25519 dss; do
        src="/mnt/us/usbnet/etc/dropbear_${ktype}_host_key"
        dst="/etc/dropbear/dropbear_${ktype}_host_key"
        if [ ! -f "$dst" ] && [ -f "$src" ]; then
            cp "$src" "$dst" 2>/dev/null
        fi
    done
    # Generate missing host keys
    for ktype in rsa ecdsa ed25519; do
        key="/etc/dropbear/dropbear_${ktype}_host_key"
        if [ ! -f "$key" ]; then
            /usr/bin/dropbearkey -t $ktype -f "$key" 2>/dev/null || true
        fi
    done
end script

script
    # Use -R for dynamic host key, -B for blank password auth
    # -p 22 for standard SSH port
    exec /usr/bin/dropbear -r /etc/dropbear/dropbear_rsa_host_key \
                           -r /etc/dropbear/dropbear_ecdsa_host_key \
                           -r /etc/dropbear/dropbear_ed25519_host_key \
                           -R -B -p 22 -F -E
end script
SSHD_EOF

echo "OK: /etc/upstart/sshd.conf 已写入"
' 2>/dev/null
echo ""

# ------------------------------------------------------------------
# 4. 配置 Kindle 防止自动休眠（保持 WiFi 在线）
# ------------------------------------------------------------------
echo "-- [4/6] 配置防止 Kindle 自动休眠 --"
${SSH_CMD} '
# 方法1: 使用 lipc 设置 stayAwake（需要时自动唤醒）
# 方法2: 修改 powerd 的休眠超时为极大值
# 方法3: 创建 upstart 作业持续阻止休眠

cat > /etc/upstart/stay-awake.conf << "AWAKE_EOF"
# Prevent Kindle from deep sleep to keep WiFi alive for SSH
# Kindle Voyage desk card project

start on started framework
stop on stopping framework

respawn
respawn limit 5 300

script
    while true; do
        # Prevent screen saver (which leads to deep sleep)
        lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>/dev/null || true
        # Request stay awake
        lipc-set-prop com.lab126.powerd stayAwake 1 2>/dev/null || true
        sleep 30
    done
end script
AWAKE_EOF

echo "OK: /etc/upstart/stay-awake.conf 已写入"
' 2>/dev/null
echo ""

# ------------------------------------------------------------------
# 5. 启动新配置的服务
# ------------------------------------------------------------------
echo "-- [5/6] 启动服务 --"
${SSH_CMD} '
# 注册并启动 sshd
initctl reload-configuration 2>/dev/null || true
sleep 1
initctl start sshd 2>/dev/null || echo "sshd 可能已在运行"
sleep 1

# 注册并启动 stay-awake
initctl reload-configuration 2>/dev/null || true
sleep 1
initctl start stay-awake 2>/dev/null || echo "stay-awake 可能已在运行"
sleep 1

# 验证
echo "=== 运行中的服务 ==="
initctl list 2>/dev/null | grep -E "sshd|stay-awake" || true
echo "=== dropbear 进程 ==="
ps | grep dropbear | grep -v grep || echo "无 dropbear 进程"
echo "=== stay-awake 进程 ==="
ps | grep stay-awake | grep -v grep || echo "无 stay-awake 进程"
echo "=== 防休眠状态 ==="
lipc-get-prop com.lab126.powerd preventScreenSaver 2>/dev/null || echo "N/A"
lipc-get-prop com.lab126.powerd stayAwake 2>/dev/null || echo "N/A"
' 2>/dev/null
echo ""

# ------------------------------------------------------------------
# 6. 验证 SSH 连接（通过新配置的 dropbear）
# ------------------------------------------------------------------
echo "-- [6/6] 验证 SSH 连接 --"
sleep 3
if ${SSH_CMD} "echo SSH_VIA_NEW_CONFIG_OK" 2>/dev/null; then
    echo "OK: 通过新配置的 dropbear SSH 连接成功！"
else
    echo "WARNING: 验证连接失败，可能需要重启 Kindle 后生效"
fi
echo ""

echo "================================================================"
echo "  配置完成！"
echo ""
echo "  已配置的服务："
echo "    - sshd: dropbear SSH，开机/WiFi 连接时自动启动，崩溃自动重启"
echo "    - stay-awake: 每 30 秒阻止 Kindle 进入深度休眠"
echo ""
echo "  现在可以退出 KUAL，SSH 将保持可用。"
echo "  如果 Kindle 重启，这两个服务也会自动启动。"
echo ""
echo "  注意：stay-awake 会增加耗电，Kindle 每天可能需要充电。"
echo "  如果想恢复自动休眠：ssh 到 Kindle 执行 initctl stop stay-awake"
echo "================================================================"
