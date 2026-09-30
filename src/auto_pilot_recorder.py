import os
import sys
import math
import time
import shutil
import subprocess
import tempfile

# 確保專案根目錄在 sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg
from src.visuals import get_font
from src.tts import generate_speech

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
RECORDINGS_DIR = "output_recordings"

# 確保輸出目錄存在
os.makedirs(RECORDINGS_DIR, exist_ok=True)

def ease_in_out(t: float) -> float:
    """平滑緩動插值 (0.0 ~ 1.0)"""
    return 0.5 * (1 - math.cos(math.pi * t))

def draw_mouse_cursor(draw: ImageDraw.ImageDraw, x: int, y: int, click_anim: float = 0.0):
    """繪製高質感 macOS / Windows 風格滑鼠指標與點擊波紋"""
    if click_anim > 0:
        r = int(10 + click_anim * 25)
        alpha = int(255 * (1.0 - click_anim))
        draw.ellipse([x - r, y - r, x + r, y + r], outline=(56, 189, 248, alpha), width=3)
        if click_anim < 0.5:
            r_inner = int(6 + click_anim * 15)
            draw.ellipse([x - r_inner, y - r_inner, x + r_inner, y + r_inner], outline=(168, 85, 247, alpha), width=2)
    
    # 經典箭頭指標多邊形
    poly = [
        (x, y),
        (x, y + 24),
        (x + 6, y + 19),
        (x + 12, y + 28),
        (x + 16, y + 26),
        (x + 10, y + 17),
        (x + 18, y + 17)
    ]
    draw.polygon(poly, fill=(255, 255, 255, 255), outline=(15, 23, 42, 255))

import wave
import struct
import random
import array

