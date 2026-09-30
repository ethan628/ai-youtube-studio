import os
import re
import math
from PIL import Image, ImageDraw, ImageFont
from src.script_generator import is_programming_topic

# 跨平台中文字型支援 (優先載入繁體中文 TC，確保絕無豆腐框 ▯)
CANDIDATE_FONTS_BOLD = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
    "C:\\Windows\\Fonts\\msjhbd.ttc",
    "C:\\Windows\\Fonts\\msjh.ttc",
    "/System/Library/Fonts/PingFang.ttc",
]

CANDIDATE_FONTS_REGULAR = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc",
    "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
    "C:\\Windows\\Fonts\\msjh.ttc",
    "/System/Library/Fonts/PingFang.ttc",
]

def clean_emoji(text: str) -> str:
    """清理文字中的 Emoji 與特殊符號，避免在非 Emoji 字型中產生豆腐框 ☒"""
    if not text:
        return ""
    emoji_pattern = re.compile(
        "[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]|[\ufe0f]",
        flags=re.UNICODE
    )
    cleaned = emoji_pattern.sub("", text).strip()
    cleaned = cleaned.replace("⚡", "|").replace("➔", "->").replace("✔", "").replace("❌", "").replace("✅", "")
    return cleaned.strip()

def get_font(size: int, bold: bool = True):
    """精準載入繁中 CJK 字型，自動匹配 TTC 繁中 TC index=3"""
    candidates = CANDIDATE_FONTS_BOLD if bold else CANDIDATE_FONTS_REGULAR
    for path in candidates:
        if os.path.exists(path):
            if path.endswith(".ttc") and "Noto" in path:
                for idx in [3, 2, 0]:  # Index 3 is Traditional Chinese (TC)
                    try:
                        return ImageFont.truetype(path, size, index=idx)
                    except Exception:
                        pass
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()

def draw_gradient_background(draw, w, h, top_color=(15, 23, 42), bottom_color=(3, 7, 18)):
    """向後相容：繪製漸層背景"""
    for y in range(h):
        r = y / h
        c = (
            int(top_color[0] * (1 - r) + bottom_color[0] * r),
            int(top_color[1] * (1 - r) + bottom_color[1] * r),
            int(top_color[2] * (1 - r) + bottom_color[2] * r),
        )
        draw.line([(0, y), (w, y)], fill=c)

def draw_tech_grid(draw, w, h, grid_size=70, color=(25, 38, 65)):
    """向後相容：繪製科技格線"""
    for x in range(0, w, grid_size):
        draw.line([(x, 0), (x, h)], fill=color)
    for y in range(0, h, grid_size):
        draw.line([(0, y), (w, y)], fill=color)

def draw_tech_background(draw, w, h, base_color=(10, 16, 32), accent_color=(0, 240, 255)):
    """繪製高質感深色漸層背景與微弱科技格線"""
    top_c = (base_color[0] + 14, base_color[1] + 16, base_color[2] + 28)
    bot_c = (max(0, base_color[0] - 6), max(0, base_color[1] - 8), max(0, base_color[2] - 10))
    for y in range(h):
        r = y / h
        c = (
            int(top_c[0] * (1 - r) + bot_c[0] * r),
            int(top_c[1] * (1 - r) + bot_c[1] * r),
            int(top_c[2] * (1 - r) + bot_c[2] * r),
        )
        draw.line([(0, y), (w, y)], fill=c)

    # 科技格線
    grid = 80
    for x in range(0, w, grid):
        draw.line([(x, 0), (x, h)], fill=(25, 38, 65))
    for y in range(0, h, grid):
        draw.line([(0, y), (w, y)], fill=(25, 38, 65))

    # 光暈裝飾
    cx, cy = int(w * 0.78), int(h * 0.38)
    for rad in range(350, 0, -40):
        glow_c = (
            int(base_color[0] + (accent_color[0] - base_color[0]) * 0.16 * (1 - rad / 350)),
            int(base_color[1] + (accent_color[1] - base_color[1]) * 0.16 * (1 - rad / 350)),
            int(base_color[2] + (accent_color[2] - base_color[2]) * 0.16 * (1 - rad / 350)),
        )
        draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=glow_c)

