#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kindle Voyage 桌面副屏卡片生成器

数据源：
- 天气 API：彩云天气（中国）/ OpenWeatherMap（国际）
- Apple Calendar（AppleScript，需授权自动化权限）
- Apple Reminders（AppleScript，需授权自动化权限）
- 一言 API（hitokoto.cn）/ Quotable API（国际）

输出：1072x1448 8-bit 灰度 PNG
"""

import os
import sys
import json
import datetime
import requests
import subprocess
import math
import hashlib
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ======================================================================
# 配置区
# ======================================================================
CONFIG = {
    "width": 1072,
    "height": 1448,
    "margin": 48,
    "card_padding": 40,
    "card_gap": 32,
    "card_radius": 16,
    "safe_margin": 40,
    "caiyun_token": "",
    "caiyun_token_env": "CAIYUN_TOKEN",
    "location": "",
    "font_regular": "/System/Library/Fonts/PingFang.ttc",
    "font_bold": "/System/Library/Fonts/PingFang.ttc",
    "font_light": "/System/Library/Fonts/PingFang.ttc",
    "output_path": "out/bg_ss00.png",
    "hash_path": "out/.data_hash",
    "kindle": {
        "host": "",
        "user": "root",
        "remote_path": "/mnt/us/linkss/screensavers/bg_ss00.png",
        "ssh_key": "",
        "ignore_push_errors": True,
        "filebrowser": {
            "url": "",
            "remote_path": "/mnt/us/linkss/screensavers/bg_ss00.png",
            "timeout_seconds": 10,
            "auth": {
                "username": "",
                "password": ""
            },
            "bind_address": "",
            "port": 80
        }
    },
    "calendar_names": ["日历", "个人"],
    "calendar_days": 3,
    "max_events": 8,
    "max_reminders": 7,
}

# ======================================================================
# 天气 skycon 中文映射
# ======================================================================
SKYCON_MAP = {
    "CLEAR_DAY": ("晴", "*"),
    "CLEAR_NIGHT": ("晴", "*"),
    "PARTLY_CLOUDY_DAY": ("多云", "o"),
    "PARTLY_CLOUDY_NIGHT": ("多云", "o"),
    "CLOUDY": ("阴", "O"),
    "LIGHT_RAIN": ("小雨", "/"),
    "MODERATE_RAIN": ("中雨", "//"),
    "HEAVY_RAIN": ("大雨", "///"),
    "EXTREME_RAIN": ("暴雨", "////"),
    "THUNDER_RAIN": ("雷阵雨", "!/"),
    "LIGHT_SNOW": ("小雪", "*"),
    "MODERATE_SNOW": ("中雪", "**"),
    "HEAVY_SNOW": ("大雪", "***"),
    "EXTREME_SNOW": ("暴雪", "****"),
    "SLEET": ("雨夹雪", "*/"),
    "LIGHT_HAIL": ("小冰雹", "o/"),
    "HEAVY_HAIL": ("大冰雹", "O/"),
    "FOG": ("雾", "~"),
    "LIGHT_HAZE": ("轻度霾", "~"),
    "MODERATE_HAZE": ("中度霾", "~~"),
    "HEAVY_HAZE": ("重度霾", "~~~"),
    "WIND": ("大风", ">"),
}

def generate_suggestion(temp, apparent, skycon, aqi, humidity):
    """根据实际天气数据生成简短、活泼的出行建议"""
    tips = []
    # 温度建议
    if apparent <= 0:
        tips.append("冻哭！羽绒服帽子围巾全副武装")
    elif apparent <= 5:
        tips.append("太冷了！厚外套+毛衣走起")
    elif apparent <= 10:
        tips.append("有点冷，记得加件外套")
    elif apparent <= 15:
        tips.append("微凉，薄外套或长袖刚好")
    elif apparent <= 25:
        tips.append("体感舒适，随便穿都好看")
    elif apparent <= 30:
        tips.append("有点热了，短袖安排上")
    else:
        tips.append("热化了！防晒+多喝水")
    # 天气建议
    rain_types = ["小雨", "中雨", "大雨", "暴雨", "雷阵雨", "雨夹雪"]
    snow_types = ["小雪", "中雪", "大雪", "暴雪"]
    if any(r in skycon for r in rain_types):
        tips.append("记得带伞！")
    elif any(s in skycon for s in snow_types):
        tips.append("下雪路滑，出门小心")
    elif "霾" in skycon:
        tips.append("空气差，戴好口罩")
    elif "雾" in skycon:
        tips.append("雾大能见度低，开车注意安全")
    # AQI 建议
    if isinstance(aqi, int):
        if aqi > 150:
            tips.append("AQI爆表，尽量别出门")
        elif aqi > 100:
            tips.append("AQI偏高，敏感人群戴口罩")
    return "，".join(tips[:2]) + "！" if tips else "今天适合出门溜达~"


# ======================================================================
# 数据采集函数
# ======================================================================

def get_lunar_date():
    """获取农历日期"""
    try:
        from lunar_python import Lunar
        lunar = Lunar.fromDate(datetime.datetime.now())
        return f"{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}"
    except ImportError:
        pass
    return ""


def get_weather():
    """从彩云天气 API 获取实时天气数据"""
    token = CONFIG.get("caiyun_token", "")
    token_env = CONFIG.get("caiyun_token_env", "CAIYUN_TOKEN")
    if not token and token_env:
        token = os.environ.get(token_env, "")
    url = f"https://api.caiyunapp.com/v2.5/{token}/{CONFIG['location']}/weather.json"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        realtime = data['result']['realtime']
        skycon = realtime.get('skycon', 'CLEAR_DAY')
        desc_cn, icon = SKYCON_MAP.get(skycon, ("未知", "?"))
        aqi_val = realtime['air_quality']['aqi']['chn']
        apparent_val = int(realtime['apparent_temperature'])
        suggestion = generate_suggestion(
            int(realtime['temperature']), apparent_val, desc_cn, aqi_val,
            int(realtime['humidity'] * 100)
        )
        return {
            "temp": int(realtime['temperature']),
            "desc": desc_cn,
            "icon": icon,
            "humidity": f"{int(realtime['humidity'] * 100)}%",
            "wind": f"{realtime['wind']['speed']:.0f}km/h",
            "aqi": aqi_val,
            "apparent": apparent_val,
            "suggestion": suggestion
        }
    except Exception:
        return {
            "temp": 22, "desc": "多云", "icon": "o",
            "humidity": "45%", "wind": "12km/h", "aqi": 45,
            "apparent": 20, "suggestion": "体感舒适，随便穿都好看！"
        }


def get_calendar_events():
    """获取 Apple Calendar 近期日程（通过 AppleScript）"""
    cal_names = CONFIG.get("calendar_names", ["日历", "个人"])
    cal_names_js = ", ".join(f'"{c}"' for c in cal_names)
    script = f'''
tell application "Calendar"
    set today to current date
    set todayTime to time of today
    set today to today - todayTime
    set threeDaysLater to today + (3 * days)
    set output to ""
    repeat with calName in {{{cal_names_js}}}
        try
            set cal to calendar calName
            set evts to (every event of cal whose start date ≥ today and start date ≤ threeDaysLater)
            repeat with evt in evts
                set evtDate to start date of evt
                set m to (month of evtDate as integer)
                set d to (day of evtDate as integer)
                set h to hours of evtDate
                set mi to minutes of evtDate
                set padH to text -2 thru -1 of ("0" & h)
                set padM to text -2 thru -1 of ("0" & mi)
                set timeStr to ("" & m & "/" & d & " " & padH & ":" & padM)
                set output to output & timeStr & " | " & (summary of evt) & linefeed
            end repeat
        end try
    end repeat
    return output
end tell
'''
    try:
        output = subprocess.check_output(
            ["osascript", "-e", script],
            stderr=subprocess.PIPE, timeout=30
        ).decode('utf-8')
        items = [line.strip() for line in output.strip().split('\n') if line.strip()]
        if items:
            return items[:6]
    except subprocess.CalledProcessError as e:
        print(f"  Calendar AppleScript error: {e.stderr.decode('utf-8', errors='replace')[:200]}")
    except Exception as e:
        print(f"  Calendar error: {e}")
    return ["暂无近期日程"]


def get_reminders():
    """获取 Apple Reminders 今天到期 + 近7天计划的未完成事项（via EventKit）"""
    script = '''
use framework "Foundation"
use framework "EventKit"

set store to current application's EKEventStore's alloc's init()
set predicate to store's predicateForRemindersInCalendars:(missing value)
set allReminders to store's remindersMatchingPredicate:predicate

set output to ""
set cnt to 0
set df to current application's NSDateFormatter's alloc's init()
df's setDateFormat:"yyyy-MM-dd"

repeat with rem in allReminders
    if (rem's completed) as boolean is false then
        set dueDate to rem's dueDate()
        if dueDate is not missing value then
            set dueStr to (df's stringFromDate:dueDate) as text
            set output to output & dueStr & "|" & ((rem's title()) as text) & linefeed
            set cnt to cnt + 1
            if cnt ≥ 20 then exit repeat
        end if
    end if
end repeat

return output
'''
    try:
        output = subprocess.check_output(
            ["osascript", "-e", script],
            stderr=subprocess.PIPE, timeout=30
        ).decode('utf-8')
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        from datetime import timedelta
        week_later = (datetime.datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        today_items = []
        upcoming_items = []
        for line in output.strip().split('\n'):
            if '|' not in line:
                continue
            due_str, title = line.strip().split('|', 1)
            if due_str == today:
                today_items.append(title)
            elif today < due_str <= week_later:
                upcoming_items.append((due_str, title))
        upcoming_items.sort(key=lambda x: x[0])
        result = []
        for t in today_items:
            result.append(("●", t, None))
        for d, t in upcoming_items:
            result.append(("○", t, d))
        if result:
            return result[:5]
    except subprocess.CalledProcessError as e:
        print(f"  Reminders AppleScript error: {e.stderr.decode('utf-8', errors='replace')[:200]}")
    except Exception as e:
        print(f"  Reminders error: {e}")
    return []


def get_hitokoto():
    """从一言 API 获取随机句子，返回 {content, source}"""
    try:
        r = requests.get("https://v1.hitokoto.cn/?encode=json", timeout=5)
        data = r.json()
        return {
            "content": data.get('hitokoto', ''),
            "source": data.get('from', '')
        }
    except Exception:
        return {
            "content": "心之所向，素履以往。生如逆旅，一苇以航。",
            "source": "七堇年"
        }


# ======================================================================
# 绘图组件
# ======================================================================

LAYOUT = {
    "color_black": 0,
    "color_white": 255,
    "color_gray": 128,
}


def _draw_rounded_card(draw, x, y, w, h, radius=16):
    draw.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=LAYOUT["color_white"], outline=LAYOUT["color_black"], width=3)


def _draw_calendar_icon(draw, x, y, size=28):
    draw.rounded_rectangle([x, y, x + size, y + size], radius=5, outline=LAYOUT["color_black"], width=3)
    draw.line([(x + 7, y), (x + 7, y - 7)], fill=LAYOUT["color_black"], width=3)
    draw.line([(x + size - 7, y), (x + size - 7, y - 7)], fill=LAYOUT["color_black"], width=3)
    draw.line([(x + 5, y + 10), (x + size - 5, y + 10)], fill=LAYOUT["color_black"], width=2)


def _draw_location_icon(draw, x, y, size=28):
    r = size // 2
    cx, cy = x + r, y + r
    draw.ellipse([cx - r, cy - r, cx + r, cy], outline=LAYOUT["color_black"], width=3)
    draw.line([(cx, cy), (cx, cy + r)], fill=LAYOUT["color_black"], width=3)
    draw.ellipse([cx - 3, cy + r - 2, cx + 3, cy + r + 4], fill=LAYOUT["color_black"])


def _draw_sun_icon(draw, cx, cy, r=36):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=LAYOUT["color_black"], width=4)
    ray_inner = r + 6
    ray_outer = r + 20
    for angle in range(0, 360, 45):
        rad = math.radians(angle)
        x1 = cx + ray_inner * math.cos(rad)
        y1 = cy + ray_inner * math.sin(rad)
        x2 = cx + ray_outer * math.cos(rad)
        y2 = cy + ray_outer * math.sin(rad)
        draw.line([(x1, y1), (x2, y2)], fill=LAYOUT["color_black"], width=4)


def _draw_cloud_icon(draw, cx, cy, r=30):
    draw.ellipse([cx - r * 0.6, cy - r * 0.3, cx + r * 0.6, cy + r * 0.3], outline=LAYOUT["color_black"], width=4)
    draw.ellipse([cx - r * 1.1, cy - r * 0.1, cx - r * 0.1, cy + r * 0.7], outline=LAYOUT["color_black"], width=4)
    draw.ellipse([cx + r * 0.1, cy - r * 0.1, cx + r * 1.1, cy + r * 0.7], outline=LAYOUT["color_black"], width=4)
    draw.line([(cx - r * 1.1, cy + r * 0.3), (cx + r * 1.1, cy + r * 0.3)], fill=LAYOUT["color_white"], width=6)
    draw.line([(cx - r * 1.05, cy + r * 0.35), (cx + r * 1.05, cy + r * 0.35)], fill=LAYOUT["color_black"], width=4)


def _draw_rain_icon(draw, cx, cy, r=30):
    _draw_cloud_icon(draw, cx, cy - 10, r)
    for i in range(3):
        dx = cx - 15 + i * 15
        draw.line([(dx, cy + 15), (dx - 5, cy + 28)], fill=LAYOUT["color_black"], width=3)


def _draw_snow_icon(draw, cx, cy, r=30):
    _draw_cloud_icon(draw, cx, cy - 10, r)
    for i in range(3):
        dx = cx - 15 + i * 15
        draw.ellipse([dx - 3, cy + 15, dx + 3, cy + 21], fill=LAYOUT["color_black"])


def _draw_weather_icon(draw, cx, cy, skycon, r=36):
    desc_cn = skycon
    if "晴" in desc_cn:
        _draw_sun_icon(draw, cx, cy, r)
    elif "雨" in desc_cn:
        _draw_rain_icon(draw, cx, cy, r)
    elif "雪" in desc_cn:
        _draw_snow_icon(draw, cx, cy, r)
    elif "云" in desc_cn or "阴" in desc_cn:
        _draw_cloud_icon(draw, cx, cy, r)
    else:
        _draw_sun_icon(draw, cx, cy, r)


def _draw_clock_icon(draw, x, y, size=28):
    r = size // 2
    cx, cy = x + r, y + r
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=LAYOUT["color_black"], width=3)
    draw.line([(cx, cy), (cx - r * 0.4, cy - r * 0.5)], fill=LAYOUT["color_black"], width=3)
    draw.line([(cx, cy), (cx + r * 0.6, cy - r * 0.3)], fill=LAYOUT["color_black"], width=2)


def _draw_lightbulb_icon(draw, x, y, size=32):
    r = size // 2
    cx, cy = x + r, y + r - 3
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=LAYOUT["color_black"], width=3)
    draw.line([(cx - 4, cy - 6), (cx + 2, cy), (cx - 2, cy), (cx + 4, cy + 6)], fill=LAYOUT["color_black"], width=2)
    base_y = cy + r + 2
    draw.line([(cx - r + 5, base_y), (cx + r - 5, base_y)], fill=LAYOUT["color_black"], width=3)
    draw.line([(cx - r + 5, base_y + 5), (cx + r - 5, base_y + 5)], fill=LAYOUT["color_black"], width=3)


def _draw_checklist_icon(draw, x, y, size=28):
    line_w = size - 8
    y_start = y + 6
    for i in range(3):
        y_pos = y_start + i * 8
        draw.line([(x + 4, y_pos), (x + 4 + line_w, y_pos)], fill=LAYOUT["color_black"], width=3)


def _draw_checkbox(draw, x, y, size=24):
    draw.rectangle([x, y, x + size, y + size], outline=LAYOUT["color_black"], width=3)


def _draw_bullet(draw, x, y, size=12):
    draw.ellipse([x, y, x + size, y + size], fill=LAYOUT["color_black"])


def _wrap_text(text, font, max_width, draw):
    if not text or max_width <= 0:
        return [text]
    lines = []
    current = ""
    for char in text:
        test = current + char
        if draw.textlength(test, font=font) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines if lines else [text]


def _truncate_text(text, font, max_width, draw):
    if draw.textlength(text, font=font) <= max_width:
        return text
    for i in range(len(text) - 1, 0, -1):
        test = text[:i] + "…"
        if draw.textlength(test, font=font) <= max_width:
            return test
    return "…"


def _auto_scale_font(text, base_size, max_width, draw, weight="regular"):
    for size in range(base_size, 16 - 1, -2):
        font = ImageFont.truetype(CONFIG[f"font_{weight}"], size)
        if draw.textlength(text, font=font) <= max_width:
            return font, size
    font = ImageFont.truetype(CONFIG[f"font_{weight}"], 16)
    return font, 16


# ======================================================================
# 主渲染函数
# ======================================================================

def render():
    img = Image.new("L", (CONFIG["width"], CONFIG["height"]), LAYOUT["color_white"])
    draw = ImageDraw.Draw(img)

    f_huge = ImageFont.truetype(CONFIG["font_bold"], 80)
    f_title = ImageFont.truetype(CONFIG["font_bold"], 64)
    f_subtitle = ImageFont.truetype(CONFIG["font_bold"], 32)
    f_body = ImageFont.truetype(CONFIG["font_regular"], 28)
    f_caption = ImageFont.truetype(CONFIG["font_regular"], 24)
    f_small = ImageFont.truetype(CONFIG["font_light"], 20)

    weather = get_weather()
    events = get_calendar_events()
    quote = get_hitokoto()
    reminders = get_reminders()

    M = CONFIG["margin"]
    PAD = CONFIG["card_padding"]
    GAP = CONFIG["card_gap"]
    CW = CONFIG["width"] - 2 * M

    # ==================== 1. 天气卡片 ====================
    card_y = 40
    card_h = 400
    _draw_rounded_card(draw, M, card_y, CW, card_h, CONFIG["card_radius"])

    cx = M + PAD
    cy = card_y + PAD
    cw = CW - 2 * PAD

    y = cy
    _draw_calendar_icon(draw, cx, y, size=28)
    draw.text((cx + 32, y), f"农历{get_lunar_date()}", font=f_small, fill=LAYOUT["color_black"])

    loc_name = CONFIG.get("location_name", "")
    loc_w = draw.textlength(loc_name, font=f_small)
    loc_icon_x = M + CW - PAD - loc_w - 32
    _draw_location_icon(draw, loc_icon_x, y, size=28)
    draw.text((loc_icon_x + 32, y), loc_name, font=f_small, fill=LAYOUT["color_black"])

    y += 64
    draw.text((cx, y), "今天", font=f_title, fill=LAYOUT["color_black"])

    y += 80
    now = datetime.datetime.now()
    weekdays = ["一", "二", "三", "四", "五", "六", "日"]
    date_text = f"{now.month}月{now.day}日 · 星期{weekdays[now.weekday()]}"
    draw.text((cx, y), date_text, font=f_caption, fill=LAYOUT["color_black"])

    sun_cx = cx + 420
    sun_cy = card_y + 140
    _draw_weather_icon(draw, sun_cx, sun_cy, weather["desc"], r=36)

    temp_text = f"{weather['temp']}°C"
    temp_w = draw.textlength(temp_text, font=f_huge)
    temp_x = sun_cx + 80
    temp_y = sun_cy - 40
    draw.text((temp_x, temp_y), temp_text, font=f_huge, fill=LAYOUT["color_black"])

    status_x = temp_x + temp_w + 24
    draw.text((status_x, sun_cy - 20), weather["desc"], font=f_subtitle, fill=LAYOUT["color_black"])

    y = card_y + 240
    detail_text = f"体感 {weather['apparent']}° | 湿度 {weather['humidity']} | 风 {weather['wind']} | AQI {weather['aqi']}"
    detail_w = draw.textlength(detail_text, font=f_caption)
    draw.text((M + CW - PAD - detail_w, y), detail_text, font=f_caption, fill=LAYOUT["color_black"])

    y = card_y + 300
    _draw_lightbulb_icon(draw, cx, y, size=32)
    advice_x = cx + 44
    advice_max_w = M + CW - CONFIG["safe_margin"] - advice_x
    advice_text = weather["suggestion"]
    if len(advice_text) <= 10:
        advice_text = "天气舒适，适合户外活动。"
    advice_lines = _wrap_text(advice_text, f_caption, advice_max_w, draw)
    for i, line in enumerate(advice_lines[:2]):
        draw.text((advice_x, y + i * 42), line, font=f_caption, fill=LAYOUT["color_gray"])

    # ==================== 2. 中部分栏：日程 + 金句 ====================
    mid_y = card_y + card_h + GAP

    sched_w = 450
    sched_h = 520
    sched_x = M
    _draw_rounded_card(draw, sched_x, mid_y, sched_w, sched_h, CONFIG["card_radius"])

    sx = sched_x + PAD
    sy = mid_y + PAD

    _draw_clock_icon(draw, sx, sy, size=28)
    draw.text((sx + 36, sy), "近期日程", font=f_subtitle, fill=LAYOUT["color_black"])

    sy += 64
    line_h = 42
    max_title_w = sched_w - 2 * PAD - 32

    for item in events:
        if sy + line_h * 2 > mid_y + sched_h - CONFIG["safe_margin"]:
            break
        _draw_bullet(draw, sx, sy + 8, size=12)
        if " | " in item:
            time_part, title_part = item.split(" | ", 1)
            draw.text((sx + 24, sy), time_part, font=f_caption, fill=LAYOUT["color_black"])
            sy += line_h
            title = _truncate_text(title_part, f_caption, max_title_w, draw)
            draw.text((sx + 24, sy), title, font=f_caption, fill=LAYOUT["color_black"])
        else:
            title = _truncate_text(item, f_caption, max_title_w, draw)
            draw.text((sx + 24, sy), title, font=f_caption, fill=LAYOUT["color_black"])
        sy += line_h + 8

    quote_w = CW - sched_w - GAP
    quote_x = sched_x + sched_w + GAP
    _draw_rounded_card(draw, quote_x, mid_y, quote_w, sched_h, CONFIG["card_radius"])

    qx = quote_x + PAD
    qy = mid_y + PAD

    quote_font = ImageFont.truetype(CONFIG["font_bold"], 56)
    _, _, qw, qh = draw.textbbox((0, 0), "\u201c", font=quote_font)
    draw.text((qx, qy + 96 - qh), "\u201c", font=quote_font, fill=LAYOUT["color_black"])

    qy += 96
    quote_max_w = quote_w - 2 * PAD - 24
    quote_content = quote["content"] if isinstance(quote, dict) else quote
    quote_lines = _wrap_text(quote_content, f_body, quote_max_w, draw)
    _punct_set = set("，。！？；：……、""''「」『』【】《》〈〉")
    for line in quote_lines[:4]:
        cx = qx + 24
        for ch in line:
            cw = draw.textlength(ch, font=f_body)
            cy_offset = 0
            if ch in _punct_set:
                _, pd = f_body.getmetrics()
                cy_offset = int(pd * 0.6)
            draw.text((cx, qy + cy_offset), ch, font=f_body, fill=LAYOUT["color_black"])
            cx += cw
        qy += 49

    qy += 24
    quote_source = quote.get("source", "") if isinstance(quote, dict) else ""
    if quote_source:
        source_text = f"\u2014\u2014 {quote_source}"
        source_w = draw.textlength(source_text, font=f_caption)
        draw.text((quote_x + quote_w - PAD - source_w, qy), source_text, font=f_caption, fill=LAYOUT["color_black"])

    # ==================== 3. 底部待办卡片 ====================
    todo_y = mid_y + sched_h + GAP
    todo_h = 400
    _draw_rounded_card(draw, M, todo_y, CW, todo_h, CONFIG["card_radius"])

    tx = M + PAD
    ty = todo_y + PAD

    _draw_checklist_icon(draw, tx, ty, size=28)
    draw.text((tx + 36, ty), "待办事项", font=f_subtitle, fill=LAYOUT["color_black"])

    ty += 64
    todo_max_w = CW - 2 * PAD - 60

    today_header_shown = False
    plan_header_shown = False
    for item in reminders:
        if ty + 28 > todo_y + todo_h - CONFIG["safe_margin"]:
            break
        marker, display_text, due_date = item
        if marker == "●":
            if not today_header_shown:
                draw.text((tx, ty), "今天", font=f_caption, fill=LAYOUT["color_gray"])
                ty += 36
                today_header_shown = True
        elif marker == "○":
            if not plan_header_shown:
                draw.text((tx, ty), "计划", font=f_caption, fill=LAYOUT["color_gray"])
                ty += 36
                plan_header_shown = True
        _draw_checkbox(draw, tx, ty + 4, size=24)
        todo_lines = _wrap_text(display_text, f_body, todo_max_w, draw)
        for i, line in enumerate(todo_lines):
            draw.text((tx + 36, ty + i * 49), line, font=f_body, fill=LAYOUT["color_black"])
        if due_date and marker == "○":
            date_label = due_date[5:]
            date_w = draw.textlength(date_label, font=f_small)
            draw.text((tx + CW - 2 * PAD - date_w, ty + 4), date_label, font=f_small, fill=LAYOUT["color_gray"])
        ty += len(todo_lines) * 49 + 16

    if not reminders:
        draw.text((tx + 36, ty), "暂无待办事项", font=f_body, fill=LAYOUT["color_gray"])

    # ==================== 4. Footer ====================
    footer_text = f"更新于 {now.strftime('%Y-%m-%d %H:%M')}  ·  Kindle Voyage Desk Card"
    footer_w = draw.textlength(footer_text, font=f_small)
    draw.text(((CONFIG["width"] - footer_w) // 2, CONFIG["height"] - 60), footer_text, font=f_small, fill=LAYOUT["color_black"])

    img.save(CONFIG["output_path"])
    print(f"Success: {CONFIG['output_path']}")


def _fb_get_token(fb_url, fb_auth, fb_timeout):
    try:
        auth_url = f"{fb_url}/api/login"
        resp = requests.post(auth_url, json=fb_auth, timeout=fb_timeout)
        if resp.status_code == 200:
            token = resp.text.strip().strip('"')
            print(f"  FileBrowser auth OK")
            return token
        else:
            print(f"  FileBrowser auth failed: {resp.status_code}")
    except Exception as e:
        print(f"  FileBrowser auth error: {e}")
    return None


def _fb_upload_script(fb_base, token, fb_timeout, remote_path, script_content):
    headers = {"Content-Type": "application/octet-stream"}
    if token:
        headers["X-Auth"] = token
    api_path = remote_path.lstrip("/")
    put_url = f"{fb_base}/api/resources/{api_path}?override=true"
    try:
        resp = requests.put(put_url, data=script_content.encode(), timeout=fb_timeout, headers=headers)
        if resp.status_code in (200, 201, 204):
            print(f"  Uploaded {remote_path}")
            return True
        else:
            print(f"  Upload {remote_path} failed: {resp.status_code}")
    except Exception as e:
        print(f"  Upload {remote_path} error: {e}")
    return False


def _deploy_keepwifi(fb_base, token, fb_timeout):
    keepwifi_conf = (
        'start on started wifid\n'
        'stop on stopping wifid\n'
        '\n'
        'env WIFI_CHECK_INTERVAL=60\n'
        '\n'
        'respawn\n'
        'respawn limit 3 300\n'
        '\n'
        'script\n'
        '    while true; do\n'
        '        WIFI_STATE=$(lipc-get-prop com.lab126.wifid enable 2>/dev/null || echo "0")\n'
        '        if [ "$WIFI_STATE" != "1" ]; then\n'
        '            lipc-set-prop com.lab126.wifid enable 1 2>/dev/null || true\n'
        '        fi\n'
        '        sleep $WIFI_CHECK_INTERVAL\n'
        '    done\n'
        'end script\n'
    )

    apply_script = (
        '#!/bin/sh\n'
        'mount -o rw,remount / 2>/dev/null\n'
        'cp /mnt/us/linkss/keep-wifi.conf /etc/upstart/keep-wifi.conf\n'
        'initctl stop keep-wifi 2>/dev/null\n'
        'sleep 1\n'
        'initctl reload-configuration 2>/dev/null\n'
        'initctl start keep-wifi 2>/dev/null\n'
        'echo "keep-wifi deployed and started"\n'
    )

    print("  Deploying keep-wifi service...")
    ok1 = _fb_upload_script(fb_base, token, fb_timeout, "linkss/keep-wifi.conf", keepwifi_conf)
    ok2 = _fb_upload_script(fb_base, token, fb_timeout, "linkss/apply_keepwifi.sh", apply_script)
    if ok1 and ok2:
        print("  keep-wifi scripts uploaded to /mnt/us/linkss/.")
    return ok1 and ok2


def _deploy_kual_fix(fb_base, token, fb_timeout):
    autostart_script = (
        '#!/bin/sh\n'
        'LOG=/mnt/us/linkss/autostart.log\n'
        'echo "=== autostart $(date) ===" >> $LOG\n'
        'iptables -C INPUT -p tcp --dport 22 -j ACCEPT 2>/dev/null || iptables -I INPUT 1 -p tcp --dport 22 -j ACCEPT\n'
        'echo "iptables: port 22 allowed" >> $LOG\n'
        'if [ -f /mnt/us/linkss/keep-wifi.conf ]; then\n'
        '    mount -o rw,remount / 2>/dev/null\n'
        '    cp /mnt/us/linkss/keep-wifi.conf /etc/upstart/keep-wifi.conf\n'
        '    initctl reload-configuration 2>/dev/null\n'
        '    initctl start keep-wifi 2>/dev/null\n'
        '    echo "keep-wifi deployed" >> $LOG\n'
        'fi\n'
        'mkdir -p /etc/dropbear\n'
        'for ktype in rsa ecdsa ed25519; do\n'
        '    key="/etc/dropbear/dropbear_${ktype}_host_key"\n'
        '    src="/mnt/us/usbnet/etc/dropbear_${ktype}_host_key"\n'
        '    [ ! -f "$key" ] && [ -f "$src" ] && cp "$src" "$key" 2>/dev/null\n'
        '    [ ! -f "$key" ] && /usr/bin/dropbearkey -t $ktype -f "$key" 2>/dev/null || true\n'
        'done\n'
        'if [ -f /mnt/us/linkss/sshd.conf ]; then\n'
        '    cp /mnt/us/linkss/sshd.conf /etc/upstart/sshd.conf\n'
        '    initctl reload-configuration 2>/dev/null\n'
        '    initctl start sshd 2>/dev/null\n'
        '    echo "sshd deployed" >> $LOG\n'
        'fi\n'
        'if ! ps | grep -v grep | grep filebrowser > /dev/null 2>&1; then\n'
        '    if [ -f /mnt/us/extensions/filebrowser/bin/filebrowser ]; then\n'
        '        FB_ADDR=$(ifconfig wlan0 2>/dev/null | grep "inet " | awk \'{print $2\'})\n'
        '        cd /mnt/us/extensions/filebrowser/bin/ && ./filebrowser -r /mnt/us -p 80 -a "${FB_ADDR:-127.0.0.1}" >> $LOG 2>&1 &\n'
        '        echo "filebrowser started on ${FB_ADDR:-127.0.0.1}:80" >> $LOG\n'
        '    fi\n'
        'fi\n'
        'initctl stop stay-awake 2>/dev/null\n'
        'rm -f /etc/upstart/stay-awake.conf\n'
        'mkdir -p /mnt/us/linkss/screensavers\n'
        'lipc-set-prop -i com.lab126.powerd preventScreenSaver 0 2>/dev/null || true\n'
        'initctl restart powerd 2>/dev/null\n'
        'sleep 3\n'
        'lipc-set-prop -i com.lab126.powerd preventScreenSaver 0 2>/dev/null || true\n'
        'echo "powerd restarted, screensaver unblocked" >> $LOG\n'
        'echo "=== autostart done ===" >> $LOG\n'
    )

    sshd_conf = (
        'start on started wifid\n'
        'stop on stopping wifid\n'
        '\n'
        'respawn\n'
        'respawn limit 10 60\n'
        '\n'
        'pre-start script\n'
        '    mkdir -p /etc/dropbear\n'
        '    for ktype in rsa ecdsa ed25519; do\n'
        '        key="/etc/dropbear/dropbear_${ktype}_host_key"\n'
        '        src="/mnt/us/usbnet/etc/dropbear_${ktype}_host_key"\n'
        '        [ ! -f "$key" ] && [ -f "$src" ] && cp "$src" "$key" 2>/dev/null\n'
        '        [ ! -f "$key" ] && /usr/bin/dropbearkey -t $ktype -f "$key" 2>/dev/null || true\n'
        '    done\n'
        'end script\n'
        '\n'
        'script\n'
        '    exec /usr/bin/dropbear -r /etc/dropbear/dropbear_rsa_host_key -r /etc/dropbear/dropbear_ecdsa_host_key -r /etc/dropbear/dropbear_ed25519_host_key -R -B -p 22 -F -E\n'
        'end script\n'
    )

    usbnet_config = (
        '#!/bin/sh\n'
        'KINDLE_IP=YOUR_KINDLE_IP\n'
        'USE_WIFI="true"\n'
        'USE_WIFI_SSHD_ONLY="true"\n'
        'USE_OPENSSH="false"\n'
        'QUIET_DROPBEAR="false"\n'
        'TWEAK_MAC_ADDRESS="false"\n'
    )

    deploy_script = (
        '#!/bin/sh\n'
        'echo "=== Deploy All Services ==="\n'
        'iptables -C INPUT -p tcp --dport 22 -j ACCEPT 2>/dev/null || iptables -I INPUT 1 -p tcp --dport 22 -j ACCEPT\n'
        'echo "iptables: port 22 allowed"\n'
        '/mnt/us/usbnet/bin/usbnetwork firewall 2>/dev/null || true\n'
        'lipc-set-prop -i com.lab126.powerd stayAwake 0 2>/dev/null || true\n'
        'lipc-set-prop -i com.lab126.powerd preventScreenSaver 0\n'
        'initctl stop keep-wifi 2>/dev/null\n'
        'mkdir -p /mnt/us/linkss/screensavers\n'
        'cp /mnt/us/linkss/keep-wifi.conf /etc/upstart/keep-wifi.conf\n'
        'cp /mnt/us/linkss/sshd.conf /etc/upstart/sshd.conf\n'
        'mkdir -p /etc/dropbear\n'
        'for ktype in rsa ecdsa ed25519; do\n'
        '    key="/etc/dropbear/dropbear_${ktype}_host_key"\n'
        '    src="/mnt/us/usbnet/etc/dropbear_${ktype}_host_key"\n'
        '    [ ! -f "$key" ] && [ -f "$src" ] && cp "$src" "$key" 2>/dev/null\n'
        '    [ ! -f "$key" ] && /usr/bin/dropbearkey -t $ktype -f "$key" 2>/dev/null || true\n'
        'done\n'
        'initctl stop stay-awake 2>/dev/null\n'
        'rm -f /etc/upstart/stay-awake.conf\n'
        'initctl reload-configuration 2>/dev/null\n'
        'initctl start keep-wifi 2>/dev/null\n'
        'initctl start sshd 2>/dev/null\n'
        'if ! ps | grep -v grep | grep filebrowser > /dev/null 2>&1; then\n'
        '    if [ -f /mnt/us/extensions/filebrowser/bin/filebrowser ]; then\n'
        '        FB_ADDR=$(ifconfig wlan0 2>/dev/null | grep "inet " | awk \'{print $2\'})\n'
        '        cd /mnt/us/extensions/filebrowser/bin/ && ./filebrowser -r /mnt/us -p 80 -a "${FB_ADDR:-127.0.0.1}" &\n'
        '    fi\n'
        'fi\n'
        'echo \'{"command": "sh /mnt/us/linkss/autostart.sh"}\' > /mnt/us/linkss/execute\n'
        'kill -9 $(pidof powerd) 2>/dev/null || true\n'
        'sleep 2\n'
        'initctl start powerd 2>/dev/null || true\n'
        'sleep 3\n'
        'lipc-set-prop -i com.lab126.powerd preventScreenSaver 0 2>/dev/null || true\n'
        'echo "=== DEPLOY ALL DONE ==="\n'
    )

    print("  Uploading persistent service files...")
    ok1 = _fb_upload_script(fb_base, token, fb_timeout, "linkss/autostart.sh", autostart_script)
    ok2 = _fb_upload_script(fb_base, token, fb_timeout, "linkss/sshd.conf", sshd_conf)
    ok3 = _fb_upload_script(fb_base, token, fb_timeout, "usbnet/etc/config", usbnet_config)
    ok4 = _fb_upload_script(fb_base, token, fb_timeout, "extensions/fixkindle/bin/deploy_all.sh", deploy_script)
    if ok1 and ok2 and ok3 and ok4:
        print("  Service files uploaded successfully.")
        print("  >>> ACTION NEEDED: Open KUAL -> Fix Kindle -> Deploy All <<<")
    return ok1 and ok2 and ok3 and ok4


def _ensure_keepwifi(k, fb_base=None, fb_token=None, fb_timeout=10):
    """确保 keep-wifi 服务在 Kindle 上运行，未运行则自动部署"""
    ssh_key = k.get("ssh_key", "")
    host = k.get("host", "")
    user = k.get("user", "root")
    port = k.get("port", 22)
    scp_extra = k.get("scp_extra_args", [])
    ssh_base = ["ssh", "-i", ssh_key, "-p", str(port)] + scp_extra + [f"{user}@{host}"]

    try:
        result = subprocess.check_output(
            ssh_base + ["initctl status keep-wifi 2>/dev/null || echo NOT_RUNNING"],
            timeout=8
        ).decode().strip()
        if "running" in result:
            print("  keep-wifi service is running.")
            return True
        print(f"  keep-wifi not running (status: {result[:60]}), re-deploying...")
    except Exception:
        print("  Cannot check keep-wifi status via SSH, will try to apply...")

    if fb_base and fb_token:
        _deploy_keepwifi(fb_base, fb_token, fb_timeout)

    try:
        print("  Applying keep-wifi via SSH...")
        ret = subprocess.call(
            ssh_base + ["sh /mnt/us/linkss/apply_keepwifi.sh"],
            timeout=15
        )
        if ret == 0:
            print("  keep-wifi service deployed and started.")
            return True
        print(f"  apply_keepwifi.sh exited with code {ret}")
    except subprocess.TimeoutExpired:
        print("  SSH timed out while applying keep-wifi.")
    except Exception as e:
        print(f"  SSH failed while applying keep-wifi: {e}")

    if fb_base and fb_token:
        print("  SSH unavailable, uploading KUAL deploy script as fallback...")
        _deploy_kual_fix(fb_base, fb_token, fb_timeout)
    else:
        print("  keep-wifi scripts are on /mnt/us/linkss/ but could not be applied via SSH.")
        print("  Next SSH access will auto-apply them.")
    return False


def upload():
    """推送 PNG 到 Kindle：优先 HTTP(filebrowser)，备选 SSH/SCP"""
    import time
    k = CONFIG["kindle"]
    ignore_errors = k.get("ignore_push_errors", True)
    max_retries = 5
    base_wait = 15

    fb = k.get("filebrowser")
    fb_base = None
    fb_timeout = 10
    token = None
    if fb and fb.get("url"):
        fb_raw_url = fb["url"].rstrip("/")
        if fb_raw_url.endswith("/files"):
            fb_base = fb_raw_url[:-len("/files")]
        elif fb_raw_url.endswith("/files/"):
            fb_base = fb_raw_url.rstrip("/files/")
        else:
            fb_base = fb_raw_url
        fb_remote = fb.get("remote_path", k.get("remote_path", "/mnt/us/linkss/screensavers/bg_ss00.png"))
        fb_timeout = fb.get("timeout_seconds", 10)
        fb_auth = fb.get("auth", {})
        api_path = fb_remote.replace("/mnt/us/", "").replace("/mnt/us", "")
        put_url = f"{fb_base}/api/resources/{api_path}?override=true"
        if fb_auth.get("username"):
            token = _fb_get_token(fb_base, fb_auth, fb_timeout)
        if token:
            _ensure_keepwifi(k, fb_base, token, fb_timeout)
            dir_path = "/".join(api_path.split("/")[:-1])
            if dir_path:
                try:
                    check_headers = {"X-Auth": token}
                    check_resp = requests.get(
                        f"{fb_base}/api/resources/{dir_path}",
                        headers=check_headers, timeout=fb_timeout
                    )
                    if check_resp.status_code == 200:
                        check_data = check_resp.json()
                        if not check_data.get("isDir", False):
                            print(f"  '{dir_path}' is not a directory (symlink/file), removing...")
                            requests.delete(
                                f"{fb_base}/api/resources/{dir_path}",
                                headers=check_headers, timeout=fb_timeout
                            )
                    mkdir_headers = {"X-Auth": token}
                    mkdir_resp = requests.post(
                        f"{fb_base}/api/resources/{dir_path}/",
                        headers=mkdir_headers, timeout=fb_timeout
                    )
                    if mkdir_resp.status_code in (200, 201, 204, 409):
                        print(f"  Directory '{dir_path}' ensured.")
                except Exception as e:
                    print(f"  mkdir '{dir_path}' error: {e}")
        for attempt in range(max_retries):
            try:
                print(f"HTTP push attempt {attempt+1}/{max_retries}: PUT {put_url}")
                headers = {"Content-Type": "application/octet-stream"}
                if token:
                    headers["X-Auth"] = token
                with open(CONFIG["output_path"], "rb") as f:
                    resp = requests.put(put_url, data=f, timeout=fb_timeout, headers=headers)
                if resp.status_code in (200, 201, 204):
                    print("  HTTP push successful!")
                    if _try_refresh_screensaver(k, fb_base, token, fb_timeout):
                        return True
                    print("  HTTP upload completed, but screensaver refresh did not run.")
                    print("  Continue with SSH/SCP fallback to force refresh...")
                    break
                elif resp.status_code == 403 and not token and attempt == 0:
                    print("  Got 403, trying auth with default credentials...")
                    token = _fb_get_token(fb_base, {"username": "", "password": ""}, fb_timeout)
                    if token:
                        continue
                else:
                    print(f"  HTTP push failed: {resp.status_code} {resp.text[:100]}")
            except requests.Timeout:
                print(f"  HTTP attempt {attempt+1} timed out")
            except requests.ConnectionError:
                print(f"  HTTP attempt {attempt+1} connection error")
            except Exception as e:
                print(f"  HTTP attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                wait = base_wait * (attempt + 1)
                print(f"  Retry in {wait}s...")
                time.sleep(wait)
        print("HTTP push/refresh incomplete, falling back to SSH...")

    ssh_key = k.get("ssh_key", "")
    host = k.get("host", "")
    user = k.get("user", "root")
    remote_path = k.get("remote_path", "/mnt/us/linkss/screensavers/bg_ss00.png")
    port = k.get("port", 22)
    scp_extra = k.get("scp_extra_args", [])
    for attempt in range(max_retries):
        try:
            scp_args = ["scp", "-i", ssh_key, "-P", str(port)]
            scp_args.extend(scp_extra)
            scp_args.extend([CONFIG["output_path"], f"{user}@{host}:{remote_path}"])
            print(f"SCP push attempt {attempt+1}/{max_retries}")
            ret = subprocess.call(scp_args, timeout=30)
            if ret != 0:
                print(f"  SCP failed (exit {ret})")
                if attempt < max_retries - 1:
                    wait = base_wait * (attempt + 1)
                    print(f"  Retry in {wait}s...")
                    time.sleep(wait)
                continue
            for cmd_str in k.get("post_push_commands", []):
                ssh_args = ["ssh", "-i", ssh_key, "-p", str(port)] + scp_extra + [f"{user}@{host}", cmd_str]
                print(f"  Post-push: {cmd_str[:60]}...")
                ret = subprocess.call(ssh_args, timeout=20)
                if ret != 0:
                    print(f"  Post-push failed (exit {ret})")
                    raise RuntimeError("Post-push refresh failed")
            print("SCP push successful!")
            _ensure_keepwifi(k, fb_base, token, fb_timeout)
            return True
        except subprocess.TimeoutExpired:
            print(f"  SCP attempt {attempt+1} timed out")
        except Exception as e:
            print(f"  SCP attempt {attempt+1} failed: {e}")
        if attempt < max_retries - 1:
            wait = base_wait * (attempt + 1)
            print(f"  Retry in {wait}s...")
            time.sleep(wait)
    if ignore_errors:
        print("All push attempts failed (ignored).")
        return False
    else:
        raise RuntimeError("All push attempts failed")


def _try_refresh_screensaver(k, fb_base=None, fb_token=None, fb_timeout=10):
    """刷新 Kindle 屏保：优先 SSH，备选 FileBrowser"""
    ssh_ok = _try_ssh_refresh(k)
    if ssh_ok:
        return True
    if fb_base and fb_token:
        return _try_fb_refresh(k, fb_base, fb_token, fb_timeout)
    return False


def _try_ssh_refresh(k):
    ssh_key = k.get("ssh_key", "")
    host = k.get("host", "")
    user = k.get("user", "root")
    port = k.get("port", 22)
    scp_extra = k.get("scp_extra_args", [])
    ssh_base = ["ssh", "-i", ssh_key, "-p", str(port)] + scp_extra + [f"{user}@{host}"]

    refresh_cmd = (
        "/mnt/us/linkss/bin/linkss >/tmp/linkss-refresh.log 2>&1 || true; "
        "kill -9 $(pidof powerd) 2>/dev/null || true; "
        "sleep 2; "
        "initctl start powerd 2>/dev/null || true; "
        "sleep 3; "
        "lipc-set-prop -i com.lab126.powerd preventScreenSaver 0 2>/dev/null || true; "
        "sleep 1; "
        "lipc-set-prop com.lab126.powerd powerButton 1 2>/dev/null || true; "
        "sleep 4; "
        "lipc-get-prop com.lab126.powerd state 2>/dev/null || true"
    )

    for attempt in range(3):
        try:
            print(f"  SSH refresh attempt {attempt+1}/3...")
            output = subprocess.check_output(
                ssh_base + [refresh_cmd],
                stderr=subprocess.STDOUT,
                timeout=30
            ).decode(errors="replace").strip()
            state = output.splitlines()[-1].strip() if output else ""
            print(f"  Kindle state after refresh: {state or 'unknown'}")
            return True
        except (subprocess.TimeoutExpired, Exception):
            if attempt < 2:
                import time; time.sleep(5)
                continue
            return False


def _try_fb_refresh(k, fb_base, token, fb_timeout):
    """通过 FileBrowser API 上传刷新脚本并尝试通过 SSH 执行"""
    refresh_script = (
        '#!/bin/sh\n'
        '/mnt/us/linkss/bin/linkss >/tmp/linkss-refresh.log 2>&1 || true\n'
        'kill -9 $(pidof powerd) 2>/dev/null || true\n'
        'sleep 2\n'
        'initctl start powerd 2>/dev/null || true\n'
        'sleep 3\n'
        'lipc-set-prop -i com.lab126.powerd preventScreenSaver 0 2>/dev/null || true\n'
        'sleep 1\n'
        'lipc-set-prop com.lab126.powerd powerButton 1 2>/dev/null || true\n'
    )

    ok = _fb_upload_script(fb_base, token, fb_timeout, "linkss/refresh_screensaver.sh", refresh_script)
    if not ok:
        return False

    ssh_key = k.get("ssh_key", "")
    host = k.get("host", "")
    user = k.get("user", "root")
    port = k.get("port", 22)
    scp_extra = k.get("scp_extra_args", [])
    ssh_base = ["ssh", "-i", ssh_key, "-p", str(port)] + scp_extra + [f"{user}@{host}"]

    try:
        print("  Trying SSH to execute refresh + keepwifi...")
        result = subprocess.call(
            ssh_base + ["sh /mnt/us/linkss/refresh_screensaver.sh"],
            timeout=15
        )
        if result == 0:
            print("  Refresh + keepwifi applied via SSH.")
            return True
    except Exception:
        pass

    print("  SSH not available; refresh script uploaded but needs manual execution.")
    print("  TIP: Wake Kindle, then: ssh root@<KINDLE_IP> 'sh /mnt/us/linkss/refresh_screensaver.sh'")
    return False


def get_data_hash(data_dict):
    """计算数据哈希值，用于检测变化"""
    raw = json.dumps(data_dict, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def check_and_push(data_dict, force=False):
    """检查数据是否变化，有变化才重新生成并推送"""
    hash_path = Path(CONFIG["hash_path"])
    current_hash = get_data_hash(data_dict)
    last_hash = ""
    if hash_path.exists():
        last_hash = hash_path.read_text().strip()
    if current_hash == last_hash and not force:
        print("Data unchanged, skip rendering.")
        return False
    # 数据有变化，重新生成
    render()
    # 保存新哈希
    hash_path.write_text(current_hash)
    # 推送到 Kindle
    try:
        upload()
    except Exception as e:
        print(f"Push failed: {e}")
    return True


if __name__ == "__main__":
    # 支持 --config 参数加载外部配置文件
    config_path = None
    args = sys.argv[1:]
    filtered_args = []
    for i, a in enumerate(args):
        if a == "--config" and i + 1 < len(args):
            config_path = args[i + 1]
            continue
        elif a.startswith("--config="):
            config_path = a.split("=", 1)[1]
            continue
        elif i > 0 and args[i - 1] == "--config":
            continue
        else:
            filtered_args.append(a)
    if config_path and Path(config_path).exists():
        with open(config_path) as f:
            ext_cfg = json.load(f)
        if "canvas" in ext_cfg:
            CONFIG["width"] = ext_cfg["canvas"].get("width", CONFIG["width"])
            CONFIG["height"] = ext_cfg["canvas"].get("height", CONFIG["height"])
            CONFIG["margin"] = ext_cfg["canvas"].get("margin", CONFIG["margin"])
        if "caiyun" in ext_cfg:
            CONFIG["caiyun_token"] = ext_cfg["caiyun"].get("token", CONFIG["caiyun_token"])
            CONFIG["caiyun_token_env"] = ext_cfg["caiyun"].get("token_env", CONFIG.get("caiyun_token_env", "CAIYUN_TOKEN"))
        if "location" in ext_cfg:
            loc = ext_cfg["location"]
            CONFIG["location"] = f"{loc.get('longitude', 116.65)},{loc.get('latitude', 39.92)}"
            if "name" in loc:
                CONFIG["location_name"] = loc["name"]
        if "output" in ext_cfg:
            CONFIG["output_path"] = ext_cfg["output"].get("png", CONFIG["output_path"])
        if "kindle" in ext_cfg:
            CONFIG["kindle"].update(ext_cfg["kindle"])
        if "fonts" in ext_cfg:
            CONFIG["font_regular"] = ext_cfg["fonts"].get("regular", CONFIG["font_regular"])
            CONFIG["font_bold"] = ext_cfg["fonts"].get("bold", CONFIG["font_bold"])
            CONFIG["font_light"] = ext_cfg["fonts"].get("light", CONFIG["font_light"])
        if "apple" in ext_cfg:
            CONFIG["calendar_days"] = ext_cfg["apple"].get("calendar_days", 3)
            CONFIG["max_events"] = ext_cfg["apple"].get("max_events", 8)
            CONFIG["max_reminders"] = ext_cfg["apple"].get("max_reminders", 7)
            if "calendar_names" in ext_cfg["apple"]:
                CONFIG["calendar_names"] = ext_cfg["apple"]["calendar_names"]
        print(f"Config loaded from {config_path}")
    force = "--force" in filtered_args
    if "--push" in filtered_args:
        # 直接生成并推送（不检测变化）
        render()
        if not upload():
            sys.exit(1)
    else:
        # 智能模式：有变化才生成+推送
        weather = get_weather()
        events = get_calendar_events()
        quote = get_hitokoto()
        reminders = get_reminders()
        data = {
            "weather": weather, "events": events,
            "quote": quote, "reminders": reminders
        }
        check_and_push(data, force=force)
