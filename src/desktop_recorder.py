import os
import sys
import subprocess
import time
import imageio_ffmpeg

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

def record_physical_desktop(duration: float = 10.0, output_path: str = None) -> str:
    """
    錄製本機實體螢幕畫面 (跨平台支援 Windows gdigrab, macOS avfoundation, Linux x11grab)
    若系統為無人機/無顯示權限環境，則自動優雅切換為虛擬無人電腦操作錄製引擎。
    """
    if not output_path:
        os.makedirs("output_recordings", exist_ok=True)
        ts = int(time.time())
        output_path = f"output_recordings/desktop_rec_{ts}.mp4"

    cmd = [FFMPEG_EXE, "-y"]

    if sys.platform.startswith("win"):
        cmd += ["-f", "gdigrab", "-framerate", "30", "-i", "desktop"]
    elif sys.platform == "darwin":
        cmd += ["-f", "avfoundation", "-framerate", "30", "-i", "1:none"]
    else:
        # Linux
        disp = os.environ.get("DISPLAY", ":0.0")
        cmd += ["-f", "x11grab", "-video_size", "1920x1080", "-framerate", "30", "-i", disp]

    cmd += [
        "-t", str(duration),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        output_path
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 15)
        if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            return output_path
    except Exception as e:
        print(f"⚠️ 實體螢幕擷取未授權或無顯示器 ({e})，自動切換至無人高畫質電腦操作錄製引擎！")

    # 優雅降級：自動調用虛擬無人電腦操作引擎
    from src.auto_pilot_recorder import run_autopilot_recording
    return run_autopilot_recording(mode="terminal", duration=duration, output_filename=os.path.basename(output_path))
