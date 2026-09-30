import os
import sys
import math
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.visuals import get_font, clean_emoji, draw_tech_background, draw_vector_check
from src.subtitle_utils import optimize_srt_file, get_ffmpeg_subtitles_style

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

def is_rubiks_cube_topic(topic: str) -> bool:
    """判斷主題是否與魔術方塊相關"""
    if not topic:
        return False
    t = topic.lower()
    keywords = ["魔術方塊", "魔方", "扭計骰", "rubik", "rubik's", "rubiks", "3x3"]
    return any(k in t for k in keywords)

# 標準魔術方塊 6 面配色
COLOR_WHITE  = (255, 255, 255) # U: 頂面白
COLOR_YELLOW = (250, 204, 21)  # D: 底面黃
COLOR_GREEN  = (34, 197, 94)   # F: 前面綠
COLOR_BLUE   = (59, 130, 246)  # B: 後面藍
COLOR_RED    = (239, 68, 68)   # R: 右面紅
COLOR_ORANGE = (249, 115, 22)  # L: 左面橘

# 預設還原階段顏色狀態生成器
def get_stage_cube_colors(stage_idx: int) -> dict:
    """
    根據階段回傳 54 個貼紙的顏色配置：
    stage 0: 打亂狀態 (Scrambled)
    stage 1: 底層白色十字 (White Cross)
    stage 2: 底層第一層完成 (First Layer)
    stage 3: 中層第二層完成 (Second Layer / F2L)
    stage 4: 頂面黃色十字 (Yellow Cross)
    stage 5: 頂面全黃 (OLL)
    stage 6+: 六面完全復原 (PLL Fully Solved)
    """
    if stage_idx >= 6:
        # 六面完全復原
        return {
            'U': [COLOR_WHITE] * 9,
            'D': [COLOR_YELLOW] * 9,
            'F': [COLOR_GREEN] * 9,
            'B': [COLOR_BLUE] * 9,
            'R': [COLOR_RED] * 9,
            'L': [COLOR_ORANGE] * 9
        }
    elif stage_idx == 5:
        # OLL 完成：頂面全黃，中層底層完整，頂層邊角微調
        return {
            'U': [COLOR_YELLOW] * 9,
            'D': [COLOR_WHITE] * 9,
            'F': [COLOR_GREEN, COLOR_GREEN, COLOR_GREEN, COLOR_GREEN, COLOR_GREEN, COLOR_GREEN, COLOR_RED, COLOR_BLUE, COLOR_GREEN],
            'B': [COLOR_BLUE, COLOR_BLUE, COLOR_BLUE, COLOR_BLUE, COLOR_BLUE, COLOR_BLUE, COLOR_ORANGE, COLOR_RED, COLOR_BLUE],
            'R': [COLOR_RED, COLOR_RED, COLOR_RED, COLOR_RED, COLOR_RED, COLOR_RED, COLOR_BLUE, COLOR_GREEN, COLOR_RED],
            'L': [COLOR_ORANGE, COLOR_ORANGE, COLOR_ORANGE, COLOR_ORANGE, COLOR_ORANGE, COLOR_ORANGE, COLOR_GREEN, COLOR_ORANGE, COLOR_ORANGE]
        }
    elif stage_idx == 4:
        # 頂層黃色十字
        u_face = [
            COLOR_GREEN, COLOR_YELLOW, COLOR_RED,
            COLOR_YELLOW, COLOR_YELLOW, COLOR_YELLOW,
            COLOR_BLUE, COLOR_YELLOW, COLOR_ORANGE
        ]
        return {
            'U': u_face,
            'D': [COLOR_WHITE] * 9,
            'F': [COLOR_GREEN]*6 + [COLOR_RED, COLOR_GREEN, COLOR_BLUE],
            'B': [COLOR_BLUE]*6 + [COLOR_ORANGE, COLOR_BLUE, COLOR_RED],
            'R': [COLOR_RED]*6 + [COLOR_BLUE, COLOR_RED, COLOR_GREEN],
            'L': [COLOR_ORANGE]*6 + [COLOR_GREEN, COLOR_ORANGE, COLOR_ORANGE]
        }
    elif stage_idx == 3:
        # 前兩層 F2L 完全復原，頂層混亂
        return {
            'U': [COLOR_YELLOW, COLOR_GREEN, COLOR_YELLOW, COLOR_RED, COLOR_YELLOW, COLOR_ORANGE, COLOR_YELLOW, COLOR_BLUE, COLOR_YELLOW],
            'D': [COLOR_WHITE] * 9,
            'F': [COLOR_GREEN]*6 + [COLOR_ORANGE, COLOR_YELLOW, COLOR_RED],
            'B': [COLOR_BLUE]*6 + [COLOR_RED, COLOR_YELLOW, COLOR_GREEN],
            'R': [COLOR_RED]*6 + [COLOR_GREEN, COLOR_YELLOW, COLOR_BLUE],
            'L': [COLOR_ORANGE]*6 + [COLOR_BLUE, COLOR_YELLOW, COLOR_ORANGE]
        }
    elif stage_idx == 2:
        # 底層第一層完整復原 (底面全白，側面底排同色)
        return {
            'U': [COLOR_BLUE, COLOR_YELLOW, COLOR_RED, COLOR_ORANGE, COLOR_YELLOW, COLOR_GREEN, COLOR_RED, COLOR_YELLOW, COLOR_BLUE],
            'D': [COLOR_WHITE] * 9,
            'F': [COLOR_GREEN]*3 + [COLOR_YELLOW, COLOR_GREEN, COLOR_RED, COLOR_ORANGE, COLOR_BLUE, COLOR_YELLOW],
            'B': [COLOR_BLUE]*3 + [COLOR_RED, COLOR_BLUE, COLOR_ORANGE, COLOR_YELLOW, COLOR_GREEN, COLOR_RED],
            'R': [COLOR_RED]*3 + [COLOR_GREEN, COLOR_RED, COLOR_BLUE, COLOR_YELLOW, COLOR_ORANGE, COLOR_GREEN],
            'L': [COLOR_ORANGE]*3 + [COLOR_BLUE, COLOR_ORANGE, COLOR_GREEN, COLOR_RED, COLOR_YELLOW, COLOR_BLUE]
        }
    elif stage_idx == 1:
        # 底層白色十字 (底面中央十字為白，角塊未歸位)
        return {
            'U': [COLOR_BLUE, COLOR_YELLOW, COLOR_GREEN, COLOR_RED, COLOR_YELLOW, COLOR_ORANGE, COLOR_YELLOW, COLOR_BLUE, COLOR_RED],
            'D': [COLOR_GREEN, COLOR_WHITE, COLOR_RED, COLOR_WHITE, COLOR_WHITE, COLOR_WHITE, COLOR_BLUE, COLOR_WHITE, COLOR_ORANGE],
            'F': [COLOR_YELLOW, COLOR_GREEN, COLOR_YELLOW, COLOR_ORANGE, COLOR_GREEN, COLOR_RED, COLOR_BLUE, COLOR_YELLOW, COLOR_GREEN],
            'B': [COLOR_RED, COLOR_BLUE, COLOR_ORANGE, COLOR_GREEN, COLOR_BLUE, COLOR_YELLOW, COLOR_RED, COLOR_ORANGE, COLOR_YELLOW],
            'R': [COLOR_BLUE, COLOR_RED, COLOR_GREEN, COLOR_YELLOW, COLOR_RED, COLOR_BLUE, COLOR_ORANGE, COLOR_GREEN, COLOR_RED],
            'L': [COLOR_ORANGE, COLOR_ORANGE, COLOR_YELLOW, COLOR_BLUE, COLOR_ORANGE, COLOR_GREEN, COLOR_YELLOW, COLOR_RED, COLOR_BLUE]
        }
    else:
        # Stage 0: 徹底打亂 (Scrambled)
        return {
            'U': [COLOR_RED, COLOR_BLUE, COLOR_YELLOW, COLOR_GREEN, COLOR_WHITE, COLOR_ORANGE, COLOR_BLUE, COLOR_WHITE, COLOR_GREEN],
            'D': [COLOR_ORANGE, COLOR_YELLOW, COLOR_RED, COLOR_WHITE, COLOR_YELLOW, COLOR_BLUE, COLOR_GREEN, COLOR_WHITE, COLOR_YELLOW],
            'F': [COLOR_WHITE, COLOR_GREEN, COLOR_RED, COLOR_ORANGE, COLOR_GREEN, COLOR_YELLOW, COLOR_BLUE, COLOR_RED, COLOR_WHITE],
            'B': [COLOR_YELLOW, COLOR_BLUE, COLOR_WHITE, COLOR_RED, COLOR_BLUE, COLOR_GREEN, COLOR_ORANGE, COLOR_YELLOW, COLOR_BLUE],
            'R': [COLOR_GREEN, COLOR_RED, COLOR_ORANGE, COLOR_BLUE, COLOR_RED, COLOR_WHITE, COLOR_YELLOW, COLOR_GREEN, COLOR_RED],
            'L': [COLOR_BLUE, COLOR_ORANGE, COLOR_GREEN, COLOR_YELLOW, COLOR_ORANGE, COLOR_RED, COLOR_WHITE, COLOR_BLUE, COLOR_ORANGE]
        }