def draw_vector_check(draw, cx, cy, radius=18, bg_color=(34, 197, 94)):
    """繪製向量綠色勾勾圖標"""
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=bg_color)
    draw.line([(cx - 7, cy), (cx - 2, cy + 6)], fill=(255, 255, 255), width=3)
    draw.line([(cx - 2, cy + 6), (cx + 8, cy - 6)], fill=(255, 255, 255), width=3)

def draw_vector_cross(draw, cx, cy, radius=18, bg_color=(239, 68, 68)):
    """繪製向量紅色叉叉圖標"""
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=bg_color)
    draw.line([(cx - 6, cy - 6), (cx + 6, cy + 6)], fill=(255, 255, 255), width=3)
    draw.line([(cx - 6, cy + 6), (cx + 6, cy - 6)], fill=(255, 255, 255), width=3)

def draw_vector_arrow(draw, x1, y1, x2, y2, color=(0, 240, 255), width=3):
    """繪製向量科技箭頭"""
    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
    draw.polygon([(x2, y2), (x2 - 12, y2 - 7), (x2 - 12, y2 + 7)], fill=color)

# =========================================================================
# 多樣化場景視覺排版風格 (徹底解決「圖片不會變」的問題)
# =========================================================================

def _render_hero_style(title, subtitle, badge, bullets, highlight_box, out_path, watermark="AI玩科技 | 2026全自動長片實戰", topic=""):
    """風格 1：Hero 主題大開場（含智慧硬體/手機/AI核心圖形插畫）"""
    w, h = 1920, 1080
    img = Image.new("RGB", (w, h), (10, 16, 32))
    draw = ImageDraw.Draw(img)
    draw_tech_background(draw, w, h, base_color=(10, 16, 32), accent_color=(0, 240, 255))

    # 右上角頻道浮水印
    clean_wm = clean_emoji(watermark) or "AI玩科技 | 2026全自動長片實戰"
    draw.text((w - 480, 45), clean_wm, fill=(148, 163, 184), font=get_font(22, bold=True))

    # 頂部膠囊徽章
    font_badge = get_font(26, bold=True)
    clean_b = clean_emoji(badge) or "爆款開場"
    draw.rounded_rectangle([100, 65, 380, 115], radius=12, fill=(30, 41, 59), outline=(0, 240, 255), width=2)
    draw.ellipse([120, 83, 134, 97], fill=(0, 240, 255))
    draw.text((150, 72), clean_b, fill=(0, 240, 255), font=font_badge)

    # 主標題
    clean_t = clean_emoji(title)
    font_t = get_font(62, bold=True)
    if len(clean_t) > 22:
        t1, t2 = clean_t[:20], clean_t[20:44]
        draw.text((102, 142), t1, fill=(0, 100, 160), font=font_t)
        draw.text((100, 140), t1, fill=(255, 255, 255), font=font_t)
        draw.text((102, 222), t2, fill=(0, 100, 160), font=font_t)
        draw.text((100, 220), t2, fill=(255, 255, 255), font=font_t)
        sub_y = 315
    else:
        draw.text((102, 152), clean_t, fill=(0, 100, 160), font=font_t)
        draw.text((100, 150), clean_t, fill=(255, 255, 255), font=font_t)
        sub_y = 245

    # 副標題
    font_s = get_font(32, bold=False)
    draw.text((100, sub_y), clean_emoji(subtitle), fill=(203, 213, 225), font=font_s)

    # 分隔線
    draw.line([(100, sub_y + 50), (w - 100, sub_y + 50)], fill=(51, 65, 85), width=2)
    draw.line([(100, sub_y + 50), (450, sub_y + 50)], fill=(0, 240, 255), width=3)

    # 左側：3 大核心重點條列卡
    cy = sub_y + 80
    font_bf = get_font(30, bold=True)
    bullets_to_draw = bullets if bullets else ["零代碼門檻：文字指令直接驅動", "三大 AI 協同：全自動生產影音", "極致高畫質：毫秒級字幕精準對齊"]
    for i, b in enumerate(bullets_to_draw[:3]):
        by = cy + (i * 105)
        draw.rounded_rectangle([100, by, 950, by + 85], radius=12, fill=(15, 23, 42), outline=(51, 65, 85), width=1)
        bar_color = (0, 240, 255) if i % 2 == 0 else (168, 85, 247)
        draw.rectangle([100, by, 112, by + 85], fill=bar_color)
        draw.ellipse([132, by + 24, 168, by + 60], fill=bar_color)
        draw.text((144, by + 26), str(i + 1), fill=(10, 15, 29), font=get_font(24, bold=True))
        draw.text((188, by + 24), clean_emoji(b)[:24], fill=(241, 245, 249), font=font_bf)

    # 右側：主題插畫區 (智慧手機 / 自動滾動翻頁示意圖)
    rx, ry, rw, rh = 1050, sub_y + 70, 770, 500
    draw.rounded_rectangle([rx, ry, rx + rw, ry + rh], radius=18, fill=(13, 20, 38), outline=(0, 240, 255), width=2)

    # 繪製手機立體框架
    px, py, pw, ph = rx + int((rw - 270) / 2), ry + 35, 270, 430
    draw.rounded_rectangle([px, py, px + pw, py + ph], radius=24, fill=(5, 8, 18), outline=(148, 163, 184), width=3)
    draw.rounded_rectangle([px + 95, py + 12, px + 175, py + 20], radius=4, fill=(71, 85, 105))
    draw.rectangle([px + 14, py + 34, px + pw - 14, py + ph - 28], fill=(15, 23, 42))

    # 手機內動態頁面卡
    draw.rounded_rectangle([px + 24, py + 55, px + pw - 24, py + 155], radius=8, fill=(30, 41, 59), outline=(0, 240, 255), width=1)
    draw.text((px + 36, py + 68), "Auto Page Scroll", fill=(0, 240, 255), font=get_font(18, bold=True))
    draw.text((px + 36, py + 102), "免動手智慧翻頁中...", fill=(203, 213, 225), font=get_font(16, bold=False))

    # 翻頁動態箭頭
    draw.polygon([(px + 135, py + 200), (px + 115, py + 180), (px + 155, py + 180)], fill=(56, 189, 248))
    draw.polygon([(px + 135, py + 240), (px + 115, py + 220), (px + 155, py + 220)], fill=(14, 165, 233))
    draw.polygon([(px + 135, py + 280), (px + 115, py + 260), (px + 155, py + 260)], fill=(2, 132, 199))

    # 雷達感應波紋
    for r in range(45, 115, 25):
        draw.arc([px + pw + 10, py + 70 - r, px + pw + 10 + r * 2, py + 70 + r], start=-60, end=60, fill=(0, 240, 255), width=2)
    draw.text((px + pw + 35, py + 110), "零觸碰偵測", fill=(56, 189, 248), font=get_font(18, bold=True))

    img.save(out_path, quality=95)

