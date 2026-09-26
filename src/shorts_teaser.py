import os
import sys
import time
import argparse
import subprocess
import tempfile
from PIL import Image, ImageDraw

# 確保專案根目錄在 sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import imageio_ffmpeg
from src.visuals import get_font
from src.tts import generate_speech

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
OUTPUT_DIR = "output_videos"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def create_teaser_overlay(w: int = 1080, h: int = 1920, title: str = "AI 自動化生片實戰教學", cta_text: str = None) -> Image.Image:
    """
    繪製 9:16 Shorts 預告專用上下導流圖層 (高對比霓虹卡片)
    """
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # ================= 頂部預告大卡片 =================
    top_card_top = 80
    top_card_bot = 590
    draw.rounded_rectangle([40, top_card_top, w - 40, top_card_bot], radius=24, fill=(15, 23, 42, 235), outline=(239, 68, 68), width=3)
    
    # 預告 Badge
    badge_w = 300
    draw.rounded_rectangle([int(w/2 - badge_w/2), top_card_top + 25, int(w/2 + badge_w/2), top_card_top + 75], radius=12, fill=(239, 68, 68))
    draw.text((int(w/2 - badge_w/2) + 24, top_card_top + 34), "★ 正片精彩預告 TEASER", font=get_font(20), fill=(255, 255, 255))

    # 主標題 (自動折行與過濾特殊 emoji)
    clean_title = title.replace(".mp4", "").replace("AI生成_", "").replace("Shorts預告_", "").strip()
    clean_title = "".join(c for c in clean_title if ord(c) < 0x10000 and not (0x1F300 <= ord(c) <= 0x1FAFF)).strip()
    if len(clean_title) > 40:
        clean_title = clean_title[:40] + "..."

    font_main = get_font(34)
    line1 = clean_title[:20]
    line2 = clean_title[20:40] if len(clean_title) > 20 else ""

    draw.text((80, top_card_top + 105), line1, font=font_main, fill=(255, 255, 255))
    if line2:
        draw.text((80, top_card_top + 160), line2, font=font_main, fill=(56, 189, 248))

    # 副標題說明
    sub_y = top_card_top + (220 if line2 else 170)
    draw.text((80, sub_y), "▶ 完整高畫質實戰課程已在頻道發布！", font=get_font(22), fill=(253, 224, 71))

    # 亮點標籤 Pills
    pill_y = sub_y + 50
    draw.rounded_rectangle([80, pill_y, 340, pill_y + 40], radius=8, fill=(30, 41, 59, 220), outline=(56, 189, 248), width=1)
    draw.text((95, pill_y + 8), "▶ 點擊下方看長片", font=get_font(18), fill=(56, 189, 248))

    draw.rounded_rectangle([360, pill_y, 630, pill_y + 40], radius=8, fill=(30, 41, 59, 220), outline=(168, 85, 247), width=1)
    draw.text((375, pill_y + 8), "◆ 附完整開源配置", font=get_font(18), fill=(168, 85, 247))

    # ================= 底部導流 CTA 卡片 =================
    bot_card_top = 1330
    bot_card_bot = 1820
    draw.rounded_rectangle([40, bot_card_top, w - 40, bot_card_bot], radius=24, fill=(15, 23, 42, 238), outline=(56, 189, 248), width=3)
    
    # 點擊指示按鈕
    raw_cta = cta_text or "點擊主頁看完整正片"
    clean_cta = "".join(c for c in raw_cta if ord(c) < 0x10000 and not (0x1F300 <= ord(c) <= 0x1FAFF)).strip()
    if not clean_cta.startswith("▶"):
        clean_cta = f"▶ {clean_cta}"

    cta_btn_w = 360
    draw.rounded_rectangle([int(w/2 - cta_btn_w/2), bot_card_top + 25, int(w/2 + cta_btn_w/2), bot_card_top + 80], radius=12, fill=(37, 99, 235))
    draw.text((int(w/2 - cta_btn_w/2) + 25, bot_card_top + 35), clean_cta, font=get_font(22), fill=(255, 255, 255))

    draw.text((80, bot_card_top + 105), "想掌握這套全自動工作流？", font=get_font(26), fill=(255, 255, 255))
    draw.text((80, bot_card_top + 155), "完整 1080p 深度教學已全面公開！", font=get_font(24), fill=(52, 211, 153))

    draw.text((80, bot_card_top + 215), "● 免費開源項目與範本完整領取", font=get_font(20), fill=(203, 213, 225))
    draw.text((80, bot_card_top + 258), "● 手把手零門檻實作避坑拆解", font=get_font(20), fill=(203, 213, 225))
    draw.text((80, bot_card_top + 300), "★ 記得按讚、訂閱並開啟小鈴鐺！", font=get_font(20), fill=(253, 224, 71))

    return img

