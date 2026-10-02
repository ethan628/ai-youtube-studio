#!/usr/bin/env python3
"""
🎤 AI 歌聲克隆與唱歌合成獨立命令行工具 (CLI Entry)
使用方式：
    python create_singing.py --song "happy_birthday" --style "pop"
    python create_singing.py --song "twinkle_star" --style "ballad"
    python create_singing.py --song "moon_heart" --voice "my_voice.mp3"
"""

import os
import sys
import argparse

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.singing_composer import generate_singing_full, PRESET_SONGS

def main():
    parser = argparse.ArgumentParser(description="🎤 AI 歌聲克隆與唱歌合成工具")
    parser.add_argument("--song", type=str, default="happy_birthday", help="歌曲代號 (happy_birthday, twinkle_star, moon_heart, glorious_days) 或 custom")
    parser.add_argument("--lyrics", type=str, default=None, help="自訂歌詞 (每行一句)")
    parser.add_argument("--voice", type=str, default=None, help="聲音樣本路徑 (預設使用 voice_samples/ 內之錄音)")
    parser.add_argument("--style", type=str, default="pop", choices=["pop", "ballad", "rock", "electronic"], help="歌唱音樂風格")
    parser.add_argument("--reverb", type=str, default="ktv", choices=["ktv", "studio", "hall"], help="混響空間感")
    args = parser.parse_args()

    print(f"🌟 啟動 AI 歌聲克隆唱歌合成管線...")
    res = generate_singing_full(
        song_id=args.song,
        custom_lyrics=args.lyrics,
        sample_voice_path=args.voice,
        style=args.style,
        reverb_type=args.reverb
    )
    if res.get("success"):
        print("\n🎉 恭喜！個人歌聲克隆翻唱作品已大功告成！")
        print(f"🎬 1080p KTV 音樂 MV 影片：output_videos/{res['video_file']}")
        print(f"🎧 獨立高音質歌曲音訊：output_videos/{res['audio_file']}")
    else:
        print("\n❌ 合成失敗，請檢查輸入參數或聲音樣本。")

if __name__ == "__main__":
    main()