def _render_workflow_style(title, subtitle, badge, bullets, highlight_box, out_path, watermark="AI玩科技 | 核心架構解析", topic=""):
    """風格 2：流程圖 / 系統架構卡（4 階段箭頭串接）"""
    w, h = 1920, 1080
    img = Image.new("RGB", (w, h), (15, 12, 32))
    draw = ImageDraw.Draw(img)
    draw_tech_background(draw, w, h, base_color=(15, 12, 32), accent_color=(168, 85, 247))

    clean_wm = clean_emoji(watermark) or "AI玩科技 | 核心架構解析"
    draw.text((w - 480, 45), clean_wm, fill=(148, 163, 184), font=get_font(22, bold=True))

    # Badge
    clean_b = clean_emoji(badge) or "核心架構機制"
    draw.rounded_rectangle([100, 65, 380, 115], radius=12, fill=(35, 28, 55), outline=(168, 85, 247), width=2)
    draw.ellipse([120, 83, 134, 97], fill=(168, 85, 247))
    draw.text((150, 72), clean_b, fill=(168, 85, 247), font=get_font(26, bold=True))

    font_t = get_font(60, bold=True)
    draw.text((100, 140), clean_emoji(title)[:26], fill=(255, 255, 255), font=font_t)
    draw.text((100, 220), clean_emoji(subtitle)[:40], fill=(203, 213, 225), font=get_font(32, bold=False))

    # 4 階段流程卡 (支援依傳入 bullets 動態生成，或預設科技流程)
    colors = [(56, 189, 248), (168, 85, 247), (234, 179, 8), (34, 197, 94)]
    tags = ["Input", "Core AI", "Control", "Output"]

    stages = []
    if bullets and len(bullets) >= 2:
        for i, b in enumerate(bullets[:4]):
            cleaned_b = clean_emoji(b)
            parts = cleaned_b.split("：") if "：" in cleaned_b else cleaned_b.split(":")
            st_title = parts[0][:10] if parts else f"步驟 {i+1}"
            st_desc = parts[1][:14] if len(parts) > 1 else cleaned_b[:14]
            stages.append({
                "title": f"{i+1}. {st_title}",
                "desc": st_desc,
                "tag": tags[i] if i < len(tags) else f"Step {i+1}",
                "color": colors[i % len(colors)]
            })
    else:
        stages = [
            {"title": "1. 數據採集", "desc": "攝像頭即時捕捉姿勢", "tag": "Input", "color": (56, 189, 248)},
            {"title": "2. AI 演算法", "desc": "模型深度特徵解析", "tag": "Model", "color": (168, 85, 247)},
            {"title": "3. 觸發控制器", "desc": "精準閾值校正鎖定", "tag": "Control", "color": (234, 179, 8)},
            {"title": "4. 平滑輸出", "desc": "全自動平穩任務執行", "tag": "Output", "color": (34, 197, 94)}
        ]

    box_w, box_h = 360, 360
    start_x = 100
    gap = 80
    y_pos = 320

    for i, st in enumerate(stages):
        x = start_x + i * (box_w + gap)
        draw.rounded_rectangle([x, y_pos, x + box_w, y_pos + box_h], radius=16, fill=(22, 26, 48), outline=st["color"], width=2)
        draw.rounded_rectangle([x, y_pos, x + box_w, y_pos + 60], radius=16, fill=(32, 38, 68))
        draw.text((x + 20, y_pos + 16), st["tag"], fill=st["color"], font=get_font(22, bold=True))
        draw.text((x + 20, y_pos + 90), st["title"], fill=(255, 255, 255), font=get_font(28, bold=True))
        draw.text((x + 20, y_pos + 150), st["desc"], fill=(148, 163, 184), font=get_font(22, bold=False))

        # 節點內部狀態框
        draw.rounded_rectangle([x + 20, y_pos + 220, x + box_w - 20, y_pos + 320], radius=10, fill=(10, 15, 28))
        draw.text((x + 35, y_pos + 245), "Status: [ACTIVE]", fill=st["color"], font=get_font(18, bold=True))
        draw.text((x + 35, y_pos + 280), "Precision: 99.8%", fill=(100, 116, 139), font=get_font(16, bold=False))

        # 向量連接箭頭
        if i < len(stages) - 1:
            ax = x + box_w + 12
            ay = y_pos + int(box_h / 2)
            draw_vector_arrow(draw, ax, ay, ax + 54, ay, color=(0, 240, 255), width=4)

    img.save(out_path, quality=95)

