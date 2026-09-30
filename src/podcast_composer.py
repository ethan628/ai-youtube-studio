import os
import sys
import math
import subprocess
import tempfile
import re
from datetime import datetime, timedelta
from PIL import Image, ImageDraw
import imageio_ffmpeg

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.tts import generate_speech, DEFAULT_VOICE, FEMALE_VOICE
from src.visuals import get_font, clean_emoji, draw_tech_background, draw_tech_grid
from src.subtitle_utils import optimize_srt_file, get_ffmpeg_subtitles_style, optimize_srt
from src.podcast_generator import generate_podcast_dialogue

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output_videos")

def get_audio_duration(audio_path: str) -> float:
    """使用 ffmpeg 獲取音訊時長（秒）"""
    cmd = [FFMPEG_EXE, "-i", audio_path]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    for line in res.stderr.split("\n"):
        if "Duration:" in line:
            parts = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = parts.split(":")
            return float(h) * 3600 + float(m) * 60 + float(s)
    return 3.0

def draw_vector_mic(draw, cx, cy, color=(255, 255, 255), scale=1.0):
    """繪製高質感向量麥克風圖示（杜絕 Emoji 方框亂碼）"""
    w = int(6 * scale)
    h = int(12 * scale)
    draw.rounded_rectangle([cx - w, cy - h, cx + w, cy + h], radius=int(5 * scale), fill=color)
    draw.arc([cx - int(10 * scale), cy - int(3 * scale), cx + int(10 * scale), cy + int(13 * scale)], 0, 180, fill=color, width=max(2, int(2 * scale)))
    draw.line([(cx, cy + int(13 * scale)), (cx, cy + int(19 * scale))], fill=color, width=max(2, int(2 * scale)))
    draw.line([(cx - int(7 * scale), cy + int(19 * scale)), (cx + int(7 * scale), cy + int(19 * scale))], fill=color, width=max(2, int(2 * scale)))

def draw_vector_avatar(draw, cx, cy, radius, label, color, bg_color):
    """繪製專業科技感主播頭像與名稱 Monogram"""
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=bg_color, outline=color, width=3)
    hr = int(radius * 0.38)
    draw.ellipse([cx - hr, cy - int(radius * 0.65), cx + hr, cy - int(radius * 0.65) + hr * 2], fill=color)
    sw = int(radius * 0.72)
    sh = int(radius * 0.45)
    draw.chord([cx - sw, cy + int(radius * 0.05), cx + sw, cy + int(radius * 0.05) + sh * 2], 180, 360, fill=color)
    badge_w = 34
    draw.rounded_rectangle([cx - badge_w, cy + radius - 16, cx + badge_w, cy + radius + 12], radius=6, fill=(15, 23, 42), outline=color, width=2)
    draw.text((cx - 20, cy + radius - 14), label, fill=(255, 255, 255), font=get_font(18, bold=True))

