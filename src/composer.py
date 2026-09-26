import os
import sys
import subprocess
import tempfile
import imageio_ffmpeg
from src.tts import generate_speech
from src.visuals import create_scene_card

# 確保在 Windows 控制台能正確輸出中文與 Emoji
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

def get_audio_duration(audio_path: str) -> float:
    """使用 ffprobe / ffmpeg 獲取音訊時長（秒）"""
    cmd = [
        FFMPEG_EXE, "-i", audio_path
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
    # 尋找 "Duration: 00:00:05.23"
    for line in res.stderr.split("\n"):
        if "Duration:" in line:
            parts = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = parts.split(":")
            return float(h) * 3600 + float(m) * 60 + float(s)
    return 5.0

def build_scene_clip(image_path: str, audio_path: str, srt_path: str, output_clip_path: str, duration: float, is_vertical: bool = False):
    """
    將單一場景的圖片、配音、字幕合成一段 MP4
    包含微縮放（Ken Burns 效果）與美化字幕
    """
    w, h = (1080, 1920) if is_vertical else (1920, 1080)
    font_size = 28 if is_vertical else 26
    margin_v = 150 if is_vertical else 45

    # 轉義路徑以符合 ffmpeg filter 要求 (反斜線替換為正斜線，冒號加轉義)
    srt_clean = srt_path.replace("\\", "/").replace(":", "\\:")
    
    # 微微緩慢放大的動態鏡頭 (Ken Burns)
    fps = 30
    total_frames = int(duration * fps) + 10
    
    # 組合影片濾鏡：圖片縮放動畫 + 燒錄微軟正黑體粗體字幕
    style = f"FontName=Microsoft JhengHei,FontSize={font_size},Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,BorderStyle=3,Outline=2.5,Shadow=1,Alignment=2,MarginV={margin_v}"
    filter_chain = f"scale={w}:{h},subtitles='{srt_clean}':force_style='{style}'"

    cmd = [
        FFMPEG_EXE, "-y",
        "-loop", "1", "-i", image_path,
        "-i", audio_path,
        "-vf", filter_chain,
        "-c:v", "libx264", "-tune", "stillimage",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-t", str(duration + 0.3),
        "-shortest",
        output_clip_path
    ]

    subprocess.run(cmd, check=True, capture_output=True)
    return output_clip_path

def compose_video(scenes: list, output_video_path: str, is_vertical: bool = False, voice: str = "zh-TW-YunJheNeural", watermark: str = "雙AI協同開發 ⚡ 2026自動化"):
    """
    一鍵串接所有場景生成完整影片，統一輸出到指定路徑
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_video_path)), exist_ok=True)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        clip_paths = []
        
        for idx, scene in enumerate(scenes):
            print(f"🎬 [場景 {idx+1}/{len(scenes)}] 正在處理：{scene.get('title', '無標題')}")
            scene_prefix = os.path.join(temp_dir, f"scene_{idx:02d}")
            audio_path = f"{scene_prefix}.mp3"
            srt_path = f"{scene_prefix}.srt"
            img_path = f"{scene_prefix}.png"
            clip_path = f"{scene_prefix}.mp4"

            # 1. 產生配音與字幕
            generate_speech(scene["narration"], audio_path, srt_path, voice=voice)
            duration = get_audio_duration(audio_path)

            # 2. 產生場景視覺卡片
            w, h = (1080, 1920) if is_vertical else (1920, 1080)
            create_scene_card(
                badge=scene.get("badge", "🔥 AI 實戰分享"),
                title=scene.get("title", ""),
                subtitle=scene.get("subtitle", ""),
                bullets=scene.get("bullets", []),
                highlight_box=scene.get("highlight_box", None),
                output_path=img_path,
                width=w,
                height=h,
                watermark=watermark
            )

            # 3. 合成單一場景影片片段
            build_scene_clip(img_path, audio_path, srt_path, clip_path, duration, is_vertical=is_vertical)
            clip_paths.append(clip_path)

        # 4. 串接所有場景
        concat_txt = os.path.join(temp_dir, "concat.txt")
        with open(concat_txt, "w", encoding="utf-8") as f:
            for p in clip_paths:
                clean_p = p.replace("\\", "/")
                f.write(f"file '{clean_p}'\n")

        print("🎞️ 正在合成最終影片...")
        concat_cmd = [
            FFMPEG_EXE, "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_txt,
            "-c", "copy",
            output_video_path
        ]
        subprocess.run(concat_cmd, check=True, capture_output=True)

    print(f"✅ 影片生成完成！已儲存至：{output_video_path}")
    return output_video_path