def _render_console_style(title, subtitle, badge, bullets, highlight_box, out_path, watermark=None, topic=""):
    """風格 3：終端機實戰 (程式主題) / 知識精華筆記卡 (非程式主題)"""
    w, h = 1920, 1080
    is_code = is_programming_topic(topic)
    
    if not is_code:
        # 非程式主題：優雅墨藍色系背景
        img = Image.new("RGB", (w, h), (10, 18, 30))
        draw = ImageDraw.Draw(img)
        draw_tech_background(draw, w, h, base_color=(10, 18, 30), accent_color=(56, 189, 248))
        clean_wm = clean_emoji(watermark) if watermark else "精選深度解析 | 實戰精華筆記"
        clean_b = clean_emoji(badge) or "精華重點筆記"
        border_c = (56, 189, 248)
    else:
        # 程式主題：經典綠色終端機背景
        img = Image.new("RGB", (w, h), (8, 20, 18))
        draw = ImageDraw.Draw(img)
        draw_tech_background(draw, w, h, base_color=(6, 18, 16), accent_color=(16, 185, 129))
        clean_wm = clean_emoji(watermark) if watermark else "AI玩科技 | 實戰代碼演示"
        clean_b = clean_emoji(badge) or "實戰代碼演示"
        border_c = (16, 185, 129)

    draw.text((w - 480, 45), clean_wm, fill=(148, 163, 184), font=get_font(22, bold=True))

    draw.rounded_rectangle([100, 65, 380, 115], radius=12, fill=(20, 35, 30) if is_code else (20, 30, 48), outline=border_c, width=2)
    draw.ellipse([120, 83, 134, 97], fill=border_c)
    draw.text((150, 72), clean_b, fill=border_c, font=get_font(26, bold=True))

    draw.text((100, 140), clean_emoji(title)[:26], fill=(255, 255, 255), font=get_font(60, bold=True))
    draw.text((100, 220), clean_emoji(subtitle)[:40], fill=(203, 213, 225), font=get_font(32, bold=False))

    # 左側：條列打勾清單
    ly = 320
    font_bf = get_font(28, bold=True)
    bullets_to_draw = bullets if bullets else (
        ["核心瓶頸精準定位", "五分鐘微行動立即開始", "建立持續正向反饋循環"] if not is_code else
        ["瀏覽器支援 WebRTC", "本地離線計算安全私密", "一鍵部署至 GitHub Pages"]
    )
    for i, b in enumerate(bullets_to_draw[:4]):
        by = ly + (i * 120)
        draw.rounded_rectangle([100, by, 880, by + 95], radius=12, fill=(15, 28, 24) if is_code else (15, 25, 40), outline=(30, 58, 48) if is_code else (30, 50, 75), width=1)
        draw_vector_check(draw, 145, by + 48, radius=20, bg_color=(16, 185, 129) if is_code else (56, 189, 248))
        draw.text((195, by + 32), clean_emoji(b)[:24], fill=(240, 253, 244) if is_code else (240, 249, 255), font=font_bf)

    # 右側：寫實終端機視窗 vs 知識精華筆記卡
    tx, ty, tw, th = 940, 320, 880, 520
    if is_code:
        draw.rounded_rectangle([tx, ty, tx + tw, ty + th], radius=16, fill=(10, 15, 20), outline=(16, 185, 129), width=2)
        draw.rounded_rectangle([tx, ty, tx + tw, ty + 50], radius=16, fill=(24, 30, 38))
        draw.ellipse([tx + 20, ty + 18, tx + 34, ty + 32], fill=(239, 68, 68))
        draw.ellipse([tx + 42, ty + 18, tx + 56, ty + 32], fill=(234, 179, 8))
        draw.ellipse([tx + 64, ty + 18, tx + 78, ty + 32], fill=(34, 197, 94))
        draw.text((tx + 95, ty + 14), "bash - 80x24 (ai-pipeline-daemon)", fill=(156, 163, 175), font=get_font(20, bold=False))

        code_lines = (highlight_box or "$ npm run dev\n>>> Model loaded: 100%\n>>> Sensor active: 60fps\n>>> Listening for gestures...").split("\n")
        line_y = ty + 75
        font_code = get_font(24, bold=False)
        for l in code_lines:
            color = (52, 211, 153) if "$" in l or ">>>" in l else (229, 231, 235)
            draw.text((tx + 30, line_y), l, fill=color, font=font_code)
            line_y += 42

        draw.rectangle([tx + 30, line_y + 5, tx + 45, line_y + 35], fill=(52, 211, 153))
    else:
        # 非程式主題：優雅知識精華筆記卡 (無終端機、無代碼、無打字光標)
        draw.rounded_rectangle([tx, ty, tx + tw, ty + th], radius=16, fill=(15, 23, 42), outline=(56, 189, 248), width=2)
        draw.rounded_rectangle([tx, ty, tx + tw, ty + 50], radius=16, fill=(30, 41, 59))
        draw.ellipse([tx + 20, ty + 18, tx + 34, ty + 32], fill=(56, 189, 248))
        draw.ellipse([tx + 42, ty + 18, tx + 56, ty + 32], fill=(129, 140, 248))
        draw.ellipse([tx + 64, ty + 18, tx + 78, ty + 32], fill=(244, 114, 182))
        draw.text((tx + 95, ty + 14), "💡 實戰精華筆記 (Key Highlights)", fill=(226, 232, 240), font=get_font(20, bold=True))

        box_lines = (highlight_box or "【核心思維地圖】\n痛點洞察 -> 本質拆解 -> 具體實踐 -> 持續複利").split("\n")
        line_y = ty + 75
        font_box = get_font(24, bold=False)
        for l in box_lines:
            clean_l = clean_emoji(l)
            color = (56, 189, 248) if any(k in clean_l for k in ["【", "[", "核心", "清單", "原則"]) else (241, 245, 249)
            draw.text((tx + 30, line_y), clean_l, fill=color, font=font_box)
            line_y += 42

    img.save(out_path, quality=95)

