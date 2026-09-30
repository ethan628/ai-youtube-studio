import os
import sys
import argparse
from src.podcast_composer import generate_podcast_full
from src.podcast_generator import generate_podcast_dialogue

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def main():
    parser = argparse.ArgumentParser(description="🎙️ AI YouTube 雙人對談 Podcast 全自動生成器")
    parser.add_argument("--topic", type=str, default="2026 AI 自動化工作流革命", help="播客話題或主題")
    parser.add_argument("--duration", type=float, default=3.0, help="對談目標時長（分鐘）")
    parser.add_argument("--style", type=str, default="科技趨勢對談", help="對談風格（例如：科技趨勢對談 / 深度思維剖析 / 實務避坑指南）")
    parser.add_argument("--preview-only", action="store_true", help="僅生成並顯示對談腳本，不渲染影片")

    args = parser.parse_args()

    print("=" * 60)
    print("🎙️ AI YouTube 雙主持 Podcast 創作中心")
    print(f"📌 主題：{args.topic}")
    print(f"⏱️ 時長：{args.duration} 分鐘")
    print(f"🎭 風格：{args.style}")
    print("=" * 60)

    if args.preview_only:
        meta = generate_podcast_dialogue(args.topic, duration_minutes=args.duration, style=args.style)
        print(f"\n【{meta['title']}】")
        print(f"副標題：{meta['subtitle']}\n")
        for idx, turn in enumerate(meta.get("dialogue", []), 1):
            print(f"[{idx:02d}] [{turn['speaker']}]: {turn['text']}\n")
        return

    result = generate_podcast_full(
        topic=args.topic,
        duration_minutes=args.duration,
        style=args.style
    )

    if result.get("success"):
        print("\n" + "=" * 60)
        print("🎉 播客生成圓滿成功！")
        print(f"🎬 1080p 影片檔案：{os.path.abspath(result['video_path'])}")
        print(f"📻 獨立 MP3 音訊：{os.path.abspath(result['audio_path'])}")
        print(f"📝 繁體中文 SRT 字幕：{os.path.abspath(result['srt_path'])}")
        print("=" * 60)

if __name__ == "__main__":
    main()