def rotate_axis(x, y, z, axis, angle):
    c, s = math.cos(angle), math.sin(angle)
    if axis == 'z':
        return x * c - y * s, x * s + y * c, z
    elif axis == 'x':
        return x, y * c - z * s, y * s + z * c
    elif axis == 'y':
        return x * c + z * s, y, -x * s + z * c
    return x, y, z

def rotate_3d(x, y, z, yaw, pitch):
    cy, sy = math.cos(yaw), math.sin(yaw)
    x1, y1, z1 = x * cy - y * sy, x * sy + y * cy, z
    cp, sp = math.cos(pitch), math.sin(pitch)
    x2, y2, z2 = x1, y1 * cp - z1 * sp, y1 * sp + z1 * cp
    return x2, y2, z2

def render_cube_frame(
    draw: ImageDraw.ImageDraw,
    cx_screen: int,
    cy_screen: int,
    scale: float,
    yaw: float,
    pitch: float,
    color_map: dict,
    turn_axis: str = None,
    turn_condition = None,
    turn_angle: float = 0.0
):
    """繪製具有立體光影與真實貼紙縫隙的高質感 3D 魔術方塊"""
    d = 0.45
    cam_dist = 9.5
    stickers = []

    # U: z = 1.5
    for i in range(3):
        for j in range(3):
            idx = j * 3 + i
            x0, y0 = (i - 1), (j - 1)
            stickers.append({
                'face': 'U',
                'center': (x0, y0, 1.5),
                'corners': [(x0-d, y0-d, 1.5), (x0+d, y0-d, 1.5), (x0+d, y0+d, 1.5), (x0-d, y0+d, 1.5)],
                'norm': (0, 0, 1),
                'color': color_map['U'][idx]
            })

    # D: z = -1.5
    for i in range(3):
        for j in range(3):
            idx = j * 3 + i
            x0, y0 = (i - 1), (j - 1)
            stickers.append({
                'face': 'D',
                'center': (x0, y0, -1.5),
                'corners': [(x0-d, y0+d, -1.5), (x0+d, y0+d, -1.5), (x0+d, y0-d, -1.5), (x0-d, y0-d, -1.5)],
                'norm': (0, 0, -1),
                'color': color_map['D'][idx]
            })

    # F: y = -1.5
    for i in range(3):
        for k in range(3):
            idx = (2 - k) * 3 + i
            x0, z0 = (i - 1), (k - 1)
            stickers.append({
                'face': 'F',
                'center': (x0, -1.5, z0),
                'corners': [(x0-d, -1.5, z0-d), (x0+d, -1.5, z0-d), (x0+d, -1.5, z0+d), (x0-d, -1.5, z0+d)],
                'norm': (0, -1, 0),
                'color': color_map['F'][idx]
            })

    # B: y = 1.5
    for i in range(3):
        for k in range(3):
            idx = (2 - k) * 3 + (2 - i)
            x0, z0 = (i - 1), (k - 1)
            stickers.append({
                'face': 'B',
                'center': (x0, 1.5, z0),
                'corners': [(x0+d, 1.5, z0-d), (x0-d, 1.5, z0-d), (x0-d, 1.5, z0+d), (x0+d, 1.5, z0+d)],
                'norm': (0, 1, 0),
                'color': color_map['B'][idx]
            })

    # R: x = 1.5
    for j in range(3):
        for k in range(3):
            idx = (2 - k) * 3 + j
            y0, z0 = (j - 1), (k - 1)
            stickers.append({
                'face': 'R',
                'center': (1.5, y0, z0),
                'corners': [(1.5, y0-d, z0-d), (1.5, y0+d, z0-d), (1.5, y0+d, z0+d), (1.5, y0-d, z0+d)],
                'norm': (1, 0, 0),
                'color': color_map['R'][idx]
            })

    # L: x = -1.5
    for j in range(3):
        for k in range(3):
            idx = (2 - k) * 3 + (2 - j)
            y0, z0 = (j - 1), (k - 1)
            stickers.append({
                'face': 'L',
                'center': (-1.5, y0, z0),
                'corners': [(-1.5, y0+d, z0-d), (-1.5, y0-d, z0-d), (-1.5, y0-d, z0+d), (-1.5, y0+d, z0+d)],
                'norm': (-1, 0, 0),
                'color': color_map['L'][idx]
            })

    # 繪製方塊底部投影橢圓
    shadow_y = cy_screen + int(scale * 1.85)
    draw.ellipse([
        cx_screen - int(scale * 1.7), shadow_y - int(scale * 0.4),
        cx_screen + int(scale * 1.7), shadow_y + int(scale * 0.4)
    ], fill=(6, 12, 22, 180))

    rendered_polys = []
    for st in stickers:
        c_x, c_y, c_z = st['center']
        norm_x, norm_y, norm_z = st['norm']
        corners = list(st['corners'])

        # 檢查該貼紙是否屬於正在旋轉的層
        if turn_axis and turn_condition and turn_condition(c_x, c_y, c_z):
            norm_x, norm_y, norm_z = rotate_axis(norm_x, norm_y, norm_z, turn_axis, turn_angle)
            corners = [rotate_axis(px, py, pz, turn_axis, turn_angle) for px, py, pz in corners]

        # 旋轉整體方塊視角
        nx, ny, nz = rotate_3d(norm_x, norm_y, norm_z, yaw, pitch)
        if ny < -0.01: # 朝向攝影機 (可視面)
            rot_corners = [rotate_3d(px, py, pz, yaw, pitch) for px, py, pz in corners]
            avg_y = sum(c[1] for c in rot_corners) / len(rot_corners)

            pts = []
            for rx, ry, rz in rot_corners:
                persp = cam_dist / (cam_dist + ry)
                sx = cx_screen + rx * scale * persp
                sy = cy_screen - rz * scale * persp
                pts.append((sx, sy))

            # 3D 光照陰影效果
            light_dir = (-0.4, -0.9, 0.7)
            l_len = math.sqrt(sum(k*k for k in light_dir))
            ld = (light_dir[0]/l_len, light_dir[1]/l_len, light_dir[2]/l_len)
            dot = -(nx*ld[0] + ny*ld[1] + nz*ld[2])
            brightness = 0.52 + 0.48 * max(0.0, dot)
            shaded_col = tuple(min(255, int(c * brightness)) for c in st['color'])

            rendered_polys.append((avg_y, pts, shaded_col))

    # 深度排序（由遠至近繪製）
    rendered_polys.sort(key=lambda item: item[0], reverse=True)
    for avg_y, pts, col in rendered_polys:
        draw.polygon(pts, fill=col, outline=(15, 20, 30), width=4)