def _render_comparison_style(title, subtitle, badge, bullets, highlight_box, out_path, watermark="AI玩科技 | 效益數據對比", topic=""):
    """風格 4：效益數據對比大字報（Before vs After）"""
    w, h = 1920, 1080
    img = Image.new("RGB", (w, h), (24, 16, 8))
    draw = ImageDraw.Draw(img)
    draw_tech_background(draw, w, h, base_color=(24, 16, 8), accent_color=(245, 158, 11))

    clean_wm = clean_emoji(watermark) or "AI玩科技 | 效益數據對比"
    draw.text((w - 480, 45), clean_wm, fill=(148, 163, 184), font=get_font(22, bold=True))

    clean_b = clean_emoji(badge) or "效益數據對比"
    draw.rounded_rectangle([100, 65, 380, 115], radius=12, fill=(40, 28, 15), outline=(245, 158, 11), width=2)
    draw.ellipse([120, 83, 134, 97], fill=(245, 158, 11))
    draw.text((150, 72), clean_b, fill=(245, 158, 11), font=get_font(26, bold=True))

    draw.text((100, 140), clean_emoji(title)[:26], fill=(255, 255, 255), font=get_font(60, bold=True))
    draw.text((100, 220), clean_emoji(subtitle)[:40], fill=(203, 213, 225), font=get_font(32, bold=False))

    stats = [
        {"value": "100%", "label": "全自動執行", "sub": "端到端免手動介入", "color": (245, 158, 11)},
        {"value": "$0 元", "label": "開源零成本", "sub": "無需額外添購硬體", "color": (16, 185, 129)},
        {"value": "0.1s", "label": "極速即時響應", "sub": "毫秒級高並發處理", "color": (56, 189, 248)}
    ]
    sw = 530
    for i, s in enumerate(stats):
        sx = 100 + i * (sw + 65)
        sy = 300
        draw.rounded_rectangle([sx, sy, sx + sw, sy + 180], radius=16, fill=(35, 24, 12), outline=s["color"], width=2)
        draw.text((sx + 35, sy + 20), s["value"], fill=s["color"], font=get_font(64, bold=True))
        draw.text((sx + 35, sy + 105), s["label"], fill=(255, 255, 255), font=get_font(28, bold=True))
        draw.text((sx + 35, sy + 140), s["sub"], fill=(156, 163, 175), font=get_font(20, bold=False))

    # 左側：痛點對比
    draw.rounded_rectangle([100, 520, 930, 800], radius=16, fill=(28, 18, 18), outline=(239, 68, 68), width=2)
    draw_vector_cross(draw, 140, 560, radius=18, bg_color=(239, 68, 68))
    draw.text((170, 545), "傳統手動作法痛點", fill=(248, 113, 113), font=get_font(30, bold=True))
    draw.text((130, 605), "• 手動重複操作繁瑣且耗費大量時間", fill=(229, 231, 235), font=get_font(24, bold=False))
    draw.text((130, 655), "• 傳統做法需要額外購買昂貴外設與硬體", fill=(229, 231, 235), font=get_font(24, bold=False))
    draw.text((130, 705), "• 操作複雜學習門檻高，難以規模化套用", fill=(229, 231, 235), font=get_font(24, bold=False))

    # 右側：自動化優勢
    draw.rounded_rectangle([990, 520, 1820, 800], radius=16, fill=(18, 28, 20), outline=(34, 197, 94), width=2)
    draw_vector_check(draw, 1030, 560, radius=18, bg_color=(34, 197, 94))
    draw.text((1060, 545), "全自動 AI 核心優勢", fill=(74, 222, 128), font=get_font(30, bold=True))
    adv_bullets = [clean_emoji(b)[:24] for b in bullets[:3]] if bullets else [
        "全自動 AI 驅動，釋放雙手真正免盯盤",
        "純開源無額外硬體花費，立即可跑",
        "一鍵啟動自動化管線，效率直接提升數倍"
    ]
    for idx, adv in enumerate(adv_bullets):
        draw.text((1020, 605 + idx * 50), f"• {adv}", fill=(229, 231, 235), font=get_font(24, bold=False))

    img.save(out_path, quality=95)

