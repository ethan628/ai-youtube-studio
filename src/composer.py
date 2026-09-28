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
    for line in res.stderr.split("\n"):
        if "Duration:" in line:
            parts = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = parts.split(":")
            return float(h) * 3600 + float(m) * 60 + float(s)
    return 5.0

def build_scene_clip(
    image_paths: list,
    audio_path: str,
    srt_path: str,
    output_clip_path: str,
    duration: float,
    is_vertical: bool = False,
    scene_idx: int = 0
):
    """
    合成單一場景影片片段：
    - 支援單幕多圖自動輪播切換 (徹底解決「圖片不會變」的問題)
    - 支援 Ken Burns 微縮放/平移動態鏡頭
    - 支援微軟正黑體/Noto Sans CJK TC 高清美化字幕
    """
    w, h = (1080, 1920) if is_vertical else (1920, 1080)
    font_size = 28 if is_vertical else 26
    margin_v = 150 if is_vertical else 45
    font_name = "Microsoft JhengHei" if sys.platform.startswith("win") else "Noto Sans CJK TC"

    srt_clean = srt_path.replace("\\", "/").replace(":", "\\:")
    style = f"FontName={font_name},FontSize={font_size},Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,BorderStyle=3,Outline=2.5,Shadow=1,Alignment=2,MarginV={margin_v}"

    fps = 25

    # 情況 A：單張圖 (時長較短，或只有 1 張圖)
    if len(image_paths) <= 1:
        img_p = image_paths[0] if image_paths else "scene.png"
        total_frames = int((duration + 0.3) * fps) + 5

        # 偶數場景緩慢推進，奇數場景緩慢拉遠
        if scene_idx % 2 == 0:
            zp = f"zoompan=z='min(zoom+0.0004,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={w}x{h}:fps={fps}"
        else:
            zp = f"zoompan=z='max(1.06-0.0004*on,1.0)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={total_frames}:s={w}x{h}:fps={fps}"

        fc = f"[0:v]scale={w}:{h},{zp},subtitles='{srt_clean}':force_style='{style}'[outv]"

        cmd = [
            FFMPEG_EXE, "-y",
            "-i", img_p,
            "-i", audio_path,
            "-filter_complex", fc,
            "-map", "[outv]", "-map", "1:a",
            "-c:v", "libx264", "-preset", "veryfast",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-t", str(duration + 0.3),
            output_clip_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return output_clip_path

    # 情況 B：兩張圖輪播切換 (每張圖平分時長，並持續燃燒字幕)
    dur1 = round(duration / 2, 2)
    dur2 = round(duration - dur1, 2)
    frames1 = int(dur1 * fps)
    frames2 = int((dur2 + 0.3) * fps)

    fc = (
        f"[0:v]scale={w}:{h},zoompan=z='min(zoom+0.0005,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames1}:s={w}x{h}:fps={fps}[v0];"
        f"[1:v]scale={w}:{h},zoompan=z='max(1.06-0.0005*on,1.0)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames2}:s={w}x{h}:fps={fps}[v1];"
        f"[v0][v1]concat=n=2:v=1:a=0[vcat];"
        f"[vcat]subtitles='{srt_clean}':force_style='{style}'[outv]"
    )

    cmd = [
        FFMPEG_EXE, "-y",
        "-i", image_paths[0],
        "-i", image_paths[1],
        "-i", audio_path,
        "-filter_complex", fc,
        "-map", "[outv]", "-map", "2:a",
        "-t", str(duration + 0.3),
        "-c:v", "libx264", "-preset", "veryfast",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        output_clip_path
    ]

    subprocess.run(cmd, check=True, capture_output=True)
    return output_clip_path

def compose_video(scenes: list, output_video_path: str, is_vertical: bool = False, voice: str = "zh-TW-YunJheNeural", watermark: str = "AI玩科技 | 2026全自動長片"):
    """
    一鍵串接所有場景生成完整影片，統一輸出到指定路徑
    包含：
    - 多樣化視覺排版與圖形主題生成
    - 單幕多圖切換（依語音長度自動補入第二視角畫面，確保畫面持續變化）
    - Ken Burns 動態鏡頭
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_video_path)), exist_ok=True)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        clip_paths = []
        total_scenes = len(scenes)

        for idx, scene in enumerate(scenes):
            print(f"🎬 [場景 {idx+1}/{total_scenes}] 正在處理：{scene.get('title', '無標題')}")
            scene_prefix = os.path.join(temp_dir, f"scene_{idx:02d}")
            audio_path = f"{scene_prefix}.mp3"
            srt_path = f"{scene_prefix}.srt"
            clip_path = f"{scene_prefix}.mp4"

            # 1. 產生配音與字幕
            generate_speech(scene["narration"], audio_path, srt_path, voice=voice)
            duration = get_audio_duration(audio_path)

            # 2. 智能產生場景視覺畫面：若時長超過 8 秒，自動生成 2 張不同視角視覺圖！
            w, h = (1080, 1920) if is_vertical else (1920, 1080)
            img_path_a = f"{scene_prefix}_a.png"
            create_scene_card(
                badge=scene.get("badge", "AI 實戰分享"),
                title=scene.get("title", ""),
                subtitle=scene.get("subtitle", ""),
                bullets=scene.get("bullets", []),
                highlight_box=scene.get("highlight_box", scene.get("code", None)),
                output_path=img_path_a,
                width=w,
                height=h,
                watermark=watermark,
                scene_idx=idx,
                total_scenes=total_scenes,
                sub_idx=0
            )

            image_paths = [img_path_a]

            if duration > 8.0:
                # 生成第二視角圖 (sub_idx = 1)，例如細部架構或實操終端機
                img_path_b = f"{scene_prefix}_b.png"
                create_scene_card(
                    badge=scene.get("badge", "細節探討"),
                    title=f"深入解析：{scene.get('title', '')[:20]}",
                    subtitle=scene.get("subtitle", "核心機制與實作關鍵拆解"),
                    bullets=scene.get("bullets", []),
                    highlight_box=scene.get("highlight_box", scene.get("code", None)),
                    output_path=img_path_b,
                    width=w,
                    height=h,
                    watermark=watermark,
                    scene_idx=idx,
                    total_scenes=total_scenes,
                    sub_idx=1
                )
                image_paths.append(img_path_b)

            # 3. 合成單一場景影片片段 (帶動態畫面與轉場)
            build_scene_clip(image_paths, audio_path, srt_path, clip_path, duration, is_vertical=is_vertical, scene_idx=idx)
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
