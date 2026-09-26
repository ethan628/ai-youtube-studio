import asyncio
import os
import edge_tts
from datetime import timedelta

DEFAULT_VOICE = "zh-TW-YunJheNeural"  # 台灣微軟自然男聲
FEMALE_VOICE = "zh-TW-HsiaoChenNeural" # 台灣微軟自然女聲

def format_timestamp(td: timedelta) -> str:
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    millis = int(td.microseconds / 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

async def _synthesize_async(text: str, audio_path: str, srt_path: str = None, voice: str = DEFAULT_VOICE, rate: str = "+5%"):
    os.makedirs(os.path.dirname(os.path.abspath(audio_path)), exist_ok=True)
    tts = edge_tts.Communicate(text, voice, rate=rate)
    
    submaker = edge_tts.SubMaker()
    has_sub = False
    
    with open(audio_path, "wb") as f:
        async for chunk in tts.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                submaker.feed(chunk)
                has_sub = True

    if srt_path:
        os.makedirs(os.path.dirname(os.path.abspath(srt_path)), exist_ok=True)
        with open(srt_path, "w", encoding="utf-8") as f:
            if has_sub and len(submaker.cues) > 0:
                f.write(submaker.get_srt())
            else:
                # Fallback: estimate single subtitle for whole sentence if boundaries missing
                f.write(f"1\n00:00:00,000 --> 00:00:05,000\n{text}\n")

def generate_speech(text: str, audio_path: str, srt_path: str = None, voice: str = DEFAULT_VOICE, rate: str = "+5%"):
    """
    同步呼叫 TTS 產生語音與字幕
    支援微軟神經自然語音 (YunJhe / HsiaoChen) 以及自訂個人聲音複製 (clone)
    """
    if voice.startswith("clone") or voice == "my_voice":
        from src.voice_clone import generate_cloned_speech
        sample_path = None
        if ":" in voice:
            sample_path = voice.split(":", 1)[1]
        return generate_cloned_speech(text, audio_path, srt_path, sample_audio_path=sample_path)

    asyncio.run(_synthesize_async(text, audio_path, srt_path, voice, rate))
    return audio_path, srt_path

if __name__ == "__main__":
    test_text = "哈囉大家好，歡迎來到雙AI協同開發！今天帶大家看最神奇的自動化！"
    generate_speech(test_text, "test_speech.mp3", "test_speech.srt")
    print("TTS generation test passed!")