def make_shorts_teaser(
    input_video_path: str,
    duration: float = 30.0,
    output_path: str = None,
    teaser_title: str = None,
    cta_text: str = None
) -> str:
    """
    全自動將任何現有影片（16:9 橫片或任意長度）轉化為 9:16 Shorts 預告片：
    1. 背景：影片動態畫面填滿 1080x1920 並加入模糊羽化 (boxblur)
    2. 主畫面：清晰 16:9 影片置中播放 (y=656)
    3. 上下圖層：正片預告大標題 + 點擊觀看完整正片導流 CTA 卡片
    4. 自動截取前 N 秒精華 (預設 30 秒)
    """
    if not os.path.exists(input_video_path):
        raise FileNotFoundError(f"找不到原始影片：{input_video_path}")

    bname = os.path.basename(input_video_path)
    if not teaser_title:
        # 從檔名解析乾淨標題
        teaser_title = bname.replace(".mp4", "").replace("AI生成_", "").replace("Shorts預告_", "")
        # 去除時長與日期標籤
        parts = teaser_title.split("_")
        teaser_title = parts[0] if parts else teaser_title

    ts = time.strftime("%Y%m%d_%H%M%S")
    clean_slug = "".join(c for c in teaser_title if c.isalnum() or c in ("-", "_"))[:20]
    if not clean_slug:
        clean_slug = "video"

    if not output_path:
        output_path = os.path.join(OUTPUT_DIR, f"Shorts預告_{clean_slug}_{int(duration)}秒_{ts}.mp4")

    # 1. 產生 1080x1920 預告透明遮罩圖層
    overlay_img = create_teaser_overlay(1080, 1920, title=teaser_title, cta_text=cta_text)
    temp_overlay_png = tempfile.mktemp(suffix=".png")
    overlay_img.save(temp_overlay_png)

    # 2. 建構 FFmpeg Filtergraph
    # [bg]: 填滿 1080x1920 並裁切與模糊
    # [fg]: 縮放至 1080:608
    # [vid]: fg 疊加在 bg 中心 (y=656)
    # [v]: 疊加預告遮罩 PNG
    filter_complex = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=28:5[bg];"
        "[0:v]scale=1080:608[fg];"
        "[bg][fg]overlay=0:656[vid];"
        "[vid][1:v]overlay=0:0[v]"
    )

    cmd = [
        FFMPEG_EXE, "-y",
        "-i", input_video_path,
        "-i", temp_overlay_png,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "0:a?",
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        output_path
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"🎉 成功生成 9:16 Shorts 預告片：{output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg 預告片生成失敗：{e.stderr}")
        raise e
    finally:
        if os.path.exists(temp_overlay_png):
            try:
                os.remove(temp_overlay_png)
            except Exception:
                pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="一鍵將長影片製作為 9:16 Shorts 預告短片")
    parser.add_argument("--video", type=str, required=True, help="輸入的影片路徑")
    parser.add_argument("--duration", type=float, default=30.0, help="預告片長度（秒）")
    parser.add_argument("--title", type=str, default=None, help="自訂預告片標題")
    parser.add_argument("--output", type=str, default=None, help="輸出路徑")
    args = parser.parse_args()

    out = make_shorts_teaser(args.video, duration=args.duration, teaser_title=args.title, output_path=args.output)
    print(f"[✔] 完成：{out}")
