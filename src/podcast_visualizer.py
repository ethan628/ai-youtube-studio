import os
import sys
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
from src.visuals import get_font, draw_gradient_background, draw_tech_grid

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

def create_podcast_background(title: str, subtitle: str, output_img_path: str, width: int = 1920, height: int = 1080):
    """
    繪製 NotebookLM 專用的 AI Podcast 科技對談視覺背景
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_img_path)), exist_ok=True)
    img = Image.new("RGB", (width, height), (10, 15, 29))
    draw = ImageDraw.Draw(img)

    # 深色漸層與格線
    draw_gradient_background(draw, width, height, top_color=(15, 23, 42), bottom_color=(3, 7, 18))
    draw_tech_grid(draw, width, height, grid_size=70)

    accent_cyan = (0, 240, 255)
    accent_purple = (168, 85, 247)
    accent_gold = (250, 204, 21)

    # 1. 頂部徽章
    font_badge = get_font(26, bold=True)
    badge_text = "Google NotebookLM 深度對談"
    draw.rounded_rectangle([100, 50, 480, 95], radius=10, fill=(30, 41, 59), outline=accent_cyan, width=2)
    draw.text((120, 58), badge_text, fill=accent_cyan, font=font_badge)

    # 水印
    font_wm = get_font(22, bold=False)
    draw.text((width - 380, 60), "雙AI協同開發 | AI實戰系列", fill=(148, 163, 184), font=font_wm)

    # 2. 標題與主題
    font_title = get_font(60, bold=True)
    draw.text((100, 125), title, fill=(255, 255, 255), font=font_title)

    font_sub = get_font(30, bold=False)
    draw.text((100, 205), subtitle, fill=(203, 213, 225), font=font_sub)

    # 分隔線
    draw.line([(100, 260), (width - 100, 260)], fill=(51, 65, 85), width=2)
    draw.line([(100, 260), (600, 260)], fill=accent_cyan, width=3)

    # 3. 雙主持人形像卡片 (NotebookLM 經典男女雙主持)
    # 主持人 A
    card_w, card_h = 500, 360
    card1_x, card1_y = 200, 300
    draw.rounded_rectangle([card1_x, card1_y, card1_x + card_w, card1_y + card_h], radius=16, fill=(15, 23, 42), outline=accent_cyan, width=2)
    # 頭像示意圓形
    draw.ellipse([card1_x + 190, card1_y + 40, card1_x + 310, card1_y + 160], fill=(30, 58, 138), outline=accent_cyan, width=3)
    font_avatar = get_font(36, bold=True)
    draw.text((card1_x + 225, card1_y + 75), "AI", fill=accent_cyan, font=font_avatar)
    
    font_host = get_font(34, bold=True)
    draw.text((card1_x + 175, card1_y + 185), "AI 男主持 (Leo)", fill=(241, 245, 249), font=font_host)
    font_role = get_font(24, bold=False)
    draw.text((card1_x + 180, card1_y + 240), "深度技術分析 / 核心推導", fill=(148, 163, 184), font=font_role)
    # 麥克風指示
    draw.rounded_rectangle([card1_x + 160, card1_y + 290, card1_x + 340, card1_y + 330], radius=8, fill=(16, 185, 129))
    font_mic = get_font(20, bold=True)
    draw.text((card1_x + 195, card1_y + 298), "● ON AIR 直播中", fill=(255, 255, 255), font=font_mic)

    # VS 或 連結圖示
    font_vs = get_font(42, bold=True)
    draw.text((width // 2 - 25, 450), "&", fill=accent_gold, font=font_vs)

    # 主持人 B
    card2_x, card2_y = width - 200 - card_w, 300
    draw.rounded_rectangle([card2_x, card2_y, card2_x + card_w, card2_y + card_h], radius=16, fill=(15, 23, 42), outline=accent_purple, width=2)
    draw.ellipse([card2_x + 190, card2_y + 40, card2_x + 310, card2_y + 160], fill=(88, 28, 135), outline=accent_purple, width=3)
    draw.text((card2_x + 225, card2_y + 75), "AI", fill=accent_purple, font=font_avatar)
    draw.text((card2_x + 170, card2_y + 185), "AI 女主持 (Mia)", fill=(241, 245, 249), font=font_host)
    draw.text((card2_x + 175, card2_y + 240), "實務場景落地 / 痛點解答", fill=(148, 163, 184), font=font_role)
    draw.rounded_rectangle([card2_x + 160, card2_y + 290, card2_x + 340, card2_y + 330], radius=8, fill=(16, 185, 129))
    draw.text((card2_x + 195, card2_y + 298), "● ON AIR 直播中", fill=(255, 255, 255), font=font_mic)

    # 4. 音頻波形外框 (放置在底部 720~980 高度區間)
    draw.rounded_rectangle([150, 710, width - 150, 980], radius=16, fill=(11, 19, 38), outline=(51, 65, 85), width=2)
    font_wave_label = get_font(22, bold=True)
    draw.text((180, 725), "AUDIO WAVEFORM / 即時動態聲波分析", fill=(148, 163, 184), font=font_wave_label)

    img.save(output_img_path, quality=95)
    return output_img_path

def convert_audio_to_podcast_video(audio_path: str, output_video_path: str, title: str = "Google NotebookLM 深度對談", subtitle: str = "AI 雙主講精華提煉與洞察"):
    """
    將音訊與即時動態音波 (Waveform) 合成為 YouTube 影片
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_video_path)), exist_ok=True)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        bg_img = os.path.join(temp_dir, "podcast_bg.png")
        create_podcast_background(title, subtitle, bg_img)

        # 動態聲波長寬與位置
        # 背景中波形區域位置為 x=180, y=770, w=1560, h=180
        clean_bg = bg_img.replace("\\", "/")
        clean_audio = audio_path.replace("\\", "/")

        filter_complex = (
            f"[1:a]showwaves=s=1560x170:mode=line:colors=0x00F0FF|0xA855F7:scale=cbrt[wave];"
            f"[0:v][wave]overlay=180:770:shortest=1[outv]"
        )

        cmd = [
            FFMPEG_EXE, "-y",
            "-loop", "1", "-i", clean_bg,
            "-i", clean_audio,
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", "1:a",
            "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            output_video_path
        ]

        print(f"🎙️ 正在將音訊轉換為 Podcast 視覺影片：{os.path.basename(audio_path)} ...")
        subprocess.run(cmd, check=True, capture_output=True)

    print(f"✅ NotebookLM Podcast 影片生成完畢！儲存於：{output_video_path}")
    return output_video_path

if __name__ == "__main__":
    test_audio = "test.mp3"
    from src.tts import generate_speech
    generate_speech("這是 NotebookLM 的測試語音對談，歡迎收聽本期專題！", test_audio)
    convert_audio_to_podcast_video(test_audio, "output_videos/test_podcast.mp4", "AI 時代的工作流革命", "如何用 AI 協同提升 10 倍效率")
    if os.path.exists(test_audio):
        os.remove(test_audio)