def render_podcast_background_frame(
    speaker: str,
    title: str,
    subtitle: str,
    output_path: str,
    turn_idx: int = 1,
    total_turns: int = 10,
    width: int = 1920,
    height: int = 1080
) -> str:
    """繪製單一對話輪次的 1080p 錄音室視覺背景（帶發言者光暈高亮指示）"""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    img = Image.new("RGB", (width, height), (10, 15, 29))
    draw = ImageDraw.Draw(img)

    # 科技感底層漸層與格線
    draw_tech_background(draw, width, height, base_color=(10, 15, 29), accent_color=(0, 240, 255))
    draw_tech_grid(draw, width, height, grid_size=70)

    # 頂部主題徽章
    draw.rounded_rectangle([100, 45, 440, 95], radius=10, fill=(20, 35, 60), outline=(0, 240, 255), width=2)
    draw_vector_mic(draw, 125, 70, color=(0, 240, 255), scale=1.1)
    draw.text((148, 56), "AI PODCAST 雙人對談", fill=(0, 240, 255), font=get_font(23, bold=True))
    draw.text((width - 430, 58), "雙AI協同開發 | 2026科技對談", fill=(148, 163, 184), font=get_font(22, bold=False))

    # 大標題與副標題 (過濾 Emoji)
    clean_t = clean_emoji(title)[:28]
    clean_s = clean_emoji(subtitle)[:40]
    draw.text((100, 115), clean_t, fill=(255, 255, 255), font=get_font(50, bold=True))
    draw.text((100, 185), clean_s, fill=(203, 213, 225), font=get_font(26, bold=False))

    # 發言動態色彩分界線
    active_color = (0, 240, 255) if speaker == "Leo" else (168, 85, 247)
    draw.line([(100, 235), (width - 100, 235)], fill=(30, 41, 59), width=2)
    draw.line([(100, 235), (650, 235)], fill=active_color, width=3)

    # ---------------- 主播卡 A：Leo (男主持，左側) ----------------
    card_w, card_h = 560, 360
    c1_x, c1_y = 180, 275
    leo_active = (speaker == "Leo")
    leo_outline = (0, 240, 255) if leo_active else (30, 41, 59)
    leo_bg = (15, 28, 55) if leo_active else (11, 19, 35)

    if leo_active:
        # 呼吸光暈外框
        draw.rounded_rectangle([c1_x - 6, c1_y - 6, c1_x + card_w + 6, c1_y + card_h + 6], radius=22, outline=(0, 240, 255, 100), width=3)
    draw.rounded_rectangle([c1_x, c1_y, c1_x + card_w, c1_y + card_h], radius=18, fill=leo_bg, outline=leo_outline, width=3 if leo_active else 1)

    # Leo 頭像
    draw_vector_avatar(draw, c1_x + card_w // 2, c1_y + 90, 52, "LEO", (0, 240, 255) if leo_active else (70, 90, 120), (20, 45, 90) if leo_active else (18, 28, 48))
    draw.text((c1_x + (card_w - 230) // 2, c1_y + 165), "AI 男主持 (Leo)", fill=(255, 255, 255) if leo_active else (148, 163, 184), font=get_font(30, bold=True))
    draw.text((c1_x + (card_w - 250) // 2, c1_y + 215), "深度技術分析 / 核心推導", fill=(56, 189, 248) if leo_active else (100, 116, 139), font=get_font(21))

    # Leo 麥克風發言狀態膠囊
    pill_w = 230
    p1_x = c1_x + (card_w - pill_w) // 2
    p1_y = c1_y + 270
    if leo_active:
        draw.rounded_rectangle([p1_x, p1_y, p1_x + pill_w, p1_y + 44], radius=22, fill=(16, 185, 129), outline=(52, 211, 153), width=2)
        draw_vector_mic(draw, p1_x + 32, p1_y + 22, color=(255, 255, 255), scale=1.0)
        draw.text((p1_x + 52, p1_y + 10), "正在發言中...", fill=(255, 255, 255), font=get_font(20, bold=True))
    else:
        draw.rounded_rectangle([p1_x, p1_y, p1_x + pill_w, p1_y + 44], radius=22, fill=(20, 30, 45), outline=(40, 55, 75), width=1)
        draw.ellipse([p1_x + 28, p1_y + 17, p1_x + 40, p1_y + 29], fill=(100, 116, 139))
        draw.text((p1_x + 52, p1_y + 10), "靜音聆聽中", fill=(100, 116, 139), font=get_font(20, bold=False))

    # ---------------- 主播卡 B：Mia (女主持，右側) ----------------
    c2_x = width - 180 - card_w
    c2_y = 275
    mia_active = (speaker == "Mia")
    mia_outline = (168, 85, 247) if mia_active else (30, 41, 59)
    mia_bg = (38, 18, 58) if mia_active else (11, 19, 35)

    if mia_active:
        draw.rounded_rectangle([c2_x - 6, c2_y - 6, c2_x + card_w + 6, c2_y + card_h + 6], radius=22, outline=(168, 85, 247, 100), width=3)
    draw.rounded_rectangle([c2_x, c2_y, c2_x + card_w, c2_y + card_h], radius=18, fill=mia_bg, outline=mia_outline, width=3 if mia_active else 1)

    # Mia 頭像
    draw_vector_avatar(draw, c2_x + card_w // 2, c2_y + 90, 52, "MIA", (168, 85, 247) if mia_active else (80, 50, 100), (60, 20, 90) if mia_active else (25, 20, 40))
    draw.text((c2_x + (card_w - 230) // 2, c2_y + 165), "AI 女主持 (Mia)", fill=(255, 255, 255) if mia_active else (148, 163, 184), font=get_font(30, bold=True))
    draw.text((c2_x + (card_w - 250) // 2, c2_y + 215), "實務場景落地 / 痛點解答", fill=(192, 132, 252) if mia_active else (100, 116, 139), font=get_font(21))

    # Mia 麥克風發言狀態膠囊
    p2_x = c2_x + (card_w - pill_w) // 2
    p2_y = c2_y + 270
    if mia_active:
        draw.rounded_rectangle([p2_x, p2_y, p2_x + pill_w, p2_y + 44], radius=22, fill=(168, 85, 247), outline=(216, 180, 254), width=2)
        draw_vector_mic(draw, p2_x + 32, p2_y + 22, color=(255, 255, 255), scale=1.0)
        draw.text((p2_x + 52, p2_y + 10), "正在發言中...", fill=(255, 255, 255), font=get_font(20, bold=True))
    else:
        draw.rounded_rectangle([p2_x, p2_y, p2_x + pill_w, p2_y + 44], radius=22, fill=(20, 30, 45), outline=(40, 55, 75), width=1)
        draw.ellipse([p2_x + 28, p2_y + 17, p2_x + 40, p2_y + 29], fill=(100, 116, 139))
        draw.text((p2_x + 52, p2_y + 10), "靜音聆聽中", fill=(100, 116, 139), font=get_font(20, bold=False))

    # 中央 Studio 對談標誌
    draw.ellipse([width // 2 - 35, 420, width // 2 + 35, 490], fill=(20, 35, 60), outline=(245, 158, 11), width=2)
    draw.text((width // 2 - 12, 438), "&", fill=(250, 204, 21), font=get_font(32, bold=True))

    # 底部音頻波形容器框 (x:140, y:665, w:1640, h:160)
    wave_x = 140
    wave_y = 665
    wave_w = width - 280
    wave_h = 160
    draw.rounded_rectangle([wave_x, wave_y, wave_x + wave_w, wave_y + wave_h], radius=16, fill=(8, 14, 28), outline=(30, 45, 70), width=2)
    draw.text((wave_x + 30, wave_y + 16), "AUDIO FREQUENCY SPECTRUM / 即時跳動聲波", fill=(100, 116, 139), font=get_font(18, bold=True))
    draw.text((wave_x + wave_w - 240, wave_y + 16), f"CURRENT: {speaker.upper()} ({turn_idx}/{total_turns})", fill=active_color, font=get_font(18, bold=True))

    img.save(output_path, quality=95)
    return output_path

def generate_podcast_full(
    topic: str,
    duration_minutes: float = 3.0,
    style: str = "科技趨勢對談",
    custom_dialogue: list = None,
    api_key: str = None
) -> dict:
    """
    全自動雙人 AI 播客完整生成管線：
    1. 生成/解析對話腳本
    2. 雙角色神經擬真語音交替合成 (YunJhe + HsiaoChen)
    3. 實時聲波視覺 (showwaves) + 當前主播高亮燈 (Active Speaker)
    4. 字幕防溢出安全排版
    5. 同時輸出 1080p MP4 影片與標準 MP3 音訊檔
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    clean_topic = topic.strip() or "2026 AI 自動化工作流革命"

    if custom_dialogue and len(custom_dialogue) > 0:
        meta = {
            "title": f"【AI Podcast】{clean_topic}",
            "subtitle": "Leo & Mia 雙主持 ⚡ 深度對談與實務洞察",
            "topic": clean_topic,
            "duration_minutes": duration_minutes,
            "dialogue": custom_dialogue
        }
    else:
        print(f"🧠 [播客編劇] 正在為主題【{clean_topic}】規劃 {duration_minutes} 分鐘雙人深度對談腳本...")
        meta = generate_podcast_dialogue(clean_topic, duration_minutes=duration_minutes, style=style, api_key=api_key)

    dialogue = meta.get("dialogue", [])
    total_turns = len(dialogue)
    print(f"🎙️ [雙主播就位] 本集共有 {total_turns} 句對談，準備啟動高音質語音合成與視覺渲染...")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = re.sub(r'[\/:*?"<>| ]+', '_', clean_topic)[:25]
    final_video = os.path.join(OUTPUT_DIR, f"Podcast_{safe_topic}_{timestamp}.mp4")
    final_audio = os.path.join(OUTPUT_DIR, f"Podcast_{safe_topic}_{timestamp}.mp3")
    final_srt = os.path.join(OUTPUT_DIR, f"Podcast_{safe_topic}_{timestamp}.srt")

    style_sub = get_ffmpeg_subtitles_style(is_vertical=False)

    with tempfile.TemporaryDirectory() as temp_dir:
        turn_clips = []
        turn_audios = []
        all_cues = []
        cumulative_time = 0.0

        for idx, turn in enumerate(dialogue):
            speaker = turn.get("speaker", "Leo")
            text = turn.get("text", "").strip()
            if not text:
                continue

            voice = DEFAULT_VOICE if speaker == "Leo" else FEMALE_VOICE
            turn_audio = os.path.join(temp_dir, f"audio_{idx:03d}.mp3")
            turn_srt = os.path.join(temp_dir, f"sub_{idx:03d}.srt")
            turn_bg = os.path.join(temp_dir, f"bg_{idx:03d}.png")
            turn_clip = os.path.join(temp_dir, f"clip_{idx:03d}.mp4")

            print(f"🎙️ [{idx+1}/{total_turns}] [{speaker}] {text[:30]}...")

            # 1. 產生單句語音
            generate_speech(text, turn_audio, turn_srt, voice=voice)
            dur = get_audio_duration(turn_audio)

            # 2. 繪製帶該發言者高亮的背景
            render_podcast_background_frame(
                speaker=speaker,
                title=meta.get("title", f"【Podcast】{clean_topic}"),
                subtitle=meta.get("subtitle", "Leo & Mia 雙主持 ⚡ 深度對談"),
                output_path=turn_bg,
                turn_idx=idx + 1,
                total_turns=total_turns
            )

            # 3. 處理單句字幕 (增加發言者標記並優化防溢出)
            speaker_color = "00F0FF" if speaker == "Leo" else "A855F7"
            sub_text = f"[{speaker}] {text}"
            raw_cue = f"1\n00:00:00,000 --> 00:00:{int(dur):02d},{int((dur%1)*1000):03d}\n{sub_text}\n"
            opt_cue_str = optimize_srt(raw_cue, is_vertical=False)
            with open(turn_srt, "w", encoding="utf-8") as f:
                f.write(opt_cue_str)

            # 累計全片 SRT 時間
            st_td = timedelta(seconds=cumulative_time)
            et_td = timedelta(seconds=cumulative_time + dur)
            all_cues.append(f"{idx+1}\n{str(st_td)[:11].replace('.', ',')} --> {str(et_td)[:11].replace('.', ',')}\n{sub_text}\n")
            cumulative_time += dur

            # 4. 合成帶即時聲波 (showwaves) 與字幕的片段
            clean_bg = turn_bg.replace("\\", "/")
            clean_audio = turn_audio.replace("\\", "/")
            clean_srt = turn_srt.replace("\\", "/").replace(":", "\\:")
            wave_color = "0x00F0FF|0x38BDF8" if speaker == "Leo" else "0xA855F7|0xE879F9"

            fc = (
                f"[1:a]showwaves=s=1640x120:mode=line:colors={wave_color}:scale=cbrt[wave];"
                f"[0:v][wave]overlay=140:685[vwave];"
                f"[vwave]subtitles='{clean_srt}':force_style='{style_sub}'[outv]"
            )

            cmd = [
                FFMPEG_EXE, "-y",
                "-loop", "1", "-i", clean_bg,
                "-i", clean_audio,
                "-filter_complex", fc,
                "-map", "[outv]", "-map", "1:a",
                "-c:v", "libx264", "-preset", "ultrafast",
                "-c:a", "aac", "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-t", str(dur + 0.15),
                turn_clip
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            turn_clips.append(turn_clip)
            turn_audios.append(turn_audio)

        # ---------------- 合併所有影片片段 ----------------
        print("🎬 正在拼接完整 1080p Podcast 影片...")
        concat_list_video = os.path.join(temp_dir, "concat_video.txt")
        with open(concat_list_video, "w", encoding="utf-8") as f:
            for cp in turn_clips:
                f.write(f"file '{cp.replace(chr(92), '/')}'\n")

        cmd_concat_v = [
            FFMPEG_EXE, "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_list_video,
            "-c", "copy",
            final_video
        ]
        subprocess.run(cmd_concat_v, check=True, capture_output=True)

        # ---------------- 合併所有音軌輸出為獨立 MP3 ----------------
        print("📻 正在匯出獨立 Podcast 音訊檔 (MP3)...")
        concat_list_audio = os.path.join(temp_dir, "concat_audio.txt")
        with open(concat_list_audio, "w", encoding="utf-8") as f:
            for ap in turn_audios:
                f.write(f"file '{ap.replace(chr(92), '/')}'\n")

        cmd_concat_a = [
            FFMPEG_EXE, "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_list_audio,
            "-c:a", "libmp3lame", "-b:a", "192k",
            final_audio
        ]
        subprocess.run(cmd_concat_a, check=True, capture_output=True)

        # ---------------- 匯出完整 SRT 字幕 ----------------
        full_raw_srt = "\n".join(all_cues)
        with open(final_srt, "w", encoding="utf-8") as f:
            f.write(optimize_srt(full_raw_srt, is_vertical=False))

    print(f"🎉 [成功] 1080p Podcast 影片已儲存：{final_video}")
    print(f"🎉 [成功] 獨立 Podcast 音訊已儲存：{final_audio}")

    # 自動註冊進待發布隊列 publish_queue.json
    try:
        from src.youtube_manager import update_publish_queue_metadata
        update_publish_queue_metadata(
            filename=os.path.basename(final_video),
            title=meta.get("title", f"【AI Podcast】{clean_topic}"),
            description=(
                f"🔥 本集 Podcast 深度對談：{clean_topic}\n\n"
                f"由 AI 雙主持 Leo 與 Mia 聯袂呈現，完整拆解核心精華！\n\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🎙️ 雙主持陣容：\n"
                f"👦 Leo：深度技術分析 / 核心推導\n"
                f"👧 Mia：實務場景落地 / 痛點解答\n\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"🔔 記得按讚、訂閱並開啟小鈴鐺，掌握最新 AI 播客與科技趨勢！\n"
                f"#AIPodcast #播客 #科技趨勢 #對談 #2026趨勢"
            ),
            tags=["AIPodcast", "播客", "科技趨勢", "對談", clean_topic[:15]]
        )
    except Exception as e:
        print(f"⚠️ 註冊發布佇列提示: {e}")

    return {
        "success": True,
        "video_path": final_video,
        "audio_path": final_audio,
        "srt_path": final_srt,
        "filename": os.path.basename(final_video),
        "audio_filename": os.path.basename(final_audio),
        "title": meta.get("title", clean_topic),
        "total_turns": total_turns
    }

if __name__ == "__main__":
    test_d = [
        {"speaker": "Leo", "text": "哈囉大家好，我是 Leo！歡迎收聽本期 AI 播客實戰測試！"},
        {"speaker": "Mia", "text": "哈囉我是 Mia！今天我們測試雙主持即時跳動聲波與高亮發言燈效果！"},
        {"speaker": "Leo", "text": "沒錯，整個流程全自動完成，隨時可以一鍵發布！"}
    ]
    res = generate_podcast_full("雙主持AI播客實測", duration_minutes=1.0, custom_dialogue=test_d)
    print("Full result:", res)