def _render_summary_style(title, subtitle, badge, bullets, highlight_box, out_path, watermark=None, topic=""):
    """風格 5：結尾呼籲 / 資源領取與精華總結卡"""
    w, h = 1920, 1080
    is_code = is_programming_topic(topic)
    img = Image.new("RGB", (w, h), (18, 10, 30))
    draw = ImageDraw.Draw(img)
    draw_tech_background(draw, w, h, base_color=(18, 10, 30), accent_color=(236, 72, 153))

    clean_wm = clean_emoji(watermark) if watermark else ("AI玩科技 | 開源資源分享" if is_code else "精選深度解析 | 實踐指南")
    draw.text((w - 480, 45), clean_wm, fill=(148, 163, 184), font=get_font(22, bold=True))

    clean_b = clean_emoji(badge) or ("資源與結尾行動" if is_code else "精華總結與行動")
    draw.rounded_rectangle([100, 65, 380, 115], radius=12, fill=(40, 20, 50), outline=(236, 72, 153), width=2)
    draw.ellipse([120, 83, 134, 97], fill=(236, 72, 153))
    draw.text((150, 72), clean_b, fill=(236, 72, 153), font=get_font(26, bold=True))

    draw.text((100, 140), clean_emoji(title)[:26], fill=(255, 255, 255), font=get_font(60, bold=True))
    draw.text((100, 220), clean_emoji(subtitle)[:40], fill=(203, 213, 225), font=get_font(32, bold=False))

    # 左側：訂閱卡
    channel_name = "【雙AI深度成長】頻道" if not is_code else "【AI玩科技】頻道"
    channel_desc = "每週帶來最實用高效成長與深度思維解析" if not is_code else "每週帶來最新最實用 AI 自動化黑科技實戰教學"
    note_line = "• 點讚收藏，隨時回頭翻看本集精華筆記" if not is_code else "• 點讚收藏，隨時回頭翻看實作設定檔"

    draw.rounded_rectangle([100, 320, 950, 780], radius=18, fill=(28, 16, 40), outline=(236, 72, 153), width=2)
    draw.text((140, 360), f"歡迎訂閱{channel_name}", fill=(255, 255, 255), font=get_font(36, bold=True))
    draw.text((140, 420), channel_desc, fill=(203, 213, 225), font=get_font(24, bold=False))
    
    draw.rounded_rectangle([140, 480, 500, 550], radius=12, fill=(239, 68, 68))
    draw.text((190, 495), "訂閱頻道 & 開啟小鈴鐺", fill=(255, 255, 255), font=get_font(26, bold=True))

    draw.text((140, 580), "• 留言分享你的想法，我會親自回覆交流！", fill=(229, 231, 235), font=get_font(24, bold=False))
    draw.text((140, 630), note_line, fill=(229, 231, 235), font=get_font(24, bold=False))

    # 右側：終端卡 (程式主題) vs 核心精華筆記總結卡 (非程式主題)
    if is_code:
        draw.rounded_rectangle([1000, 320, 1820, 780], radius=18, fill=(16, 24, 38), outline=(56, 189, 248), width=2)
        draw.text((1040, 360), "全自動影音管線運行終端", fill=(56, 189, 248), font=get_font(36, bold=True))
        draw.text((1040, 420), "Core Engine: Python 3.12+ | FFmpeg | Edge-TTS", fill=(148, 163, 184), font=get_font(22, bold=False))
        
        draw.rounded_rectangle([1040, 480, 1780, 740], radius=12, fill=(10, 15, 25))
        draw.text((1070, 510), "$ pip install -r requirements.txt", fill=(52, 211, 153), font=get_font(22, bold=False))
        draw.text((1070, 560), "$ python create_video.py --topic 'AI實戰' --duration 10", fill=(52, 211, 153), font=get_font(22, bold=False))
        draw.text((1070, 610), "$ python web_ui.py", fill=(52, 211, 153), font=get_font(22, bold=False))
        draw.text((1070, 670), ">>> Ready to Launch: 100% Complete!", fill=(56, 189, 248), font=get_font(24, bold=True))
    else:
        # 非程式主題：精華重點總結卡 (絕無程式碼、pip 或終端機指令)
        draw.rounded_rectangle([1000, 320, 1820, 780], radius=18, fill=(16, 24, 38), outline=(56, 189, 248), width=2)
        draw.text((1040, 360), "📌 本集核心精華與實踐指引", fill=(56, 189, 248), font=get_font(36, bold=True))
        draw.text((1040, 420), "Key Takeaways: 認知升級 | 最小行動 | 持續覆盤", fill=(148, 163, 184), font=get_font(22, bold=False))
        
        draw.rounded_rectangle([1040, 480, 1780, 740], radius=12, fill=(10, 15, 25))
        draw.text((1070, 510), "💡 重點 1: 抓準核心槓桿點，拒絕被瑣事耗損精力", fill=(56, 189, 248), font=get_font(22, bold=True))
        draw.text((1070, 560), "🚀 重點 2: 建立五分鐘微啟動機制，降低執行阻力", fill=(74, 222, 128), font=get_font(22, bold=False))
        draw.text((1070, 610), "🔄 重點 3: 每週固定十五分鐘覆盤，實現指數級複利", fill=(250, 204, 21), font=get_font(22, bold=False))
        draw.text((1070, 670), "🎯 實踐行動清單已整理在下方說明欄，歡迎領取！", fill=(244, 114, 182), font=get_font(22, bold=True))

    img.save(out_path, quality=95)

