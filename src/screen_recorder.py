import os
import sys
import time
import subprocess
import tempfile
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

def create_watermark_image(title: str, target_path: str, width: int = 720, height: int = 56) -> str:
    """
    使用 Pillow 渲染帶有圓角半透明深藍膠囊、科技青邊框與繁中字型的錄影示範標題浮水印。
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 膠囊背景
    draw.rounded_rectangle([2, 2, width - 3, height - 3], radius=16, fill=(15, 23, 42, 215), outline=(56, 189, 248, 240), width=2)

    # 載入繁體中文字型
    font = None
    for fpath in [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf"
    ]:
        if os.path.exists(fpath):
            try:
                if fpath.endswith(".ttc"):
                    font = ImageFont.truetype(fpath, 20, index=3)
                else:
                    font = ImageFont.truetype(fpath, 20)
                break
            except Exception:
                pass
    if font is None:
        font = ImageFont.load_default()

    # 錄製紅點呼吸燈
    dot_r = 6
    dot_cx, dot_cy = 28, height // 2
    draw.ellipse([dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r], fill=(239, 68, 68, 255))

    clean_title = title if title else "AI 全自動無人操作示範"
    if len(clean_title) > 28:
        clean_title = clean_title[:27] + "..."
    display_text = f"REC · 示範：{clean_title}"
    draw.text((46, 15), display_text, font=font, fill=(240, 249, 255, 255))

    img.save(target_path, "PNG")
    return target_path

class ScreenRecorder:
    """
    FFmpeg x11grab 背景螢幕錄製器，支援動態浮水印與 1080p 橫向長片輸出。
    """
    def __init__(self, output_path: str = None, display: str = None, title_watermark: str = "", resolution: str = "1920x1080", fps: int = 30):
        if not output_path:
            os.makedirs("output_recordings", exist_ok=True)
            ts = int(time.time())
            output_path = os.path.abspath(f"output_recordings/autopilot_rec_{ts}.mp4")
        else:
            output_path = os.path.abspath(output_path)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

        self.output_path = output_path
        self.display = display or os.environ.get("DISPLAY", ":0.0")
        if not self.display.startswith(":"):
            self.display = ":0.0"
        self.title_watermark = title_watermark
        self.resolution = resolution
        self.fps = fps
        self.proc = None
        self.temp_wm_path = None

    def start(self) -> bool:
        """背景啟動錄影進程"""
        if self.is_active():
            return True

        # 準備浮水印圖片
        wm_file = None
        if self.title_watermark:
            self.temp_wm_path = tempfile.mktemp(suffix=".png")
            create_watermark_image(self.title_watermark, self.temp_wm_path)
            wm_file = self.temp_wm_path

        # 構建 FFmpeg 命令
        cmd = [
            FFMPEG_EXE, "-y",
            "-f", "x11grab",
            "-framerate", str(self.fps),
            "-i", self.display
        ]

        if wm_file and os.path.exists(wm_file):
            cmd += [
                "-i", wm_file,
                "-filter_complex", "[0:v]scale=1920:1080[base];[base][1:v]overlay=(W-w)/2:28[outv]",
                "-map", "[outv]"
            ]
        else:
            cmd += [
                "-vf", "scale=1920:1080"
            ]

        cmd += [
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            self.output_path
        ]

        env = os.environ.copy()
        if "XAUTHORITY" not in env:
            # 自動定位常見 XAUTHORITY
            for cand in [
                os.path.expanduser("~/.Xauthority"),
                f"/run/user/{os.getuid()}/.mutter-Xwaylandauth.*"
            ]:
                if os.path.exists(cand):
                    env["XAUTHORITY"] = cand
                    break

        try:
            self.proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            time.sleep(0.8) # 確保 FFmpeg 成功擷取
            if self.proc.poll() is not None:
                err = self.proc.stderr.read()
                print(f"⚠️ FFmpeg 錄影啟動失敗: {err[-400:]}")
                return False
            return True
        except Exception as e:
            print(f"⚠️ 啟動螢幕錄影失敗: {e}")
            return False

    def stop(self) -> bool:
        """優雅停止錄影並封裝 MP4"""
        if not self.proc:
            return os.path.exists(self.output_path) and os.path.getsize(self.output_path) > 1000

        try:
            # 送出 'q' 讓 FFmpeg 平順封裝
            if self.proc.stdin:
                try:
                    self.proc.stdin.write("q\n")
                    self.proc.stdin.flush()
                except Exception:
                    pass
            
            try:
                self.proc.wait(timeout=4)
            except subprocess.TimeoutExpired:
                self.proc.terminate()
                self.proc.wait(timeout=3)
        except Exception as e:
            print(f"⚠️ 停止錄影異常: {e}")
        finally:
            self.proc = None
            if self.temp_wm_path and os.path.exists(self.temp_wm_path):
                try:
                    os.remove(self.temp_wm_path)
                except Exception:
                    pass

        return os.path.exists(self.output_path) and os.path.getsize(self.output_path) > 1000

    def is_active(self) -> bool:
        """檢查錄製是否正在進行中"""
        return self.proc is not None and self.proc.poll() is None