def generate_typing_wav(output_path: str, duration: float, intervals: list):
    """
    純 Python 毫秒級生成逼真的機械鍵盤敲擊音效音軌 (Click-Clack Soundscape)。
    在指定的時間區間產生隨機間隔與頻率微變化的鍵盤敲擊聲音與 Enter 確定聲。
    採用 array 串流加速，並僅在有打字行為的有效時間段生成樣本，超長影片（如60分鐘）亦毫秒級生成。
    """
    sample_rate = 44100
    max_interval_end = max([t[1] for t in intervals] + [0.0])
    effective_dur = min(duration, max(5.0, max_interval_end + 1.0))
    total_samples = int(effective_dur * sample_rate)
    samples = [0] * total_samples

    for (start_t, end_t) in intervals:
        t = max(0.0, start_t)
        while t < min(effective_dur, end_t):
            click_samples = int(0.035 * sample_rate)
            base_idx = int(t * sample_rate)
            freq = random.uniform(1800, 3200)
            vol = random.uniform(0.35, 0.65)
            for i in range(click_samples):
                if base_idx + i < total_samples:
                    decay = math.exp(-i / (sample_rate * 0.008))
                    noise = (random.random() * 2 - 1) * 0.35
                    tone = math.sin(2 * math.pi * freq * (i / sample_rate)) * 0.65
                    val = int((tone + noise) * decay * vol * 32767)
                    samples[base_idx + i] = max(-32768, min(32767, samples[base_idx + i] + val))
            # 人類自然手速間隔 80ms ~ 160ms
            t += random.uniform(0.08, 0.16)

        # 在區間結束時加入一個稍微沉穩的 Enter 鍵敲擊聲
        enter_idx = int(min(effective_dur - 0.05, end_t) * sample_rate)
        if 0 <= enter_idx < total_samples:
            for i in range(int(0.05 * sample_rate)):
                if enter_idx + i < total_samples:
                    decay = math.exp(-i / (sample_rate * 0.012))
                    tone = math.sin(2 * math.pi * 950 * (i / sample_rate)) * 0.8
                    val = int(tone * decay * 32767)
                    samples[enter_idx + i] = max(-32768, min(32767, samples[enter_idx + i] + val))

    raw_bytes = array.array('h', samples).tobytes()
    with wave.open(output_path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(raw_bytes)

def build_complete_audio(output_audio_path: str, duration: float, narration_text: str, typing_intervals: list):
    """
    合成完整多軌音訊：微軟自然神經語音配音 + 機械鍵盤敲擊音效，嚴格維持與影片 100% 同步的時長。
    使用 apad 自動補齊靜音至精確秒數，避免生成巨型空白音訊佔據記憶體。
    """
    sfx_wav = tempfile.mktemp(suffix=".wav")
    generate_typing_wav(sfx_wav, duration, typing_intervals)
    speech_mp3 = tempfile.mktemp(suffix=".mp3")
    has_speech = False

    if narration_text and narration_text.strip():
        try:
            generate_speech(narration_text, speech_mp3)
            if os.path.exists(speech_mp3) and os.path.getsize(speech_mp3) > 1000:
                has_speech = True
        except Exception as e:
            print(f"⚠️ 語音配音合成異常 ({e})，採用鍵盤打字音效音軌。")

    try:
        if has_speech:
            cmd = [
                FFMPEG_EXE, "-y",
                "-i", sfx_wav,
                "-i", speech_mp3,
                "-filter_complex", f"[0:a]volume=0.45[sfx]; [1:a]volume=1.35[spk]; [sfx][spk]amix=inputs=2:duration=longest:dropout_transition=2,apad=whole_dur={duration:.2f}[aout]",
                "-map", "[aout]",
                "-t", f"{duration:.2f}",
                "-c:a", "aac",
                "-b:a", "192k",
                output_audio_path
            ]
        else:
            cmd = [
                FFMPEG_EXE, "-y",
                "-i", sfx_wav,
                "-af", f"apad=whole_dur={duration:.2f}",
                "-t", f"{duration:.2f}",
                "-c:a", "aac",
                "-b:a", "192k",
                output_audio_path
            ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finally:
        for p in (sfx_wav, speech_mp3):
            if os.path.exists(p):
                try: os.remove(p)
                except Exception: pass

def draw_subtitle_banner(draw: ImageDraw.ImageDraw, w: int, h: int, text: str, is_vertical: bool = False):
    """繪製影片底部高質感半透明浮動字幕膠囊（支援多行自適應與螢幕安全邊界保護，絕不溢出畫面）"""
    if not text or not text.strip():
        return
    clean_sub = text.strip()
    from src.subtitle_utils import wrap_two_lines

    max_line_chars = 14 if is_vertical else 26
    wrapped_sub = wrap_two_lines(clean_sub, max_line_units=max_line_chars * 2)
    sub_lines = wrapped_sub.split("\n")

    sub_font = get_font(21 if not is_vertical else 18)
    line_bboxes = [draw.textbbox((0, 0), f"[解說] {line}" if i == 0 else line, font=sub_font) for i, line in enumerate(sub_lines)]
    max_tw = max(bb[2] - bb[0] for bb in line_bboxes)
    single_th = max(bb[3] - bb[1] for bb in line_bboxes)

    # 確保寬度絕不超出螢幕左右邊界 (左右各留安全邊距)
    card_w = min(w - 80, max(460, max_tw + 60))
    card_h = 56 if len(sub_lines) == 1 else 92
    card_x = (w - card_w) // 2
    if not is_vertical:
        card_y = (h - 90) if len(sub_lines) == 1 else (h - 125)
    else:
        card_y = (h - 140) if len(sub_lines) == 1 else (h - 175)

    # 半透明深藍黑背景膠囊，帶青藍色邊框
    draw.rounded_rectangle([card_x, card_y, card_x + card_w, card_y + card_h], radius=14, fill=(10, 15, 29), outline=(56, 189, 248), width=2)
    
    # 繪製各行解說文字 (居中排版)
    for i, line in enumerate(sub_lines):
        line_str = f"[解說] {line}" if i == 0 else line
        lbb = line_bboxes[i]
        ltw = lbb[2] - lbb[0]
        ly = (card_y + 14 + (i * (single_th + 8))) if len(sub_lines) > 1 else (card_y + (card_h - single_th) // 2 - 2)
        lx = card_x + (card_w - ltw) // 2
        draw.text((lx, ly), line_str, font=sub_font, fill=(255, 255, 255))

def draw_speed_hud_badge(draw: ImageDraw.ImageDraw, w: int, h: int, speed: float, frame_idx: int, fps: int):
    """繪製右上角 HUD 快轉倍速動態標籤"""
    if speed <= 1.0:
        return
    hud_w, hud_h = 160, 36
    hud_x = w - hud_w - 75
    hud_y = 60
    # 閃爍呼吸點
    dot_color = (239, 68, 68) if (frame_idx // max(1, (fps // 2))) % 2 == 0 else (245, 158, 11)
    draw.rounded_rectangle([hud_x, hud_y, hud_x + hud_w, hud_y + hud_h], radius=8, fill=(15, 23, 42, 230), outline=(245, 158, 11), width=2)
    draw.ellipse([hud_x + 12, hud_y + 12, hud_x + 24, hud_y + 24], fill=dot_color)
    draw.text((hud_x + 32, hud_y + 8), f">> {speed:g}X 快轉中", font=get_font(15), fill=(251, 191, 36))

def export_vtt_subtitles(vtt_path: str, cues: list):
    """導出標準 WebVTT 字幕檔供網頁播放器動態載入"""
    with open(vtt_path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for idx, cue in enumerate(cues, 1):
            s_m, s_s = divmod(cue["start"], 60)
            s_h, s_m = divmod(s_m, 60)
            e_m, e_s = divmod(cue["end"], 60)
            e_h, e_m = divmod(e_m, 60)
            start_str = f"{int(s_h):02d}:{int(s_m):02d}:{s_s:06.3f}"
            end_str = f"{int(e_h):02d}:{int(e_m):02d}:{e_s:06.3f}"
            f.write(f"{idx}\n{start_str} --> {end_str}\n{cue['text']}\n\n")

def create_window_base(w: int, h: int, title: str, app_type: str = "terminal") -> Image.Image:
    """建立 macOS 現代風格應用程式視窗底圖"""
    base = Image.new("RGBA", (w, h), (15, 23, 42, 255))
    draw = ImageDraw.Draw(base)

    # 視窗邊界與圓角矩形
    pad_x, pad_y = 60, 50
    win_w, win_h = w - pad_x * 2, h - pad_y * 2
    
    bg_color = (15, 20, 32) if app_type == "terminal" else (24, 30, 48)
    draw.rounded_rectangle([pad_x, pad_y, pad_x + win_w, pad_y + win_h], radius=16, fill=bg_color, outline=(51, 65, 85), width=2)

    # 頂部標題列
    header_h = 52
    draw.rounded_rectangle([pad_x, pad_y, pad_x + win_w, pad_y + header_h], radius=16, fill=(30, 41, 59))
    draw.rectangle([pad_x, pad_y + header_h - 10, pad_x + win_w, pad_y + header_h], fill=(30, 41, 59))
    draw.line([pad_x, pad_y + header_h, pad_x + win_w, pad_y + header_h], fill=(51, 65, 85), width=1)

    # 交通燈三色按鈕 (紅黃綠)
    btn_y = pad_y + 18
    draw.ellipse([pad_x + 22, btn_y, pad_x + 36, btn_y + 14], fill=(239, 68, 68))
    draw.ellipse([pad_x + 44, btn_y, pad_x + 58, btn_y + 14], fill=(245, 158, 11))
    draw.ellipse([pad_x + 66, btn_y, pad_x + 80, btn_y + 14], fill=(34, 197, 94))

    # 標題與圖示
    font_title = get_font(18)
    icon_prefix = ">_ " if app_type == "terminal" else ("[Web] " if app_type == "browser" else "[Code] ")
    draw.text((pad_x + 110, pad_y + 14), f"{icon_prefix}{title}", font=font_title, fill=(226, 232, 240))

    if app_type == "terminal":
        # 標註終端機目前目錄與 Git 狀態
        draw.text((pad_x + win_w - 280, pad_y + 16), "zsh · ~/ai-workspace · (main)", font=get_font(14), fill=(148, 163, 184))
    elif app_type == "browser":
        # 網址列背景
        url_box_w = min(600, win_w - 400)
        url_x = pad_x + 250
        draw.rounded_rectangle([url_x, pad_y + 10, url_x + url_box_w, pad_y + 40], radius=8, fill=(15, 23, 42), outline=(71, 85, 105), width=1)
        draw.text((url_x + 14, pad_y + 16), "https://ai-studio.local/workspace", font=get_font(14), fill=(56, 189, 248))

    return base

# -------------------------------------------------------------
# 模式一：終端機命令列全自動操作錄製 (Terminal Auto-Pilot)
# -------------------------------------------------------------
def render_terminal_recording(
    title: str = "AI 影片自動化管線一鍵啟動",
    commands: list = None,
    duration: float = 15.0,
    output_path: str = None,
    narration_text: str = None,
    is_vertical: bool = False,
    speed: float = 1.0,
    show_subtitles: bool = True,
    enable_audio: bool = True
) -> str:
    """
    全自動模擬工程師/創作者在終端機輸入指令、跑程式、即時日誌捲動與游標操作。
    動態支援 1~6 條自訂步驟指令，時長支援 5 秒 ~ 3600 秒 (60分鐘完整長片)，
    內建機械鍵盤敲擊音效、微軟神經自然配音、多步驟同步動態字幕與快轉倍速 HUD。
    """
    w, h = (1080, 1920) if is_vertical else (1920, 1080)
    fps = 24 if duration <= 60 else (16 if duration <= 300 else (8 if duration <= 900 else 4))
    total_frames = int(duration * fps)

    # 智慧標準化 commands
    norm_cmds = []
    if not commands:
        norm_cmds = [
            {"cmd": "python3 --version", "logs": ["Python 3.14.4 (繁中標準開發環境就緒)", "GCC 13.2.0 on linux x86_64", "[OK] Python 解譯器運行正常"], "narration": "第一步先在終端機確認 Python 3 開發環境，確保解譯器正確安裝。"},
            {"cmd": 'python3 -c "print(\'Hello, Python 2026 AI Studio!\')"', "logs": ["Hello, Python 2026 AI Studio!", "[OK] 互動式語法執行成功，毫秒級輸出！"], "narration": "接著透過單行指令執行第一支程式，輸出 Hello Python，驗證語法執行引擎運作正常！"},
            {"cmd": "python3 -c \"skills = ['變數', '迴圈', 'AI串接']; print(f'[實戰] 核心技能：{skills}')\"", "logs": ["[實戰] 核心技能：['變數', '迴圈', 'AI串接']", "[OK] Python 學習腳本 100% 執行成功！"], "narration": "現在建立實戰腳本，定義核心技能清單並驗收成果，輕鬆掌握完整工作流！"}
        ]
    else:
        for c in commands:
            if isinstance(c, dict) and "cmd" in c:
                norm_cmds.append(c)
            elif isinstance(c, str) and c.strip():
                cmd_s = c.strip()
                if "python" in cmd_s and "--version" in cmd_s:
                    logs = ["Python 3.14.4 (繁體中文開發環境已就緒)", "GCC 13.2.0 on linux x86_64", "[OK] Python 運行正常"]
                    narr = "第一步先在終端機確認 Python 3 開發環境。"
                elif "print" in cmd_s:
                    logs = ["Hello, Python 2026 AI Studio!", "[OK] 語法執行成功，毫秒級響應"]
                    narr = "接著我們執行程式代碼，驗證輸出與運算正確。"
                elif "learn_python" in cmd_s or ".py" in cmd_s:
                    logs = ["第1講：掌握 變數宣告", "第2講：掌握 迴圈控制", "第3講：掌握 AI自動化", "[OK] Python 學習腳本 100% 執行成功！"]
                    narr = "編譯並執行實戰腳本，終端機瞬間回傳成功狀態！"
                elif "docker" in cmd_s:
                    logs = ["Docker version 27.1.1, build 6312e80", "[OK] 容器守護進程運行中"]
                    narr = "檢查 Docker 容器引擎與守護進程運行狀態。"
                elif "git" in cmd_s:
                    logs = ["位於分支 main", "您的分支與上游分支 'origin/main' 一致。", "無未追蹤的檔案，工作區乾淨 [OK]"]
                    narr = "執行 Git 版本控制命令，確保程式碼庫維持最新一致。"
                else:
                    logs = [f"[執行] {cmd_s[:42]}", "狀態: 100% 完成 [OK]"]
                    narr = f"執行命令：{cmd_s[:30]}"
                norm_cmds.append({"cmd": cmd_s, "logs": logs, "narration": narr})

    if not norm_cmds:
        norm_cmds = [{"cmd": "python3 --version", "logs": ["Python 3.14.4 (繁中標準環境就緒)", "[OK] 系統環境正常"], "narration": "確認執行環境就緒。"}]

    if not output_path:
        ts = int(time.time())
        output_path = os.path.join(RECORDINGS_DIR, f"autopilot_terminal_{ts}.mp4")

    num_cmds = len(norm_cmds)
    # 人類真實自然節奏：在長片中將展示集中於前段，避免指令之間出現數百秒空白延遲
    active_demo_sec = min(duration * 0.75, max(12.0, num_cmds * 5.5 / max(1.0, speed)))
    slice_sec = active_demo_sec / num_cmds

    # 記錄每個指令的時間區間與打字區間
    step_intervals = []
    typing_intervals = []
    vtt_cues = []

    for k, c_item in enumerate(norm_cmds):
        start_sec = min(1.0, duration * 0.03) + k * slice_sec
        end_sec = start_sec + slice_sec
        cmd_text = c_item["cmd"]
        
        # 打字所需時間
        type_sec = min(slice_sec * 0.50, max(1.5, len(cmd_text) * 0.07 / max(1.0, speed)))
        type_end_sec = min(end_sec - 0.2, start_sec + type_sec)

        t_start = start_sec / max(0.1, duration)
        t_type_end = type_end_sec / max(0.1, duration)
        t_end = end_sec / max(0.1, duration)

        typing_intervals.append((start_sec, type_end_sec))
        step_intervals.append({
            "step": k + 1,
            "cmd": cmd_text,
            "logs": c_item.get("logs", []),
            "t_start": t_start,
            "t_type_end": t_type_end,
            "t_end": t_end,
            "start_sec": start_sec,
            "type_end_sec": type_end_sec,
            "end_sec": end_sec,
            "narration": c_item.get("narration", "")
        })

        sub_desc = c_item.get("narration") or f"執行指令：{cmd_text[:40]}"
        vtt_cues.append({
            "start": start_sec,
            "end": end_sec,
            "text": f"[步驟 {k+1}/{num_cmds}] {sub_desc}"
        })

    last_end = step_intervals[-1]["end_sec"] if step_intervals else 0.0
    if duration > last_end:
        vtt_cues.append({
            "start": last_end,
            "end": duration,
            "text": f"[完成] 【{title}】自動化操作教學 100% 執行成功！"
        })

    # 準備字型
    font_mono = get_font(20 if not is_vertical else 18)
    font_badge = get_font(16)

    temp_raw_video = tempfile.mktemp(suffix=".mp4")
    cmd_ffmpeg = [
        FFMPEG_EXE, "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{w}x{h}",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-r", "24",
        temp_raw_video
    ]
    proc = subprocess.Popen(cmd_ffmpeg, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    base_img = create_window_base(w, h, title, "terminal")
    content_x = 100
    start_y = 130
    line_h = 32

    # 模擬滑鼠移動關鍵點
    mouse_waypoints = [
        (w * 0.85, h * 0.85),
        (content_x + 280, start_y + 15),
        (content_x + 380, start_y + 160),
        (content_x + 460, start_y + 320),
        (w * 0.9, h * 0.2)
    ]

    prompt_colors = [(56, 189, 248), (168, 85, 247), (52, 211, 153), (251, 191, 36), (244, 63, 94)]
    cached_static_bytes = None
    last_end = step_intervals[-1]["end_sec"] if step_intervals else 0.0

    for frame_idx in range(total_frames):
        t = frame_idx / float(total_frames)
        curr_sec = t * duration

        if curr_sec >= last_end + 1.0 and cached_static_bytes is not None:
            proc.stdin.write(cached_static_bytes)
            continue

        frame = base_img.copy()
        draw = ImageDraw.Draw(frame)

        # 游標閃爍週期
        cursor_visible = (int(t * fps * 2) % 2 == 0)
        curr_y = start_y
        active_subtitle = None

        for k, s_info in enumerate(step_intervals):
            t_start = s_info["t_start"]
            t_type_end = s_info["t_type_end"]
            t_end = s_info["t_end"]
            cmd_text = s_info["cmd"]
            logs = s_info["logs"]
            col = prompt_colors[k % len(prompt_colors)]

            if t < t_start:
                continue

            draw.text((content_x, curr_y), "ethan@ai-studio:~$ ", font=font_mono, fill=col)

            if t <= t_type_end:
                prog = (t - t_start) / max(0.001, (t_type_end - t_start))
                typed_len = int(prog * len(cmd_text))
                draw.text((content_x + 195, curr_y), cmd_text[:typed_len], font=font_mono, fill=(248, 250, 252))
                if cursor_visible:
                    c_pos_x = content_x + 195 + typed_len * 11
                    draw.rectangle([c_pos_x, curr_y + 2, c_pos_x + 10, curr_y + 22], fill=col)
                curr_y += line_h
                active_subtitle = f"步驟 {k+1}/{num_cmds}：正在輸入指令 {cmd_text[:38]}"
            else:
                draw.text((content_x + 195, curr_y), cmd_text, font=font_mono, fill=(248, 250, 252))
                curr_y += line_h

                log_prog = min(1.0, (t - t_type_end) / max(0.001, (t_end - t_type_end)))
                show_cnt = max(1, int(log_prog * len(logs)))
                for li in range(min(show_cnt, len(logs))):
                    ltxt = logs[li]
                    lcol = (52, 211, 153) if any(w in ltxt for w in ["成功", "✔", "OK", "就緒", "完成"]) else (148, 163, 184)
                    draw.text((content_x + 20, curr_y), ltxt, font=font_mono, fill=lcol)
                    curr_y += line_h - 4
                curr_y += 10

                if s_info["narration"]:
                    active_subtitle = f"步驟 {k+1}/{num_cmds}：{s_info['narration'][:50]}"
                else:
                    active_subtitle = f"步驟 {k+1}/{num_cmds}：指令執行中，已取得輸出日誌"

        # 整體成果展示 (在所有指令完成後顯示綠色成功標籤)
        if curr_sec >= last_end:
            draw.rounded_rectangle([content_x + 20, curr_y + 8, content_x + 420, curr_y + 48], radius=8, fill=(16, 185, 129, 45), outline=(16, 185, 129), width=2)
            draw.text((content_x + 35, curr_y + 16), "[OK] 示範教學腳本 100% 執行成功！", font=font_badge, fill=(52, 211, 153))
            active_subtitle = f"【{title}】教學實戰 100% 圓滿達成！"

        # 繪製快轉 HUD 標籤 (若有啟用倍速快轉)
        if speed > 1.0:
            draw_speed_hud_badge(draw, w, h, speed, frame_idx, fps)

        # 繪製底部動態解說字幕膠囊
        if show_subtitles and active_subtitle:
            draw_subtitle_banner(draw, w, h, active_subtitle, is_vertical)

        # 滑鼠移動軌跡插值
        seg_idx = min(len(mouse_waypoints) - 2, int(t * (len(mouse_waypoints) - 1)))
        seg_t = (t * (len(mouse_waypoints) - 1)) - seg_idx
        p0 = mouse_waypoints[seg_idx]
        p1 = mouse_waypoints[seg_idx + 1]
        mx = int(p0[0] + (p1[0] - p0[0]) * ease_in_out(seg_t))
        my = int(p0[1] + (p1[1] - p0[1]) * ease_in_out(seg_t))

        click_val = 0.3 if cursor_visible and t > 0.5 else 0.0
        draw_mouse_cursor(draw, mx, my, click_val)

        raw_bytes = frame.convert("RGB").tobytes()
        if curr_sec >= last_end + 1.0 and cached_static_bytes is None:
            cached_static_bytes = raw_bytes

        proc.stdin.write(raw_bytes)

    proc.stdin.close()
    proc.wait()

    # 導出 WebVTT 字幕檔案
    vtt_path = output_path.rsplit(".", 1)[0] + ".vtt"
    try:
        export_vtt_subtitles(vtt_path, vtt_cues)
    except Exception as e_vtt:
        print(f"⚠️ WebVTT 字幕導出異常: {e_vtt}")

    # 合成多軌音訊 (配音 + 機械鍵盤打字音效)
    if enable_audio:
        speech_text = narration_text
        if not speech_text or not speech_text.strip():
            auto_narr_parts = [f"哈囉大家好！今天帶大家實戰【{title}】。"]
            for si in step_intervals:
                if si["narration"]:
                    auto_narr_parts.append(si["narration"])
            auto_narr_parts.append("最後一鍵執行驗收成果，恭喜大家順利完成全部實戰操作！")
            speech_text = " ".join(auto_narr_parts)

        audio_temp = tempfile.mktemp(suffix=".m4a")
        try:
            build_complete_audio(audio_temp, duration, speech_text, typing_intervals)
            cmd_merge = [
                FFMPEG_EXE, "-y",
                "-i", temp_raw_video,
                "-i", audio_temp,
                "-c:v", "copy",
                "-c:a", "copy",
                "-map", "0:v:0",
                "-map", "1:a:0",
                output_path
            ]
            subprocess.run(cmd_merge, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(temp_raw_video): os.remove(temp_raw_video)
            if os.path.exists(audio_temp): os.remove(audio_temp)
            return output_path
        except Exception as e_audio:
            print(f"⚠️ 音訊合成合併異常 ({e_audio})，導出純影像")

    if os.path.exists(temp_raw_video):
        if os.path.exists(output_path):
            os.remove(output_path)
        shutil.move(temp_raw_video, output_path)

    return output_path

# -------------------------------------------------------------
# 模式二：網頁瀏覽器與大模型操作錄製 (Browser Auto-Pilot)
# -------------------------------------------------------------
def render_browser_recording(
    url: str = "https://chat.deepseek.com",
    prompt_text: str = "請幫我規劃一套完全不用人操作的 YouTube 影片自動生成工作流",
    duration: float = 10.0,
    output_path: str = None,
    narration_text: str = None,
    is_vertical: bool = False,
    speed: float = 1.0,
    show_subtitles: bool = True,
    enable_audio: bool = True
) -> str:
    """
    全自動模擬在瀏覽器中打開 AI 介面、滑鼠移動至輸入框、打字送出、串流生成回答。
    時長支援 5 秒 ~ 3600 秒 (60分鐘)，包含打字音效、自然語音配音、動態字幕膠囊與快轉倍速標籤。
    """
    w, h = (1080, 1920) if is_vertical else (1920, 1080)
    fps = 24 if duration <= 60 else (16 if duration <= 300 else (8 if duration <= 900 else 4))
    total_frames = int(duration * fps)

    if not output_path:
        ts = int(time.time())
        output_path = os.path.join(RECORDINGS_DIR, f"autopilot_browser_{ts}.mp4")

    temp_raw_video = tempfile.mktemp(suffix=".mp4")
    cmd_ffmpeg = [
        FFMPEG_EXE, "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{w}x{h}",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-r", "24",
        temp_raw_video
    ]
    proc = subprocess.Popen(cmd_ffmpeg, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    base_img = create_window_base(w, h, "DeepSeek AI · 自動化工作流助理", "browser")
    font_main = get_font(22 if not is_vertical else 18)
    font_sub = get_font(18 if not is_vertical else 15)
    font_badge = get_font(16)

    input_box_rect = [120, h - 220, w - 120, h - 110]
    send_btn_rect = [w - 240, h - 180, w - 140, h - 130]

    ai_responses = [
        "【AI 智慧分析】已就緒！為您建立以下無人自動化管線：",
        "1. 腳本生成層：深度拆解主題，精準匹配目標分鐘數與專業分鏡。",
        "2. 語音配音層：微軟神經自然語音合成 (支援台灣男聲與女聲)。",
        "3. 電腦操作層：全自動模擬滑鼠、鍵盤與命令列執行，零人力介入！",
        "4. 成品導出層：一鍵拼接 1080p 超高畫質 YouTube 完整長片！"
    ]

    # 人性化自然節奏 (秒數基準，長片前段展示完畢後常駐畫面)
    start_sec = min(1.2, duration * 0.05)
    type_dur = min(max(2.5, len(prompt_text) * 0.08 / max(1.0, speed)), min(15.0, duration * 0.35))
    type_end_sec = start_sec + type_dur
    send_sec = type_end_sec + min(1.2, max(0.5, duration * 0.05))
    stream_dur = min(max(4.0, duration * 0.30), min(25.0, duration * 0.50))
    stream_end_sec = min(duration * 0.95, send_sec + stream_dur)

    typing_intervals = [(start_sec, type_end_sec)]
    vtt_cues = [
        {
            "start": 0.0,
            "end": type_end_sec,
            "text": f"[步驟 1/3] 在 AI 瀏覽器輸入框輸入提問：「{prompt_text[:28]}」"
        },
        {
            "start": type_end_sec,
            "end": send_sec + 0.5,
            "text": "[步驟 2/3] 滑鼠移動並點擊送出按鈕"
        },
        {
            "start": send_sec + 0.5,
            "end": stream_end_sec,
            "text": "[步驟 3/3] DeepSeek AI 即時串流生成結構化自動化方案"
        },
        {
            "start": stream_end_sec,
            "end": duration,
            "text": "[完成] AI 自動化工作流規劃就緒，啟動全無人執行！"
        }
    ]

    p_init = (w * 0.7, h * 0.3)
    p_box = (input_box_rect[0] + 120, input_box_rect[1] + 45)
    p_send = (send_btn_rect[0] + 50, send_btn_rect[1] + 25)
    p_read = (w * 0.45, h * 0.45)
    p_rest = (w * 0.85, h * 0.35)

    cached_static_bytes = None

    for frame_idx in range(total_frames):
        t = frame_idx / float(total_frames)
        curr_sec = t * duration

        if curr_sec >= stream_end_sec + 1.0 and cached_static_bytes is not None:
            proc.stdin.write(cached_static_bytes)
            continue

        frame = base_img.copy()
        draw = ImageDraw.Draw(frame)
        active_subtitle = None

        # 頂部對話歷史
        conv_y = 125
        # 使用者氣泡 (送出後常駐)
        if curr_sec >= send_sec:
            draw.rounded_rectangle([w - 680, conv_y, w - 120, conv_y + 60], radius=12, fill=(37, 99, 235))
            draw.text((w - 660, conv_y + 16), prompt_text[:30] + ("..." if len(prompt_text) > 30 else ""), font=font_sub, fill=(255, 255, 255))
            conv_y += 85

        # AI 回應 (在 send_sec 之後逐步串流或常駐完整內容)
        if curr_sec >= send_sec:
            if curr_sec < stream_end_sec:
                ai_prog = min(1.0, max(0.0, (curr_sec - send_sec) / max(0.001, (stream_end_sec - send_sec))))
                show_lines = max(1, int(ai_prog * len(ai_responses)))
                active_subtitle = "步驟 3/3：DeepSeek AI 正在串流輸出智慧自動化流程..."
            else:
                show_lines = len(ai_responses)
                active_subtitle = "步驟 3/3：AI 自動化工作流規劃完成，可直接投入無人執行！"

            draw.rounded_rectangle([120, conv_y, w - 240, conv_y + 40 + show_lines * 34], radius=14, fill=(30, 41, 59), outline=(56, 189, 248), width=1)
            for idx in range(show_lines):
                line = ai_responses[idx]
                col = (56, 189, 248) if idx == 0 else (226, 232, 240)
                draw.text((150, conv_y + 18 + idx * 34), line, font=font_sub, fill=col)

            # 完成綠色標籤
            if curr_sec >= stream_end_sec:
                tag_y = conv_y + 50 + len(ai_responses) * 34
                draw.rounded_rectangle([120, tag_y, 440, tag_y + 36], radius=8, fill=(16, 185, 129, 45), outline=(16, 185, 129), width=2)
                draw.text((135, tag_y + 8), "[OK] AI 規劃流程已完整生成", font=font_badge, fill=(52, 211, 153))

        # 底部輸入框
        draw.rounded_rectangle(input_box_rect, radius=12, fill=(15, 23, 42), outline=(56, 189, 248) if curr_sec < send_sec else (51, 65, 85), width=2)

        # 打字效果
        if curr_sec < start_sec:
            draw.text((input_box_rect[0] + 20, input_box_rect[1] + 35), "輸入問題或指令...", font=font_main, fill=(100, 116, 139))
            active_subtitle = "步驟 1/3：準備向 AI 助手發送提示詞"
        elif curr_sec <= type_end_sec:
            type_ratio = (curr_sec - start_sec) / max(0.001, (type_end_sec - start_sec))
            chars_to_show = int(type_ratio * len(prompt_text))
            draw.text((input_box_rect[0] + 20, input_box_rect[1] + 35), prompt_text[:chars_to_show], font=font_main, fill=(255, 255, 255))
            if int(curr_sec * 3) % 2 == 0:
                cx = input_box_rect[0] + 20 + chars_to_show * 15
                draw.rectangle([cx, input_box_rect[1] + 32, cx + 8, input_box_rect[1] + 58], fill=(56, 189, 248))
            active_subtitle = f"步驟 1/3：正在輸入提示詞「{prompt_text[:chars_to_show]}」"
        elif curr_sec < send_sec:
            draw.text((input_box_rect[0] + 20, input_box_rect[1] + 35), prompt_text, font=font_main, fill=(255, 255, 255))
            active_subtitle = "步驟 2/3：確認提示詞完畢，準備點擊送出"
        else:
            draw.text((input_box_rect[0] + 20, input_box_rect[1] + 35), "AI 正在回覆中...", font=font_main, fill=(148, 163, 184))

        # 發送按鈕
        btn_col = (37, 99, 235) if curr_sec < send_sec else (30, 41, 59)
        draw.rounded_rectangle(send_btn_rect, radius=8, fill=btn_col)
        draw.text((send_btn_rect[0] + 24, send_btn_rect[1] + 14), "送出 >", font=font_sub, fill=(255, 255, 255))

        # 繪製快轉 HUD 標籤
        if speed > 1.0:
            draw_speed_hud_badge(draw, w, h, speed, frame_idx, fps)

        # 繪製底部動態解說字幕膠囊
        if show_subtitles and active_subtitle:
            draw_subtitle_banner(draw, w, h, active_subtitle, is_vertical)

        # 滑鼠軌跡插值 (秒數平滑轉移)
        if curr_sec < start_sec:
            p_a, p_b = p_init, p_box
            seg_ratio = curr_sec / max(0.001, start_sec)
        elif curr_sec < type_end_sec:
            p_a, p_b = p_box, p_box
            seg_ratio = 0.0
        elif curr_sec < send_sec:
            p_a, p_b = p_box, p_send
            seg_ratio = (curr_sec - type_end_sec) / max(0.001, (send_sec - type_end_sec))
        elif curr_sec < stream_end_sec:
            p_a, p_b = p_send, p_read
            seg_ratio = (curr_sec - send_sec) / max(0.001, (stream_end_sec - send_sec))
        else:
            p_a, p_b = p_read, p_rest
            seg_ratio = min(1.0, (curr_sec - stream_end_sec) / max(0.001, min(5.0, duration - stream_end_sec)))

        mx = int(p_a[0] + (p_b[0] - p_a[0]) * ease_in_out(min(1.0, max(0.0, seg_ratio))))
        my = int(p_a[1] + (p_b[1] - p_a[1]) * ease_in_out(min(1.0, max(0.0, seg_ratio))))

        click_val = 0.0
        if abs(curr_sec - start_sec) <= 0.25:
            click_val = 1.0 - abs(curr_sec - start_sec) / 0.25
        elif abs(curr_sec - send_sec) <= 0.25:
            click_val = 1.0 - abs(curr_sec - send_sec) / 0.25

        draw_mouse_cursor(draw, mx, my, click_val)

        raw_bytes = frame.convert("RGB").tobytes()
        if curr_sec >= stream_end_sec + 1.0 and cached_static_bytes is None:
            cached_static_bytes = raw_bytes

        proc.stdin.write(raw_bytes)

    proc.stdin.close()
    proc.wait()

    # 導出 WebVTT 字幕
    vtt_path = output_path.rsplit(".", 1)[0] + ".vtt"
    try:
        export_vtt_subtitles(vtt_path, vtt_cues)
    except Exception as e_vtt:
        print(f"⚠️ WebVTT 字幕導出異常: {e_vtt}")

    # 合成多軌音訊 (配音 + 機械鍵盤打字音效)
    if enable_audio:
        speech_text = narration_text
        if not speech_text or not speech_text.strip():
            speech_text = f"現在我們在瀏覽器打開 AI 助理介面，輸入提示詞：{prompt_text[:30]}。點擊送出後，AI 立即為我們規劃全套自動化生成架構！"

        audio_temp = tempfile.mktemp(suffix=".m4a")
        try:
            build_complete_audio(audio_temp, duration, speech_text, typing_intervals)
            cmd_merge = [
                FFMPEG_EXE, "-y",
                "-i", temp_raw_video,
                "-i", audio_temp,
                "-c:v", "copy",
                "-c:a", "copy",
                "-map", "0:v:0",
                "-map", "1:a:0",
                output_path
            ]
            subprocess.run(cmd_merge, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(temp_raw_video): os.remove(temp_raw_video)
            if os.path.exists(audio_temp): os.remove(audio_temp)
            return output_path
        except Exception as e_audio:
            print(f"⚠️ 網頁操作音訊合成異常 ({e_audio})，導出純影像")

    if os.path.exists(temp_raw_video):
        if os.path.exists(output_path):
            os.remove(output_path)
        shutil.move(temp_raw_video, output_path)

    return output_path

# -------------------------------------------------------------
# 模式三：代碼編輯器與自動執行 (Code Editor & Auto-Run)
# -------------------------------------------------------------
def render_editor_recording(
    filename: str = "create_video.py",
    code_lines: list = None,
    duration: float = 8.0,
    output_path: str = None,
    narration_text: str = None,
    is_vertical: bool = False,
    speed: float = 1.0,
    show_subtitles: bool = True,
    enable_audio: bool = True
) -> str:
    """
    全自動模擬 VS Code 寫代碼、語法高亮、點擊 Run 執行與終端機回饋。
    時長支援 5 秒 ~ 3600 秒 (60分鐘)，包含打字音效、自然語音配音、動態字幕膠囊與快轉倍速標籤。
    """
    w, h = (1080, 1920) if is_vertical else (1920, 1080)
    fps = 24 if duration <= 60 else (16 if duration <= 300 else (8 if duration <= 900 else 4))
    total_frames = int(duration * fps)

    if not code_lines:
        code_lines = [
            "from src.script_generator import generate_script_by_ai",
            "from src.composer import render_video_pipeline",
            "",
            "# 1. 自動由 AI 生成專業多幕結構化分鏡腳本",
            "script = generate_script_by_ai(topic='2026最新AI生片', duration_minutes=3.0)",
            "print(f'[AI Studio] 成功規劃 {len(script[\"scenes\"])} 幕分鏡')",
            "",
            "# 2. 一鍵啟動配音與渲染管線",
            "output_file = render_video_pipeline(script=script, voice='YunJhe', is_vertical=False)",
            "print(f'🎉 影片成功輸出：{output_file}')"
        ]

    if not output_path:
        ts = int(time.time())
        output_path = os.path.join(RECORDINGS_DIR, f"autopilot_editor_{ts}.mp4")

    temp_raw_video = tempfile.mktemp(suffix=".mp4")
    cmd_ffmpeg = [
        FFMPEG_EXE, "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{w}x{h}",
        "-pix_fmt", "rgb24",
        "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-r", "24",
        temp_raw_video
    ]
    proc = subprocess.Popen(cmd_ffmpeg, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    base_img = create_window_base(w, h, f"VS Code · {filename}", "editor")
    font_code = get_font(18)
    font_sub = get_font(15)

    # 計算代碼打字時間與字幕 (秒數基準)
    total_code_chars = sum(len(line) + 1 for line in code_lines)
    start_sec = min(1.0, duration * 0.05)
    type_dur = min(max(3.0, total_code_chars * 0.05 / max(1.0, speed)), min(15.0, duration * 0.40))
    type_end_sec = start_sec + type_dur
    run_sec = type_end_sec + min(1.2, max(0.5, duration * 0.05))
    exec_dur = min(max(4.0, duration * 0.30), min(20.0, duration * 0.40))
    exec_end_sec = min(duration * 0.95, run_sec + exec_dur)

    typing_intervals = [(start_sec, type_end_sec)]
    vtt_cues = [
        {
            "start": 0.0,
            "end": type_end_sec,
            "text": f"[步驟 1/3] 在 VS Code 撰寫 {filename} 核心程式邏輯"
        },
        {
            "start": type_end_sec,
            "end": run_sec + 0.5,
            "text": "[步驟 2/3] 點擊右上角 Run 按鈕編譯執行"
        },
        {
            "start": run_sec + 0.5,
            "end": exec_end_sec,
            "text": "[步驟 3/3] 內嵌終端機啟動並輸出產出結果"
        },
        {
            "start": exec_end_sec,
            "end": duration,
            "text": "[完成] 程式執行成功，已順利生成 YouTube 自動化影片！"
        }
    ]

    p_init = (w * 0.8, h * 0.8)
    p_code = (350, 220)
    p_run = (w - 200, 77)
    p_term = (w * 0.5, h * 0.75)
    p_rest = (w * 0.9, h * 0.2)

    cached_static_bytes = None

    for frame_idx in range(total_frames):
        t = frame_idx / float(total_frames)
        curr_sec = t * duration

        if curr_sec >= exec_end_sec + 1.0 and cached_static_bytes is not None:
            proc.stdin.write(cached_static_bytes)
            continue

        frame = base_img.copy()
        draw = ImageDraw.Draw(frame)
        active_subtitle = None

        # 側邊欄 (File Tree)
        draw.rectangle([60, 102, 240, h - 50], fill=(24, 30, 48))
        draw.line([240, 102, 240, h - 50], fill=(51, 65, 85), width=1)
        draw.text((80, 120), "EXPLORER", font=font_sub, fill=(148, 163, 184))
        draw.text((80, 155), "📄 main.py", font=font_sub, fill=(148, 163, 184))
        draw.text((80, 190), f"[PY] {filename}", font=font_sub, fill=(56, 189, 248))
        draw.text((80, 225), "📄 composer.py", font=font_sub, fill=(148, 163, 184))

        # 右上角 Run 按鈕
        run_btn_rect = [w - 240, 62, w - 160, 92]
        is_running_btn = (abs(curr_sec - run_sec) <= 0.4)
        draw.rounded_rectangle(run_btn_rect, radius=6, fill=(34, 197, 94) if is_running_btn else (30, 41, 59), outline=(34, 197, 94), width=1)
        draw.text((run_btn_rect[0] + 16, run_btn_rect[1] + 6), "▶ Run", font=font_sub, fill=(255, 255, 255))

        # 代碼逐步打字效果
        if curr_sec < start_sec:
            curr_chars = 0
            active_subtitle = f"步驟 1/3：準備在 VS Code 編輯器撰寫 {filename}"
        elif curr_sec <= type_end_sec:
            code_prog = (curr_sec - start_sec) / max(0.001, (type_end_sec - start_sec))
            curr_chars = int(code_prog * total_code_chars)
            active_subtitle = f"步驟 1/3：在 VS Code 編輯器中撰寫 {filename} 代碼"
        else:
            curr_chars = total_code_chars
            if curr_sec < run_sec:
                active_subtitle = "步驟 2/3：點擊右上角 ▶ Run 一鍵自動執行"
            elif curr_sec < exec_end_sec:
                active_subtitle = "步驟 3/3：終端機輸出日誌，程式執行中..."
            else:
                active_subtitle = "步驟 3/3：終端機輸出日誌，程式執行成功！"

        chars_left = curr_chars
        code_y = 120
        for idx, line in enumerate(code_lines):
            line_no = f"{idx + 1:2d}"
            draw.text((260, code_y), line_no, font=font_code, fill=(71, 85, 105))
            
            if chars_left >= len(line):
                txt_to_show = line
                chars_left -= (len(line) + 1)
            elif chars_left > 0:
                txt_to_show = line[:chars_left]
                chars_left = 0
            else:
                txt_to_show = ""

            if txt_to_show.startswith("import") or txt_to_show.startswith("from"):
                color = (192, 132, 252) # 關鍵字紫
            elif txt_to_show.startswith("#"):
                color = (100, 116, 139) # 註解灰
            elif "print" in txt_to_show:
                color = (56, 189, 248)  # 函式青
            else:
                color = (248, 250, 252)

            draw.text((300, code_y), txt_to_show, font=font_code, fill=color)
            code_y += 28

        # 下方執行終端機 (curr_sec >= run_sec 滑出並常駐)
        if curr_sec >= run_sec:
            term_top = h - 260
            draw.rectangle([241, term_top, w - 60, h - 50], fill=(15, 20, 32))
            draw.line([241, term_top, w - 60, term_top], fill=(56, 189, 248), width=2)
            draw.text((260, term_top + 10), f"TERMINAL · python3 {filename}", font=font_sub, fill=(148, 163, 184))
            
            exec_prog = min(1.0, (curr_sec - run_sec) / max(0.001, (exec_end_sec - run_sec)))
            draw.text((260, term_top + 45), ">>> [AI Studio] 成功規劃 8 幕分鏡", font=font_code, fill=(56, 189, 248))
            if exec_prog >= 0.40:
                draw.text((260, term_top + 75), ">>> [TTS] 微軟自然配音已合成完畢 (YunJhe)", font=font_code, fill=(253, 224, 71))
            if exec_prog >= 0.80:
                draw.text((260, term_top + 105), ">>> [完成] 影片成功輸出：output_videos/demo.mp4 (Process finished with exit code 0)", font=font_code, fill=(52, 211, 153))

        # 繪製快轉 HUD 標籤
        if speed > 1.0:
            draw_speed_hud_badge(draw, w, h, speed, frame_idx, fps)

        # 繪製底部動態解說字幕膠囊
        if show_subtitles and active_subtitle:
            draw_subtitle_banner(draw, w, h, active_subtitle, is_vertical)

        # 滑鼠軌跡插值
        if curr_sec < start_sec:
            p_a, p_b = p_init, p_code
            seg_ratio = curr_sec / max(0.001, start_sec)
        elif curr_sec < type_end_sec:
            p_a, p_b = p_code, p_code
            seg_ratio = 0.0
        elif curr_sec < run_sec:
            p_a, p_b = p_code, p_run
            seg_ratio = (curr_sec - type_end_sec) / max(0.001, (run_sec - type_end_sec))
        elif curr_sec < exec_end_sec:
            p_a, p_b = p_run, p_term
            seg_ratio = (curr_sec - run_sec) / max(0.001, (exec_end_sec - run_sec))
        else:
            p_a, p_b = p_term, p_rest
            seg_ratio = min(1.0, (curr_sec - exec_end_sec) / max(0.001, min(5.0, duration - exec_end_sec)))

        mx = int(p_a[0] + (p_b[0] - p_a[0]) * ease_in_out(min(1.0, max(0.0, seg_ratio))))
        my = int(p_a[1] + (p_b[1] - p_a[1]) * ease_in_out(min(1.0, max(0.0, seg_ratio))))

        click_val = 0.0
        if abs(curr_sec - run_sec) <= 0.25:
            click_val = 1.0 - abs(curr_sec - run_sec) / 0.25

        draw_mouse_cursor(draw, mx, my, click_val)

        raw_bytes = frame.convert("RGB").tobytes()
        if curr_sec >= exec_end_sec + 1.0 and cached_static_bytes is None:
            cached_static_bytes = raw_bytes

        proc.stdin.write(raw_bytes)

    proc.stdin.close()
    proc.wait()

    # 導出 WebVTT 字幕
    vtt_path = output_path.rsplit(".", 1)[0] + ".vtt"
    try:
        export_vtt_subtitles(vtt_path, vtt_cues)
    except Exception as e_vtt:
        print(f"⚠️ WebVTT 字幕導出異常: {e_vtt}")

    # 合成多軌音訊 (配音 + 機械鍵盤打字音效)
    if enable_audio:
        speech_text = narration_text
        if not speech_text or not speech_text.strip():
            speech_text = f"在 VS Code 開啟 {filename}，編寫全自動生成影片邏輯。撰寫完畢後點擊 Run 執行，下方終端機瞬間輸出成果！"

        audio_temp = tempfile.mktemp(suffix=".m4a")
        try:
            build_complete_audio(audio_temp, duration, speech_text, typing_intervals)
            cmd_merge = [
                FFMPEG_EXE, "-y",
                "-i", temp_raw_video,
                "-i", audio_temp,
                "-c:v", "copy",
                "-c:a", "copy",
                "-map", "0:v:0",
                "-map", "1:a:0",
                output_path
            ]
            subprocess.run(cmd_merge, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.exists(temp_raw_video): os.remove(temp_raw_video)
            if os.path.exists(audio_temp): os.remove(audio_temp)
            return output_path
        except Exception as e_audio:
            print(f"⚠️ 代碼編輯器音訊合成異常 ({e_audio})，導出純影像")

    if os.path.exists(temp_raw_video):
        if os.path.exists(output_path):
            os.remove(output_path)
        shutil.move(temp_raw_video, output_path)

    return output_path

# -------------------------------------------------------------
# 智能模式判斷演算法 (Smart Mode Auto-Detector)
# -------------------------------------------------------------
def detect_best_autopilot_mode(text: str) -> dict:
    """
    智能分析腳本內容，自動決策最適合的無人電腦操作模式 (terminal, browser, editor, desktop)
    """
    if not text:
        return {"mode": "terminal", "confidence": 85, "reasons": ["通用預設技術操作"]}
    
    lower = text.lower()
    scores = {"terminal": 0, "browser": 0, "editor": 0, "desktop": 0}
    reasons = {"terminal": [], "browser": [], "editor": [], "desktop": []}

    # 1. 終端機特徵
    term_kws = [
        ("git", 5, "Git 版本控制"), ("pip", 5, "Pip 套件管理"), ("npm", 5, "NPM 套件管理"),
        ("install", 4, "安裝套件"), ("安裝", 4, "安裝套件"), ("終端機", 6, "終端機環境"),
        ("指令", 5, "Shell 指令"), ("命令行", 5, "命令行"), ("terminal", 6, "Terminal"),
        ("bash", 5, "Bash"), ("docker", 5, "Docker"), ("curl", 4, "Curl 請求"),
        ("$ ", 6, "Shell Prompt 指令符號"), ("cd ", 4, "切換目錄"), ("環境", 3, "環境就緒"),
        ("setup", 4, "初始化設定")
    ]
    for kw, pts, lbl in term_kws:
        if kw in lower:
            scores["terminal"] += pts
            if lbl not in reasons["terminal"]: reasons["terminal"].append(lbl)

    # 2. 網頁與 AI 助手特徵
    browser_kws = [
        ("http", 5, "HTTP 網址"), ("chatgpt", 6, "ChatGPT"), ("claude", 6, "Claude"),
        ("deepseek", 6, "DeepSeek"), ("gemini", 5, "Gemini"), ("notebooklm", 6, "NotebookLM"),
        ("prompt", 5, "AI 提示詞"), ("提示詞", 5, "提示詞 Prompt"), ("網頁", 5, "網頁介面"),
        ("網站", 4, "網站平台"), ("瀏覽器", 6, "瀏覽器操作"), ("搜尋", 4, "搜尋操作"),
        ("提問", 4, "AI 對話提問"), ("對話", 3, "AI 對話"), ("問答", 3, "智慧問答"),
        ("線上", 3, "線上雲端")
    ]
    for kw, pts, lbl in browser_kws:
        if kw in lower:
            scores["browser"] += pts
            if lbl not in reasons["browser"]: reasons["browser"].append(lbl)

    # 3. 代碼編輯器特徵
    editor_kws = [
        ("def ", 6, "Python 函式 (def)"), ("import ", 5, "模組導入 (import)"),
        ("class ", 5, "物件類別 (class)"), ("python", 4, "Python 語言"),
        (".py", 5, "Python 程式檔案"), ("代碼", 5, "程式代碼"),
        ("寫代碼", 6, "撰寫代碼"), ("程式", 4, "寫程式"), ("函式", 4, "函式封裝"),
        ("vscode", 6, "VS Code 編輯器"), ("編輯器", 5, "代碼編輯器"),
        ("print(", 5, "Print 輸出語法"), ("return ", 4, "語法結構 (return)")
    ]
    for kw, pts, lbl in editor_kws:
        if kw in lower:
            scores["editor"] += pts
            if lbl not in reasons["editor"]: reasons["editor"].append(lbl)

    # 4. 實體螢幕桌面特徵
    desktop_kws = [
        ("桌面", 5, "電腦桌面"), ("螢幕", 5, "螢幕錄影"), ("檔案總管", 5, "檔案管理員"),
        ("資料夾", 4, "資料夾操作"), ("視窗", 4, "視窗切換"), ("軟體", 3, "桌面軟體")
    ]
    for kw, pts, lbl in desktop_kws:
        if kw in lower:
            scores["desktop"] += pts
            if lbl not in reasons["desktop"]: reasons["desktop"].append(lbl)

    best_mode = max(scores, key=scores.get)
    tot = sum(scores.values())
    confidence = min(99, max(70, int((scores[best_mode] / tot) * 100))) if tot > 0 else 85

    return {
        "mode": best_mode,
        "confidence": confidence,
        "reasons": reasons[best_mode]
    }

def run_autopilot_recording(
    mode: str = "auto",
    title: str = "AI 電腦無人操作自動錄影",
    duration: float = 8.0,
    commands: list = None,
    prompt: str = None,
    output_filename: str = None,
    narration: str = None,
    is_vertical: bool = False,
    speed: float = 1.0,
    show_subtitles: bool = True,
    enable_audio: bool = True
) -> str:
    """
    統一分派執行無人電腦操作並自動錄影，支援 'auto' 自動依文本判斷最佳模式。
    時長支援 5 秒 ~ 3600 秒 (60分鐘)，完整支援字幕膠囊、配音與打字音效、操作快轉倍速。
    優先使用 FFmpeg x11grab 背景螢幕錄製器 + 自動化操作引擎（真機操作）；
    若環境不支援實體畫面錄製，則自動切換至高畫質無人操作 Canvas 模擬渲染器。
    """
    from src.autopilot_detector import detect_mode_by_gemini
    from src.screen_recorder import ScreenRecorder
    import src.autopilot_engines as engines

    if mode == "auto" or not mode:
        analysis = detect_mode_by_gemini(f"{title} {prompt or ''} {' '.join(commands or [])} {narration or ''}")
        mode = analysis.get("mode", "terminal")
        print(f"🤖 [Auto-Detector] 自動識別為【{mode}】模式 (信心度: {analysis.get('confidence', 90)}%)")

    ts = int(time.time())
    if not output_filename:
        output_filename = f"autopilot_{mode}_{ts}.mp4"
    
    out_path = os.path.join(RECORDINGS_DIR, output_filename)
    os.makedirs(RECORDINGS_DIR, exist_ok=True)

    # 若使用者選擇「系統螢幕即時錄影 (desktop)」，嘗試擷取實體螢幕
    if mode == "desktop":
        real_rec_success = False
        try:
            recorder = ScreenRecorder(output_path=out_path, title_watermark=title, fps=30)
            if recorder.start():
                print(f"🎬 [ScreenRecorder] 背景實體螢幕錄影中 (時長: {duration}秒)...")
                engines.execute_pure_record_mode(duration=duration)
                stopped = recorder.stop()
                if stopped and os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
                    return out_path
        except Exception as e:
            print(f"⚠️ [ScreenRecorder] 實體錄製異常: {e}，自動切換至高畫質視窗模擬")

    # 方案 B：高質感無人 Canvas 渲染器 (保證 100% 產出 1080p 超高清無人操作影片)
    print(f"🎨 啟動高畫質無人操作 Canvas 模擬渲染器 (時長: {duration}s, 模式: {mode}, 快轉倍速: {speed}x)...")
    if mode == "terminal":
        return render_terminal_recording(
            title=title,
            commands=commands,
            duration=duration,
            output_path=out_path,
            narration_text=narration,
            is_vertical=is_vertical,
            speed=speed,
            show_subtitles=show_subtitles,
            enable_audio=enable_audio
        )
    elif mode == "browser":
        return render_browser_recording(
            url="https://chat.deepseek.com",
            prompt_text=prompt or "請幫我規劃一套完全不用人操作的 YouTube 影片自動生成工作流",
            duration=duration,
            output_path=out_path,
            narration_text=narration,
            is_vertical=is_vertical,
            speed=speed,
            show_subtitles=show_subtitles,
            enable_audio=enable_audio
        )
    elif mode == "editor":
        return render_editor_recording(
            filename="create_video.py",
            code_lines=commands,
            duration=duration,
            output_path=out_path,
            narration_text=narration,
            is_vertical=is_vertical,
            speed=speed,
            show_subtitles=show_subtitles,
            enable_audio=enable_audio
        )
    else:
        return render_terminal_recording(
            title=title,
            commands=commands,
            duration=duration,
            output_path=out_path,
            narration_text=narration,
            is_vertical=is_vertical,
            speed=speed,
            show_subtitles=show_subtitles,
            enable_audio=enable_audio
        )

if __name__ == "__main__":
    print("🎬 開始測試無人電腦操作錄製引擎...")
    res = run_autopilot_recording(mode="terminal", duration=5.0)
    print(f"[✔] 終端機操作錄製成功：{res}")
    res2 = run_autopilot_recording(mode="browser", duration=5.0)
    print(f"[✔] 網頁操作錄製成功：{res2}")