# =========================================================================
# 對外核心調用接口
# =========================================================================

def create_scene_card(
    badge: str,
    title: str,
    subtitle: str,
    bullets: list = None,
    highlight_box: str = None,
    output_path: str = "scene.png",
    width: int = 1920,
    height: int = 1080,
    watermark: str = "AI玩科技 | 2026全自動長片",
    scene_idx: int = 0,
    total_scenes: int = 1,
    sub_idx: int = 0,
    topic: str = ""
):
    """
    智能多樣化場景視覺生成器：
    根據場景序號與分鏡階段，自動選用最契合的專業排版風格，並支援單幕多圖切換，
    徹底終結「影片中圖片不會變」的問題！
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    clean_b = badge or ""

    is_code = is_programming_topic(topic)
    if not is_code and watermark == "AI玩科技 | 2026全自動長片":
        watermark = "精選深度解析 | 實踐指南"

    # 若單一場景有第二視角 (sub_idx == 1)，自動切換到細部架構或實操控制台
    if sub_idx == 1:
        if scene_idx % 2 == 0:
            _render_workflow_style(title, subtitle, badge, bullets, highlight_box, output_path, watermark=watermark, topic=topic)
        else:
            _render_console_style(title, subtitle, badge, bullets, highlight_box, output_path, watermark=watermark, topic=topic)
        return output_path

    # 主視角排版規則
    if scene_idx == 0 or "開場" in clean_b:
        _render_hero_style(title, subtitle, badge, bullets, highlight_box, output_path, watermark=watermark, topic=topic)
    elif scene_idx == total_scenes - 1 or "訂閱" in clean_b or "結尾" in clean_b or "資源" in clean_b:
        _render_summary_style(title, subtitle, badge, bullets, highlight_box, output_path, watermark=watermark, topic=topic)
    elif "架構" in clean_b or "核心" in clean_b or scene_idx % 4 == 1:
        _render_workflow_style(title, subtitle, badge, bullets, highlight_box, output_path, watermark=watermark, topic=topic)
    elif "實戰" in clean_b or "代碼" in clean_b or "步驟" in clean_b or scene_idx % 4 == 2:
        _render_console_style(title, subtitle, badge, bullets, highlight_box, output_path, watermark=watermark, topic=topic)
    elif "效益" in clean_b or "對比" in clean_b or "數據" in clean_b or scene_idx % 4 == 3:
        _render_comparison_style(title, subtitle, badge, bullets, highlight_box, output_path, watermark=watermark, topic=topic)
    else:
        _render_hero_style(title, subtitle, badge, bullets, highlight_box, output_path, watermark=watermark, topic=topic)

    return output_path
