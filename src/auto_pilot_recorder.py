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
    icon_prefix = "💻 " if app_type == "terminal" else ("🌐 " if app_type == "browser" else "📝 ")
    draw.text((pad_x + 110, pad_y + 14), f"{icon_prefix}{title}", font=font_title, fill=(226, 232, 240))

    if app_type == "terminal":
        # 標註終端機目前目錄與 Git 狀態
        draw.text((pad_x + win_w - 280, pad_y + 16), "zsh · ~/ai-workspace · (main)", font=get_font(14), fill=(148, 163, 184))
    elif app_type == "browser":
        # 網址列背景
        url_box_w = min(600, win_w - 400)
        url_x = pad_x + 250
        draw.rounded_rectangle([url_x, pad_y + 10, url_x + url_box_w, pad_y + 40], radius=8, fill=(15, 23, 42), outline=(71, 85, 105), width=1)
        draw.text((url_x + 14, pad_y + 16), "🔒 https://ai-studio.local/workspace", font=get_font(14), fill=(56, 189, 248))

    return base

# -------------------------------------------------------------
# 模式一：終端機命令列全自動操作錄製 (Terminal Auto-Pilot)
# -------------------------------------------------------------
def render_terminal_recording(
    title: str = "AI 影片自動化管線一鍵啟動",
    commands: list = None,
    duration: float = 8.0,
    output_path: str = None,
    narration_text: str = None,
    is_vertical: bool = False
) -> str:
    """
    全自動模擬工程師/創作者在終端機輸入指令、跑程式、即時日誌捲動與游標操作
    """
    w, h = (1080, 1920) if is_vertical else (1920, 1080)
    fps = 24
    total_frames = int(duration * fps)

    if not commands:
        commands = [
            {
                "cmd": "git clone https://github.com/ethan628/ai-youtube-studio.git",
                "logs": [
                    "Cloning into 'ai-youtube-studio'...",
                    "remote: Enumerating objects: 120, done.",
                    "remote: Compressing objects: 100% (88/88), done.",
                    "Receiving objects: 100% (120/120), 4.20 MiB | 12.5 MiB/s, done."
                ]
            },
            {
                "cmd": "python create_video.py --topic '2026最強AI實戰' --duration 3",
                "logs": [
                    "[1/4] 🚀 載入智能腳本引擎 (多幕深度架構)... [OK]",
                    "[2/4] 🎙️ Edge-TTS 台灣微軟自然語音合成中... [OK]",
                    "[3/4] 🎨 生成 1080p Cyberpunk 視覺分鏡卡片... [OK]",
                    "[4/4] 🎬 全自動渲染導出 MP4 影片完成！",
                    ">>> 輸出路徑：output_videos/ai_studio_final.mp4 (100% 完成)"
                ]
            }
        ]

    if not output_path:
        ts = int(time.time())
        output_path = os.path.join(RECORDINGS_DIR, f"autopilot_terminal_{ts}.mp4")

    # 準備字型
    font_mono = get_font(20 if not is_vertical else 18)
    font_badge = get_font(16)
    
    # 預先計算打字進度與游標動畫
    # 第一段指令在 0.1~0.4 期間打字，第二段在 0.5~0.8 期間打字
    cmd1_text = commands[0]["cmd"]
    cmd2_text = commands[1]["cmd"] if len(commands) > 1 else ""

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
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        temp_raw_video
    ]
    proc = subprocess.Popen(cmd_ffmpeg, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    base_img = create_window_base(w, h, title, "terminal")
    content_x = 100
    start_y = 130
    line_h = 32

    # 模擬滑鼠移動關鍵幀 (x, y)
    mouse_waypoints = [
        (w * 0.85, h * 0.85),     # 初始在右下
        (content_x + 280, start_y + 15), # 移到第一個指令
        (content_x + 350, start_y + 180), # 移到第二個指令
        (content_x + 450, start_y + 360), # 點擊高亮輸出成果
        (w * 0.9, h * 0.2)       # 移開
    ]

    for frame_idx in range(total_frames):
        t = frame_idx / float(total_frames)
        frame = base_img.copy()
        draw = ImageDraw.Draw(frame)

        # 游標閃爍週期 (每秒閃爍 2 次)
        cursor_visible = (int(t * fps * 2) % 2 == 0)

        curr_y = start_y

        # === 第一條指令 ===
        t_cmd1_start, t_cmd1_end = 0.05, 0.35
        if t < t_cmd1_start:
            typed_len1 = 0
        elif t <= t_cmd1_end:
            progress1 = (t - t_cmd1_start) / (t_cmd1_end - t_cmd1_start)
            typed_len1 = int(progress1 * len(cmd1_text))
        else:
            typed_len1 = len(cmd1_text)

        draw.text((content_x, curr_y), "ethan@ai-studio:~$ ", font=font_mono, fill=(56, 189, 248))
        draw.text((content_x + 195, curr_y), cmd1_text[:typed_len1], font=font_mono, fill=(248, 250, 252))
        
        if t <= t_cmd1_end:
            if cursor_visible:
                c_pos_x = content_x + 195 + typed_len1 * 11
                draw.rectangle([c_pos_x, curr_y + 2, c_pos_x + 10, curr_y + 22], fill=(56, 189, 248))
        curr_y += line_h

        # 第一條指令的日誌輸出
        if t > t_cmd1_end:
            logs1 = commands[0].get("logs", [])
            log_progress = min(1.0, (t - t_cmd1_end) / 0.12)
            show_logs1_count = int(log_progress * len(logs1))
            for i in range(show_logs1_count):
                draw.text((content_x + 20, curr_y), logs1[i], font=font_mono, fill=(148, 163, 184))
                curr_y += line_h - 4
            curr_y += 10

        # === 第二條指令 ===
        t_cmd2_start, t_cmd2_end = 0.50, 0.75
        if cmd2_text and t >= t_cmd2_start:
            if t <= t_cmd2_end:
                progress2 = (t - t_cmd2_start) / (t_cmd2_end - t_cmd2_start)
                typed_len2 = int(progress2 * len(cmd2_text))
            else:
                typed_len2 = len(cmd2_text)

            draw.text((content_x, curr_y), "ethan@ai-studio:~$ ", font=font_mono, fill=(168, 85, 247))
            draw.text((content_x + 195, curr_y), cmd2_text[:typed_len2], font=font_mono, fill=(253, 224, 71))

            if t <= t_cmd2_end:
                if cursor_visible:
                    c_pos_x = content_x + 195 + typed_len2 * 11
                    draw.rectangle([c_pos_x, curr_y + 2, c_pos_x + 10, curr_y + 22], fill=(253, 224, 71))
            curr_y += line_h

            if t > t_cmd2_end:
                logs2 = commands[1].get("logs", [])
                log2_progress = min(1.0, (t - t_cmd2_end) / 0.15)
                show_logs2_count = int(log2_progress * len(logs2))
                for i in range(show_logs2_count):
                    line_txt = logs2[i]
                    col = (52, 211, 153) if "完成" in line_txt or "OK" in line_txt else (203, 213, 225)
                    draw.text((content_x + 20, curr_y), line_txt, font=font_mono, fill=col)
                    curr_y += line_h - 2

                # 成功高亮標籤
                if log2_progress >= 0.9:
                    draw.rounded_rectangle([content_x + 20, curr_y + 8, content_x + 360, curr_y + 44], radius=6, fill=(16, 185, 129, 40), outline=(16, 185, 129), width=2)
                    draw.text((content_x + 35, curr_y + 14), "✔ 全自動生片管線 100% 執行成功！", font=font_badge, fill=(52, 211, 153))

        # === 滑鼠移動軌跡插值 ===
        seg_idx = min(len(mouse_waypoints) - 2, int(t * (len(mouse_waypoints) - 1)))
        seg_t = (t * (len(mouse_waypoints) - 1)) - seg_idx
        p0 = mouse_waypoints[seg_idx]
        p1 = mouse_waypoints[seg_idx + 1]
        mx = int(p0[0] + (p1[0] - p0[0]) * ease_in_out(seg_t))
        my = int(p0[1] + (p1[1] - p0[1]) * ease_in_out(seg_t))

        # 模擬點擊波紋 (在 t=0.36 與 t=0.76 指令輸入完畢點擊)
        click_val = 0.0
        if 0.35 <= t <= 0.40:
            click_val = (t - 0.35) / 0.05
        elif 0.75 <= t <= 0.80:
            click_val = (t - 0.75) / 0.05

        draw_mouse_cursor(draw, mx, my, click_val)

        # 寫入 rawvideo
        proc.stdin.write(frame.convert("RGB").tobytes())

    proc.stdin.close()
    proc.wait()

    # 若有旁白語音需求，合併聲音
    final_output = output_path
    if narration_text:
        audio_temp = tempfile.mktemp(suffix=".mp3")
        try:
            generate_speech(narration_text, audio_temp)
            cmd_merge = [
                FFMPEG_EXE, "-y",
                "-i", temp_raw_video,
                "-i", audio_temp,
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                output_path
            ]
            subprocess.run(cmd_merge, check=True)
            if os.path.exists(temp_raw_video):
                os.remove(temp_raw_video)
            if os.path.exists(audio_temp):
                os.remove(audio_temp)
            return output_path
        except Exception as e:
            print(f"⚠️ 旁白合成失敗 ({e})，直接導出無人操作純影像。")

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
    is_vertical: bool = False
) -> str:
    """
    全自動模擬在瀏覽器中打開 AI 介面、滑鼠移動至輸入框、打字送出、串流生成回答
    """
    w, h = (1080, 1920) if is_vertical else (1920, 1080)
    fps = 24
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
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        temp_raw_video
    ]
    proc = subprocess.Popen(cmd_ffmpeg, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    base_img = create_window_base(w, h, "DeepSeek AI · 自動化工作流助理", "browser")
    font_main = get_font(22 if not is_vertical else 18)
    font_sub = get_font(18 if not is_vertical else 15)

    input_box_rect = [120, h - 220, w - 120, h - 110]
    send_btn_rect = [w - 240, h - 180, w - 140, h - 130]

    ai_responses = [
        "🤖 AI 智慧分析已就緒！為您建立以下無人自動化管線：",
        "1. 腳本生成層：深度拆解主題，精準匹配目標分鐘數與專業分鏡。",
        "2. 語音配音層：微軟神經自然語音合成 (支援台灣男聲與女聲)。",
        "3. 電腦操作層：全自動模擬滑鼠、鍵盤與命令列執行，零人力介入！",
        "4. 成品導出層：一鍵拼接 1080p 超高畫質 YouTube 完整長片與 Shorts！"
    ]

    mouse_waypoints = [
        (w * 0.7, h * 0.3),
        (input_box_rect[0] + 120, input_box_rect[1] + 45), # 移到輸入框
        (send_btn_rect[0] + 50, send_btn_rect[1] + 25),    # 移到發送按鈕
        (w * 0.45, h * 0.45),                              # 移到回答區域閱讀
        (w * 0.85, h * 0.35)                               # 移開
    ]

    for frame_idx in range(total_frames):
        t = frame_idx / float(total_frames)
        frame = base_img.copy()
        draw = ImageDraw.Draw(frame)

        # 頂部對話歷史
        conv_y = 125
        # 使用者氣泡 (發送後顯示)
        if t > 0.45:
            draw.rounded_rectangle([w - 680, conv_y, w - 120, conv_y + 60], radius=12, fill=(37, 99, 235))
            draw.text((w - 660, conv_y + 16), prompt_text[:30] + ("..." if len(prompt_text) > 30 else ""), font=font_sub, fill=(255, 255, 255))
            conv_y += 85

        # AI 回應 (在 t > 0.50 逐步串流生成)
        if t > 0.50:
            ai_progress = min(1.0, (t - 0.50) / 0.40)
            show_lines = max(1, int(ai_progress * len(ai_responses)))
            
            draw.rounded_rectangle([120, conv_y, w - 240, conv_y + 40 + show_lines * 34], radius=14, fill=(30, 41, 59), outline=(56, 189, 248), width=1)
            for idx in range(show_lines):
                line = ai_responses[idx]
                col = (56, 189, 248) if idx == 0 else (226, 232, 240)
                draw.text((150, conv_y + 18 + idx * 34), line, font=font_sub, fill=col)

        # 底部輸入框
        draw.rounded_rectangle(input_box_rect, radius=12, fill=(15, 23, 42), outline=(56, 189, 248) if t < 0.45 else (51, 65, 85), width=2)
        
        # 打字效果 (在 0.10 ~ 0.40 期間打字)
        if t < 0.10:
            draw.text((input_box_rect[0] + 20, input_box_rect[1] + 35), "輸入問題或指令...", font=font_main, fill=(100, 116, 139))
        elif t <= 0.42:
            type_ratio = (t - 0.10) / 0.32
            chars_to_show = int(type_ratio * len(prompt_text))
            draw.text((input_box_rect[0] + 20, input_box_rect[1] + 35), prompt_text[:chars_to_show], font=font_main, fill=(255, 255, 255))
            if int(t * fps * 2) % 2 == 0:
                cx = input_box_rect[0] + 20 + chars_to_show * 15
                draw.rectangle([cx, input_box_rect[1] + 32, cx + 8, input_box_rect[1] + 58], fill=(56, 189, 248))
        else:
            draw.text((input_box_rect[0] + 20, input_box_rect[1] + 35), "AI 正在回覆中...", font=font_main, fill=(148, 163, 184))

        # 發送按鈕
        btn_col = (37, 99, 235) if t < 0.42 else (30, 41, 59)
        draw.rounded_rectangle(send_btn_rect, radius=8, fill=btn_col)
        draw.text((send_btn_rect[0] + 20, send_btn_rect[1] + 14), "送出 🚀", font=font_sub, fill=(255, 255, 255))

        # 滑鼠軌跡插值
        seg_idx = min(len(mouse_waypoints) - 2, int(t * (len(mouse_waypoints) - 1)))
        seg_t = (t * (len(mouse_waypoints) - 1)) - seg_idx
        p0 = mouse_waypoints[seg_idx]
        p1 = mouse_waypoints[seg_idx + 1]
        mx = int(p0[0] + (p1[0] - p0[0]) * ease_in_out(seg_t))
        my = int(p0[1] + (p1[1] - p0[1]) * ease_in_out(seg_t))

        click_val = 0.0
        if 0.08 <= t <= 0.12:
            click_val = (t - 0.08) / 0.04
        elif 0.41 <= t <= 0.45:
            click_val = (t - 0.41) / 0.04

        draw_mouse_cursor(draw, mx, my, click_val)
        proc.stdin.write(frame.convert("RGB").tobytes())

    proc.stdin.close()
    proc.wait()

    if narration_text:
        audio_temp = tempfile.mktemp(suffix=".mp3")
        try:
            generate_speech(narration_text, audio_temp)
            cmd_merge = [
                FFMPEG_EXE, "-y",
                "-i", temp_raw_video,
                "-i", audio_temp,
                "-c:v", "copy",
                "-c:a", "aac",
                "-shortest",
                output_path
            ]
            subprocess.run(cmd_merge, check=True)
            if os.path.exists(temp_raw_video):
                os.remove(temp_raw_video)
            if os.path.exists(audio_temp):
                os.remove(audio_temp)
            return output_path
        except Exception:
            pass

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
    is_vertical: bool = False
) -> str:
    """
    全自動模擬 VS Code 寫代碼、語法高亮、點擊 Run 執行與終端機回饋
    """
    w, h = (1080, 1920) if is_vertical else (1920, 1080)
    fps = 24
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
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        temp_raw_video
    ]
    proc = subprocess.Popen(cmd_ffmpeg, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    base_img = create_window_base(w, h, f"VS Code · {filename}", "editor")
    font_code = get_font(18)
    font_sub = get_font(15)

    mouse_waypoints = [
        (w * 0.8, h * 0.8),
        (350, 220),           # 移到代碼區
        (w - 220, 75),        # 移到右上角 Run 按鈕 ▶
        (w * 0.5, h * 0.75),  # 移到下方終端機輸出區
        (w * 0.9, h * 0.2)
    ]

    for frame_idx in range(total_frames):
        t = frame_idx / float(total_frames)
        frame = base_img.copy()
        draw = ImageDraw.Draw(frame)

        # 側邊欄 (File Tree)
        draw.rectangle([60, 102, 240, h - 50], fill=(24, 30, 48))
        draw.line([240, 102, 240, h - 50], fill=(51, 65, 85), width=1)
        draw.text((80, 120), "EXPLORER", font=font_sub, fill=(148, 163, 184))
        draw.text((80, 155), "📄 main.py", font=font_sub, fill=(148, 163, 184))
        draw.text((80, 190), f"🐍 {filename}", font=font_sub, fill=(56, 189, 248))
        draw.text((80, 225), "📄 composer.py", font=font_sub, fill=(148, 163, 184))

        # 右上角 Run 按鈕
        run_btn_rect = [w - 240, 62, w - 160, 92]
        draw.rounded_rectangle(run_btn_rect, radius=6, fill=(34, 197, 94) if 0.45 <= t <= 0.60 else (30, 41, 59), outline=(34, 197, 94), width=1)
        draw.text((run_btn_rect[0] + 16, run_btn_rect[1] + 6), "▶ Run", font=font_sub, fill=(255, 255, 255))

        # 代碼逐步打字效果 (0.05 ~ 0.50)
        code_progress = min(1.0, max(0.0, (t - 0.05) / 0.45))
        total_code_chars = sum(len(line) + 1 for line in code_lines)
        curr_chars = int(code_progress * total_code_chars)

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

        # 下方執行終端機 (t > 0.55 滑出)
        if t > 0.55:
            term_top = h - 260
            draw.rectangle([241, term_top, w - 60, h - 50], fill=(15, 20, 32))
            draw.line([241, term_top, w - 60, term_top], fill=(56, 189, 248), width=2)
            draw.text((260, term_top + 10), "TERMINAL · python3 create_video.py", font=font_sub, fill=(148, 163, 184))
            
            draw.text((260, term_top + 45), ">>> [AI Studio] 成功規劃 8 幕分鏡", font=font_code, fill=(56, 189, 248))
            if t > 0.70:
                draw.text((260, term_top + 75), ">>> [TTS] 微軟自然配音已合成完畢 (YunJhe)", font=font_code, fill=(253, 224, 71))
            if t > 0.82:
                draw.text((260, term_top + 105), ">>> 🎉 影片成功輸出：output_videos/demo.mp4 (Process finished with exit code 0)", font=font_code, fill=(52, 211, 153))

        # 滑鼠軌跡與點擊
        seg_idx = min(len(mouse_waypoints) - 2, int(t * (len(mouse_waypoints) - 1)))
        seg_t = (t * (len(mouse_waypoints) - 1)) - seg_idx
        p0 = mouse_waypoints[seg_idx]
        p1 = mouse_waypoints[seg_idx + 1]
        mx = int(p0[0] + (p1[0] - p0[0]) * ease_in_out(seg_t))
        my = int(p0[1] + (p1[1] - p0[1]) * ease_in_out(seg_t))

        click_val = 0.0
        if 0.50 <= t <= 0.55:
            click_val = (t - 0.50) / 0.05

        draw_mouse_cursor(draw, mx, my, click_val)
        proc.stdin.write(frame.convert("RGB").tobytes())

    proc.stdin.close()
    proc.wait()

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
    is_vertical: bool = False
) -> str:
    """
    統一分派執行無人電腦操作並自動錄影，支援 'auto' 自動依文本判斷最佳模式
    """
    if mode == "auto" or not mode:
        analysis = detect_best_autopilot_mode(f"{title} {prompt or ''} {' '.join(commands or [])} {narration or ''}")
        mode = analysis["mode"]
        print(f"🤖 [Auto-Detector] 自動識別為【{mode}】模式 (信心度: {analysis['confidence']}%)")

    ts = int(time.time())
    if not output_filename:
        output_filename = f"autopilot_{mode}_{ts}.mp4"
    
    out_path = os.path.join(RECORDINGS_DIR, output_filename)

    if mode == "terminal":
        return render_terminal_recording(
            title=title,
            commands=commands,
            duration=duration,
            output_path=out_path,
            narration_text=narration,
            is_vertical=is_vertical
        )
    elif mode == "browser":
        return render_browser_recording(
            url="https://chat.deepseek.com",
            prompt_text=prompt or "請幫我規劃一套完全不用人操作的 YouTube 影片自動生成工作流",
            duration=duration,
            output_path=out_path,
            narration_text=narration,
            is_vertical=is_vertical
        )
    elif mode == "editor":
        return render_editor_recording(
            filename="create_video.py",
            code_lines=commands,
            duration=duration,
            output_path=out_path,
            is_vertical=is_vertical
        )
    else:
        # 預設回到 terminal
        return render_terminal_recording(
            title=title,
            commands=commands,
            duration=duration,
            output_path=out_path,
            narration_text=narration,
            is_vertical=is_vertical
        )

if __name__ == "__main__":
    print("🎬 開始測試無人電腦操作錄製引擎...")
    res = run_autopilot_recording(mode="terminal", duration=5.0)
    print(f"[✔] 終端機操作錄製成功：{res}")
    res2 = run_autopilot_recording(mode="browser", duration=5.0)
    print(f"[✔] 網頁操作錄製成功：{res2}")