def render_rubiks_cube_scene_clip(
    scene: dict,
    duration: float,
    output_clip_path: str,
    is_vertical: bool = False,
    scene_idx: int = 0,
    total_scenes: int = 7,
    audio_path: str = None,
    srt_path: str = None
) -> str:
    """
    動態生成【魔術方塊解法 3D 動畫】影片片段：
    - 即時渲染 3D 魔術方塊逐層旋轉與解法過程
    - 側邊顯示公式口訣、步驟說明、進度條與檢核點
    - 直接串流至 FFmpeg 生成超高清 1080p MP4 片段
    """
    w, h = (1080, 1920) if is_vertical else (1920, 1080)
    fps = 24
    total_frames = max(1, int((duration + 0.3) * fps))

    # 智能判斷或映射還原階段
    scene_text = (scene.get("title", "") + " " + scene.get("badge", "") + " " + scene.get("subtitle", "")).lower()
    is_hook_result = (scene_idx == 0) and any(k in scene_text for k in ["成果", "搶先看", "展示", "全解"])
    if is_hook_result:
        stage_idx = 6 # 開場前 15~30 秒成果搶先看：直接展示六面完全復原的震撼效果！
    elif any(k in scene_text for k in ["打亂", "認識", "結構"]):
        stage_idx = 0
    elif any(k in scene_text for k in ["小花", "底十字", "底層十字", "白色十字"]):
        stage_idx = 1
    elif any(k in scene_text for k in ["第一層", "底層角塊", "角塊歸位", "上左下右"]):
        stage_idx = 2
    elif any(k in scene_text for k in ["第二層", "中層", "f2l"]):
        stage_idx = 3
    elif any(k in scene_text for k in ["頂面十字", "頂十字", "黃色十字"]):
        stage_idx = 4
    elif any(k in scene_text for k in ["小魚", "oll", "翻面", "全黃", "頂面全黃"]):
        stage_idx = 5
    elif any(k in scene_text for k in ["pll", "六面", "全解", "完全復原", "復原", "最後一步"]):
        stage_idx = 6
    else:
        stage_idx = min(6, int(scene_idx * 6 / max(1, total_scenes - 1)))
    color_map = get_stage_cube_colors(stage_idx)

    # 公式與提示設定
    formula_map = {
        0: ("[成果搶先看] 最終全解展示" if is_hook_result else "[狀態] 全隨機打亂", "照著七步層先法口訣，零門檻100%全解復原！" if is_hook_result else "觀察六面顏色，找到白色中心塊作為底面", 100 if is_hook_result else 0),
        1: ("[步驟一] 白色小花與底十字", "口訣：白稜對齊底中心，四邊十字完成", 20),
        2: ("[步驟二] 底層角塊歸位", "口訣公式：上左下右 (R U R' U')", 40),
        3: ("[步驟三] 中層稜塊歸位 (F2L)", "口訣公式：U R U' R' U' F' U F", 65),
        4: ("[步驟四] 頂面黃色十字", "口訣公式：F R U R' U' F'", 80),
        5: ("[步驟五] 小魚公式翻頂面 (OLL)", "口訣公式：R U R' U R U2 R'", 92),
        6: ("[步驟六] 六面完全復原！(PLL)", "口訣公式：R U R' F' R U R' U' R' F R2 U' R'", 100),
    }
    formula_info = formula_map.get(scene_idx, formula_map[min(6, scene_idx)])

    temp_video = output_clip_path + ".raw.mp4"
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
        "-r", str(fps),
        temp_video
    ]

    proc = subprocess.Popen(cmd_ffmpeg, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    # 預備字型
    font_title = get_font(42 if not is_vertical else 32, bold=True)
    font_sub = get_font(26 if not is_vertical else 20, bold=False)
    font_badge = get_font(24 if not is_vertical else 18, bold=True)
    font_formula = get_font(26 if not is_vertical else 20, bold=True)
    font_bullet = get_font(24 if not is_vertical else 18, bold=False)
    font_progress = get_font(20 if not is_vertical else 16, bold=True)

    # 魔術方塊中心位置與大小
    if not is_vertical:
        cube_cx = 1360
        cube_cy = 550
        scale = 145
    else:
        cube_cx = 540
        cube_cy = 1380
        scale = 130

    base_yaw = math.radians(-32)
    base_pitch = math.radians(26)

    # 根據不同階段定義旋轉動作模式
    # 每 48 幀 (2秒) 循環執行一次轉動展示
    period_frames = 48
    active_axis = 'z' if scene_idx in (1, 4, 5) else ('x' if scene_idx in (2, 3, 6) else 'y')

    try:
        for f in range(total_frames):
            frame_t = f / fps
            img = Image.new("RGB", (w, h), (10, 16, 28))
            draw = ImageDraw.Draw(img)

            # 繪製深藍科技漸層背景與環境光
            draw_tech_background(draw, w, h, base_color=(10, 16, 28), accent_color=(6, 182, 212))

            # 漂浮微動態 (Floating animation)
            bob_y = math.sin(frame_t * 2.0) * 12
            cur_cy = int(cube_cy + bob_y)
            cur_yaw = base_yaw + math.sin(frame_t * 0.8) * math.radians(10)
            cur_pitch = base_pitch + math.cos(frame_t * 0.6) * math.radians(5)

            # 計算轉層動畫角度
            cycle_f = f % period_frames
            if cycle_f < 24:
                # 轉動中 (0 ~ 90度，帶平滑 Ease)
                progress = cycle_f / 24.0
                ease_turn = 0.5 * (1 - math.cos(math.pi * progress))
                turn_deg = ease_turn * math.radians(90)
            else:
                # 靜止停留
                turn_deg = 0.0

            # 轉動條件判斷
            if active_axis == 'z':
                cond = lambda x, y, z: z > 0.5 # 頂層 U 轉動
            elif active_axis == 'x':
                cond = lambda x, y, z: x > 0.5 # 右層 R 轉動
            else:
                cond = lambda x, y, z: y < -0.5 # 前層 F 轉動

            # 渲染 3D 魔術方塊本體
            render_cube_frame(
                draw=draw,
                cx_screen=cube_cx,
                cy_screen=cur_cy,
                scale=scale,
                yaw=cur_yaw,
                pitch=cur_pitch,
                color_map=color_map,
                turn_axis=active_axis if turn_deg > 0.01 else None,
                turn_condition=cond if turn_deg > 0.01 else None,
                turn_angle=turn_deg
            )

            # ---------------- 繪製左側教學解說面板 ----------------
            lx = 80 if not is_vertical else 50
            ly = 60

            # 頂部主題徽章
            badge_text = clean_emoji(scene.get("badge", "魔方七步還原法")) or "魔方實戰教學"
            draw.rounded_rectangle([lx, ly, lx + 360, ly + 50], radius=10, fill=(16, 32, 50), outline=(6, 182, 212), width=2)
            draw.ellipse([lx + 16, ly + 17, lx + 32, ly + 33], fill=(6, 182, 212))
            draw.text((lx + 45, ly + 10), badge_text, fill=(6, 182, 212), font=font_badge)

            # 大標題與副標題
            title_text = clean_emoji(scene.get("title", "魔術方塊新手教學"))[:24]
            draw.text((lx, ly + 75), title_text, fill=(255, 255, 255), font=font_title)
            
            sub_text = clean_emoji(scene.get("subtitle", "手把手零基礎公式口訣全解"))[:35]
            draw.text((lx, ly + 145), sub_text, fill=(203, 213, 225), font=font_sub)

            # 公式醒目展示卡
            form_y = ly + 210
            card_w = 760 if not is_vertical else (w - 100)
            draw.rounded_rectangle([lx, form_y, lx + card_w, form_y + 115], radius=14, fill=(15, 25, 42), outline=(245, 158, 11), width=2)
            custom_code = str(scene.get("highlight_box") or scene.get("code") or "").strip()
            display_sub = formula_info[1]
            if custom_code and not any(k in custom_code for k in ["$", "def ", "import "]):
                first_line = custom_code.split("\n")[0].strip()
                if first_line:
                    display_sub = first_line[:42]
            draw.text((lx + 25, form_y + 16), formula_info[0], fill=(250, 204, 21), font=font_formula)
            draw.text((lx + 25, form_y + 65), display_sub, fill=(241, 245, 249), font=get_font(22, bold=False))

            # 步驟條列清單 (Bullets)
            bullet_y = form_y + 145
            bullets = scene.get("bullets", [])
            if not bullets:
                bullets = [
                    "看準中心塊定位，各面顏色永不變",
                    "掌握基本轉動手法，指法順暢更輕鬆",
                    "每一步確實歸位，零失誤快速全解"
                ]

            for b_idx, b in enumerate(bullets[:4]):
                cur_by = bullet_y + (b_idx * 75)
                draw.rounded_rectangle([lx, cur_by, lx + card_w, cur_by + 60], radius=10, fill=(15, 23, 38), outline=(30, 50, 75), width=1)
                draw_vector_check(draw, lx + 35, cur_by + 30, radius=16, bg_color=(16, 185, 129))
                draw.text((lx + 70, cur_by + 16), clean_emoji(b)[:28], fill=(226, 232, 240), font=font_bullet)

            # 還原進度條 (Progress Bar)
            prog_y = bullet_y + (len(bullets[:4]) * 75) + 25
            pct = formula_info[2]
            draw.text((lx, prog_y), f"還原進度：{pct}%", fill=(56, 189, 248), font=font_progress)
            
            bar_w = card_w
            draw.rounded_rectangle([lx, prog_y + 35, lx + bar_w, prog_y + 55], radius=10, fill=(30, 41, 59))
            fill_w = int((bar_w - 4) * (pct / 100.0))
            if fill_w > 0:
                draw.rounded_rectangle([lx + 2, prog_y + 37, lx + 2 + fill_w, prog_y + 53], radius=8, fill=(6, 182, 212))

            # 右上角動態旋轉提示光標
            if turn_deg > 0.01:
                curv_y = 120
                curv_x = cube_cx - 100
                draw.rounded_rectangle([curv_x, curv_y, curv_x + 220, curv_y + 45], radius=10, fill=(234, 88, 12, 220), outline=(251, 146, 60), width=2)
                draw.text((curv_x + 18, curv_y + 10), f"旋轉動作: {active_axis.upper()} 順時針", fill=(255, 255, 255), font=get_font(20, bold=True))

            proc.stdin.write(img.tobytes())

        proc.stdin.close()
        proc.wait()

        # ---------------- 合併音訊與字幕 ----------------
        if audio_path and os.path.exists(audio_path):
            if srt_path and os.path.exists(srt_path):
                optimize_srt_file(srt_path, is_vertical=is_vertical)

            style = get_ffmpeg_subtitles_style(is_vertical=is_vertical)

            cmd_mux = [
                FFMPEG_EXE, "-y",
                "-i", temp_video,
                "-i", audio_path
            ]

            if srt_path and os.path.exists(srt_path):
                srt_clean = srt_path.replace("\\", "/").replace(":", "\\:")
                cmd_mux += [
                    "-filter_complex", f"[0:v]subtitles='{srt_clean}':force_style='{style}'[outv]",
                    "-map", "[outv]", "-map", "1:a"
                ]
            else:
                cmd_mux += ["-map", "0:v", "-map", "1:a"]

            cmd_mux += [
                "-c:v", "libx264", "-preset", "veryfast",
                "-c:a", "aac", "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-t", str(duration + 0.3),
                output_clip_path
            ]
            subprocess.run(cmd_mux, check=True, capture_output=True)
            if os.path.exists(temp_video):
                os.remove(temp_video)
        else:
            if os.path.exists(output_clip_path):
                os.remove(output_clip_path)
            os.rename(temp_video, output_clip_path)

    except Exception as e:
        if proc and proc.stdin:
            try:
                proc.stdin.close()
            except Exception:
                pass
        raise e

    return output_clip_path
