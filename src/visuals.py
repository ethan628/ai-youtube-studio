import os
from PIL import Image, ImageDraw, ImageFont

# Windows default fonts
FONT_BOLD_PATH = "C:\\Windows\\Fonts\\msjhbd.ttc"
FONT_REGULAR_PATH = "C:\\Windows\\Fonts\\msjh.ttc"

def get_font(size: int, bold: bool = True):
    try:
        path = FONT_BOLD_PATH if bold else FONT_REGULAR_PATH
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    except Exception:
        pass
    return ImageFont.load_default()

def draw_gradient_background(draw, width, height, top_color=(10, 15, 29), bottom_color=(5, 8, 16)):
    """繪製深色科技感漸層背景"""
    for y in range(height):
        ratio = y / height
        r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

def draw_tech_grid(draw, width, height, grid_size=60, color=(255, 255, 255, 8)):
    """繪製微弱的科技格線"""
    for x in range(0, width, grid_size):
        draw.line([(x, 0), (x, height)], fill=(20, 35, 60))
    for y in range(0, height, grid_size):
        draw.line([(0, y), (width, y)], fill=(20, 35, 60))

def create_scene_card(
    badge: str,
    title: str,
    subtitle: str,
    bullets: list = None,
    highlight_box: str = None,
    output_path: str = "scene.png",
    width: int = 1920,
    height: int = 1080,
    watermark: str = "雙AI協同開發 ⚡ 2026自動化實戰"
):
    """
    產生高質感科技風簡報／影片畫面
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    img = Image.new("RGB", (width, height), (10, 15, 29))
    draw = ImageDraw.Draw(img)

    # 1. 漸層背景與格線
    draw_gradient_background(draw, width, height, top_color=(15, 23, 42), bottom_color=(3, 7, 18))
    draw_tech_grid(draw, width, height, grid_size=80)

    # 霓虹光暈 (中央裝飾框)
    accent_cyan = (0, 240, 255)
    accent_purple = (168, 85, 247)
    accent_yellow = (250, 204, 21)

    # 2. 水印 / 頻道標籤 (右上角)
    font_watermark = get_font(24, bold=True)
    draw.text((width - 450, 45), watermark, fill=(148, 163, 184), font=font_watermark)

    # 3. 頂部徽章 Badge (例如: 🔥 雙AI協同開發)
    font_badge = get_font(28, bold=True)
    badge_x, badge_y = 100, 70
    badge_bbox = draw.textbbox((badge_x + 20, badge_y + 8), badge, font=font_badge)
    # 畫膠囊背景
    draw.rounded_rectangle(
        [badge_x, badge_y, badge_bbox[2] + 20, badge_bbox[3] + 8],
        radius=12,
        fill=(30, 41, 59),
        outline=accent_cyan,
        width=2
    )
    draw.text((badge_x + 20, badge_y + 8), badge, fill=accent_cyan, font=font_badge)

    # 4. 主標題 (超大粗體)
    font_title = get_font(68, bold=True)
    title_y = 160
    # 發光投影效果
    draw.text((102, title_y + 2), title, fill=(0, 100, 150), font=font_title)
    draw.text((100, title_y), title, fill=(255, 255, 255), font=font_title)

    # 5. 副標題 (次要說明)
    font_sub = get_font(34, bold=False)
    sub_y = title_y + 90
    draw.text((100, sub_y), subtitle, fill=(203, 213, 225), font=font_sub)

    # 分隔發光線
    line_y = sub_y + 60
    draw.line([(100, line_y), (width - 100, line_y)], fill=(51, 65, 85), width=2)
    draw.line([(100, line_y), (500, line_y)], fill=accent_cyan, width=3)

    # 6. 核心內容區塊 (左右分欄或卡片條列)
    content_y = line_y + 40
    if bullets:
        font_bullet = get_font(36, bold=True)
        for i, bullet in enumerate(bullets):
            by = content_y + (i * 85)
            if by + 70 > height - 120:
                break
            # 卡片背景
            card_w = 1100
            draw.rounded_rectangle(
                [100, by, 100 + card_w, by + 68],
                radius=10,
                fill=(15, 23, 42),
                outline=(51, 65, 85),
                width=1
            )
            # 左側發光色條
            bar_color = accent_cyan if i % 2 == 0 else accent_purple
            draw.rectangle([100, by, 110, by + 68], fill=bar_color)
            # 編號圓圈
            draw.ellipse([125, by + 18, 157, by + 50], fill=bar_color)
            font_num = get_font(22, bold=True)
            draw.text((135, by + 22), str(i + 1), fill=(10, 15, 29), font=font_num)
            # 文字
            draw.text((175, by + 16), bullet, fill=(241, 245, 249), font=font_bullet)

    # 7. 右側亮點小卡片 / 代碼框 / 核心成果
    if highlight_box:
        box_x = 1260
        box_y = content_y
        box_w = 560
        box_h = 420
        draw.rounded_rectangle(
            [box_x, box_y, box_x + box_w, box_y + box_h],
            radius=16,
            fill=(17, 24, 39),
            outline=accent_purple,
            width=2
        )
        # 標題欄
        draw.rounded_rectangle([box_x, box_y, box_x + box_w, box_y + 45], radius=16, fill=(31, 41, 55))
        draw.ellipse([box_x + 18, box_y + 16, box_x + 30, box_y + 28], fill=(239, 68, 68))
        draw.ellipse([box_x + 38, box_y + 16, box_x + 50, box_y + 28], fill=(234, 179, 8))
        draw.ellipse([box_x + 58, box_y + 16, box_x + 70, box_y + 28], fill=(34, 197, 94))
        font_box_title = get_font(20, bold=True)
        draw.text((box_x + 85, box_y + 12), "TERMINAL / RESULT", fill=(156, 163, 175), font=font_box_title)

        # 框內文字
        font_box_text = get_font(26, bold=False)
        lines = highlight_box.strip().split("\n")
        line_offset = box_y + 65
        for l in lines:
            color = accent_cyan if ">>>" in l or "$" in l else (229, 231, 235)
            draw.text((box_x + 25, line_offset), l, fill=color, font=font_box_text)
            line_offset += 42

    # 8. 底部預留字幕區指示
    # 底部會由 FFmpeg 自動燒錄字幕

    img.save(output_path, quality=95)
    return output_path

if __name__ == "__main__":
    create_scene_card(
        badge="🔥 雙AI協同開發 EP5",
        title="不寫 Python 也能做！5 分鐘打造個人 AI",
        subtitle="2026 最強自動化工作流，告別手動寫代碼",
        bullets=[
            "三大 AI 協同：Antigravity + Claude + Gemini",
            "零環境配置：自動生成程式碼與排除錯誤",
            "一鍵部署上線：完全免費提供好友測試"
        ],
        highlight_box="$ antigravity run assistant\n>>> Initializing Gemini 3.8...\n>>> Connected to workspace\n>>> Status: 100% READY!\n>>> Video Created!",
        output_path="test_card.png"
    )
    print("Scene card created successfully!")
