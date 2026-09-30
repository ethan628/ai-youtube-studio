import os
import sys
import re
from datetime import timedelta

def parse_time(ts_str: str) -> timedelta:
    """解析 SRT 時間標籤字串 (00:00:01,234 或 00:00:01.234)"""
    ts_str = ts_str.replace('.', ',').strip()
    parts = ts_str.split(':')
    h = int(parts[0])
    m = int(parts[1])
    s_parts = parts[2].split(',')
    s = int(s_parts[0])
    ms = int(s_parts[1]) if len(s_parts) > 1 else 0
    return timedelta(hours=h, minutes=m, seconds=s, milliseconds=ms)

def format_time(td: timedelta) -> str:
    """將 timedelta 格式化為標準 SRT 時間戳記 (00:00:01,234)"""
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    millis = int(td.microseconds / 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

def get_cjk_len(s: str) -> int:
    """計算文字顯示單位寬度：中文字元/全形為 2 單位，英數半形為 1 單位"""
    return sum(2 if ord(c) > 127 else 1 for c in s)

def split_into_clauses(text: str, max_units: int = 76) -> list:
    """
    將過長的一句話，依標點符號（句點、逗點、頓號）自然拆分為多個短子句。
    避免單一字幕在畫面上停留過久或塞入過多字元。
    """
    text = text.strip()
    if get_cjk_len(text) <= max_units:
        return [text]

    # 第一階段：以主要結束標點（。！？\n）拆分
    puncts = r'([。！？\n])'
    chunks = re.split(puncts, text)
    sentences = []
    for i in range(0, len(chunks) - 1, 2):
        if chunks[i] or chunks[i + 1]:
            sentences.append(chunks[i] + chunks[i + 1])
    if len(chunks) % 2 == 1 and chunks[-1]:
        sentences.append(chunks[-1])

    result = []
    cur = ""
    for s in sentences:
        s_clean = s.strip()
        if not s_clean:
            continue
        if get_cjk_len(cur + s_clean) <= max_units:
            cur += s_clean
        else:
            if cur:
                result.append(cur)
            # 若單一句子依然超過上限，以次要標點（，；、 , ;）繼續細分
            if get_cjk_len(s_clean) > max_units:
                comma_parts = re.split(r'([，；、,; ])', s_clean)
                sub_parts = []
                for j in range(0, len(comma_parts) - 1, 2):
                    sub_parts.append(comma_parts[j] + comma_parts[j + 1])
                if len(comma_parts) % 2 == 1 and comma_parts[-1]:
                    sub_parts.append(comma_parts[-1])

                cur_sub = ""
                for cp in sub_parts:
                    if not cp.strip():
                        continue
                    if get_cjk_len(cur_sub + cp) <= max_units:
                        cur_sub += cp
                    else:
                        if cur_sub:
                            result.append(cur_sub)
                        cur_sub = cp
                cur = cur_sub
            else:
                cur = s_clean
    if cur:
        result.append(cur)

    # 保底機制：若仍有片段超過上限，強制以字元邊界切割
    final_res = []
    for r in result:
        r = r.strip()
        if not r:
            continue
        if get_cjk_len(r) <= max_units:
            final_res.append(r)
        else:
            cur_hard = ""
            for ch in r:
                if get_cjk_len(cur_hard + ch) > max_units:
                    final_res.append(cur_hard)
                    cur_hard = ch
                else:
                    cur_hard += ch
            if cur_hard:
                final_res.append(cur_hard)
    return final_res

def wrap_two_lines(text: str, max_line_units: int = 38) -> str:
    """
    將一段文字智慧斷為最多兩行，優先在中心點附近的標點符號換行，
    保證畫面上字幕左右平衡，絕不溢出螢幕。
    """
    text = text.strip()
    if get_cjk_len(text) <= max_line_units:
        return text

    # 尋找靠近正中間的標點斷句
    puncts = ['，', '。', '！', '？', '；', '、', ' ', ',', '!', '?']
    mid = len(text) // 2
    best_split = -1
    best_diff = 999
    for i, ch in enumerate(text):
        if ch in puncts and 2 <= i <= len(text) - 2:
            diff = abs(i - mid)
            if diff < best_diff:
                best_diff = diff
                best_split = i + 1

    if best_split != -1:
        l1 = text[:best_split].strip()
        l2 = text[best_split:].strip()
        if l1 and l2 and get_cjk_len(l1) <= max_line_units + 6 and get_cjk_len(l2) <= max_line_units + 6:
            return f"{l1}\n{l2}"

    # 無適當標點時，依照長度硬折行
    l1 = ""
    l2 = ""
    for ch in text:
        if get_cjk_len(l1 + ch) <= max_line_units:
            l1 += ch
        else:
            l2 += ch
    if l2:
        return f"{l1}\n{l2}"
    return l1

def optimize_srt(raw_srt: str, is_vertical: bool = False) -> str:
    """
    將原始 SRT 字幕字串重新排版與時間平衡：
    1. 解析所有 Cue
    2. 若文字長度超出單行上限，自動拆分為標點對齊的 1~2 行
    3. 若整體過長，自動切分為多段獨立的時間同步 Cue
    4. 回傳格式純淨、保證不會超出影片畫面的完美 SRT 字串
    """
    if not raw_srt or not raw_srt.strip():
        return ""
    max_line = 24 if is_vertical else 38
    max_cue = max_line * 2

    raw_srt = raw_srt.replace('\r\n', '\n').replace('\r', '\n')
    blocks = re.split(r'\n\s*\n', raw_srt.strip())
    parsed_cues = []
    for b in blocks:
        lines = [l.strip() for l in b.split('\n') if l.strip()]
        if len(lines) < 2:
            continue
        time_idx = -1
        for i, l in enumerate(lines):
            if '-->' in l:
                time_idx = i
                break
        if time_idx == -1:
            continue
        time_line = lines[time_idx]
        t_start_s, t_end_s = time_line.split('-->')
        try:
            start_td = parse_time(t_start_s)
            end_td = parse_time(t_end_s)
        except Exception:
            continue
        txt = ''.join(lines[time_idx + 1:])
        if txt.strip():
            parsed_cues.append((start_td, end_td, txt.strip()))

    if not parsed_cues:
        return raw_srt

    new_cues = []
    for start_td, end_td, txt in parsed_cues:
        clauses = split_into_clauses(txt, max_units=max_cue)
        if len(clauses) <= 1:
            wrapped = wrap_two_lines(txt, max_line_units=max_line)
            new_cues.append((start_td, end_td, wrapped))
        else:
            total_dur = max(0.5, (end_td - start_td).total_seconds())
            total_chars = max(1, sum(get_cjk_len(c) for c in clauses))
            cur_st = start_td
            for idx, c in enumerate(clauses):
                c_dur = total_dur * (get_cjk_len(c) / total_chars)
                if idx == len(clauses) - 1:
                    cur_et = end_td
                else:
                    cur_et = cur_st + timedelta(seconds=c_dur)
                wrapped = wrap_two_lines(c, max_line_units=max_line)
                new_cues.append((cur_st, cur_et, wrapped))
                cur_st = cur_et

    output_lines = []
    for idx, (st, et, txt) in enumerate(new_cues, 1):
        output_lines.append(f"{idx}")
        output_lines.append(f"{format_time(st)} --> {format_time(et)}")
        output_lines.append(txt)
        output_lines.append("")
    return "\n".join(output_lines)

def optimize_srt_file(srt_path: str, is_vertical: bool = False) -> str:
    """讀取既有 SRT 檔案，進行智慧斷行、長句分句、時間重平衡，並覆寫回檔案"""
    if not srt_path or not os.path.exists(srt_path):
        return srt_path
    try:
        with open(srt_path, "r", encoding="utf-8") as f:
            content = f.read()
        opt = optimize_srt(content, is_vertical=is_vertical)
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(opt)
    except Exception as e:
        print(f"⚠️ 優化字幕檔案失敗 ({srt_path}): {e}")
    return srt_path

def get_ffmpeg_subtitles_style(is_vertical: bool = False) -> str:
    """
    回傳符合 YouTube / Shorts 官方安全區的高清 ASS/SRT 字幕樣式字串：
    - 明確宣告 PlayResX 與 PlayResY，徹底解決 libass 預設 384x288 導致字體爆大超出畫面的致命缺陷！
    - 設定 MarginL 與 MarginR 安全邊距，杜絕字幕被左右兩側黑邊或影片邊緣切字。
    - 設定 MarginV 安全避開 YouTube 播放器進度條與 Shorts 互動按鈕。
    """
    if sys.platform.startswith("win"):
        font_name = "Microsoft JhengHei"
    elif sys.platform == "darwin":
        font_name = "PingFang TC"
    else:
        font_name = "Noto Sans CJK TC"

    if not is_vertical:
        # 16:9 橫向長片 (1920x1080)
        # 字體大小 40px，底部邊距 55px (安全避開播放控制列)，左右安全邊距各 140px
        return (
            f"PlayResX=1920,PlayResY=1080,"
            f"FontName={font_name},FontSize=40,Bold=1,"
            f"PrimaryColour=&H00FFFFFF,SecondaryColour=&H00000000,"
            f"OutlineColour=&H00000000,BackColour=&H80000000,"
            f"BorderStyle=1,Outline=2.8,Shadow=1.5,"
            f"Alignment=2,MarginV=55,MarginL=140,MarginR=140"
        )
    else:
        # 9:16 直向短影音 (1080x1920)
        # 字體大小 42px，底部邊距 180px (安全避開標題、作者名稱、按讚留言按鈕)，左右安全邊距各 80px
        return (
            f"PlayResX=1080,PlayResY=1920,"
            f"FontName={font_name},FontSize=42,Bold=1,"
            f"PrimaryColour=&H00FFFFFF,SecondaryColour=&H00000000,"
            f"OutlineColour=&H00000000,BackColour=&H80000000,"
            f"BorderStyle=1,Outline=2.8,Shadow=1.5,"
            f"Alignment=2,MarginV=180,MarginL=80,MarginR=80"
        )
