import os
import sys
import glob
from datetime import datetime
from src.podcast_visualizer import convert_audio_to_podcast_video

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

INPUT_DIR = "inputs_notebooklm"
OUTPUT_DIR = "output_videos"

def run_notebooklm_converter(audio_file: str = None, title: str = None, subtitle: str = None):
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not audio_file:
        # 自動搜尋 inputs_notebooklm 中的音訊檔案
        patterns = [os.path.join(INPUT_DIR, f"*.{ext}") for ext in ["m4a", "mp3", "wav", "aac"]]
        files = []
        for p in patterns:
            files.extend(glob.glob(p))

        if not files:
            print("=" * 60)
            print("⚠️ 未在 inputs_notebooklm 資料夾中找到音訊檔案！")
            print("💡 使用方式：")
            print("  1. 前往 Google NotebookLM (https://notebooklm.google.com)")
            print("  2. 上傳你的筆記或文章，點擊生成「Audio Overview (語音導覽)」")
            print("  3. 下載音訊 (.m4a 或 .mp3)，放入 inputs_notebooklm 資料夾")
            print("  4. 再次執行本程式，即可自動生成 1080p Podcast 影片！")
            print("=" * 60)
            return None
        
        audio_file = files[0]
        print(f"🔍 自動選取找到的第一個音訊檔：{audio_file}")

    if not os.path.exists(audio_file):
        print(f"❌ 找不到指定的音訊檔案：{audio_file}")
        return None

    base_name = os.path.splitext(os.path.basename(audio_file))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_filename = f"notebooklm_{base_name}_{timestamp}.mp4"
    output_path = os.path.join(OUTPUT_DIR, out_filename)

    vid_title = title or f"Google NotebookLM 深度對談：{base_name}"
    vid_sub = subtitle or "AI 雙主講精華提煉 ⚡ 雙AI協同實戰"

    print("=" * 60)
    print(f"🚀 開始將 NotebookLM 音訊轉換為高畫質影片...")
    print(f"📁 音訊來源：{audio_file}")
    print(f"🎯 輸出目標：{output_path}")
    print("=" * 60)

    convert_audio_to_podcast_video(
        audio_path=audio_file,
        output_video_path=output_path,
        title=vid_title,
        subtitle=vid_sub
    )

    print("=" * 60)
    print(f"🎉 影片合成完畢！檔案路徑：\n{os.path.abspath(output_path)}")
    print("=" * 60)
    return output_path

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Google NotebookLM 音訊轉 YouTube 影片工具")
    parser.add_argument("--audio", type=str, help="音訊檔案路徑 (m4a/mp3)")
    parser.add_argument("--title", type=str, help="影片主標題")
    parser.add_argument("--subtitle", type=str, help="影片副標題")
    args = parser.parse_args()

    run_notebooklm_converter(args.audio, args.title, args.subtitle)
