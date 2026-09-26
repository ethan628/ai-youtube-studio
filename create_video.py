import os
import sys
from datetime import datetime
from src.composer import compose_video

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

OUTPUT_DIR = "output_videos"

# 內建預設熱門模板（契合頻道「雙AI協同、不寫程式、實用黑科技」風格）
PRESET_TEMPLATES = {
    "1": {
        "name": "雙AI協同 EP5：不寫Python也能做！打造個人自動化知識庫",
        "output_prefix": "雙AI協同_EP5_個人知識庫",
        "scenes": [
            {
                "badge": "雙AI協同 EP5",
                "title": "不寫 Python 也能做！",
                "subtitle": "教你用三大 AI 打造個人專屬自動化知識庫",
                "bullets": [
                    "零代碼門檻：文字指令直接驅動",
                    "三大 AI 協同：自動整合整理資料",
                    "秒級精準檢索：再多筆記也能一秒找到"
                ],
                "highlight_box": "$ antigravity run kb-agent\n>>> Indexing your documents...\n>>> 1,250 docs indexed!\n>>> Ready to query: 100%",
                "narration": "哈囉大家好，歡迎來到雙AI協同開發！很多新手想做自己的專屬知識庫，但卡在複雜的Python環境與資料庫設定。今天教大家不寫一行代碼，5分鐘搞定！"
            },
            {
                "badge": "架構核心",
                "title": "三大 AI 各司其職！",
                "subtitle": "從資料擷取、語音分析到界面生成",
                "bullets": [
                    "Gemini 3.8：超長上下文分析與推理",
                    "Claude 3.7：精確邏輯與架構輸出",
                    "Antigravity：本地執行與一鍵建置"
                ],
                "highlight_box": "[Workflow Pipeline]\nDocs -> Gemini (Analyze)\n-> Claude (Structure)\n-> Antigravity (Run)",
                "narration": "核心秘訣就在於分工：讓 Gemini 負責海量文件理解，Claude 負責整理知識脈絡，最後交給 Antigravity 自動在你的電腦上跑起來。"
            },
            {
                "badge": "實機效果",
                "title": "只需一句話，知識庫自動回答",
                "subtitle": "不僅能找筆記，還能直接生成報告",
                "bullets": [
                    "支援 PDF、Word、網頁一鍵匯入",
                    "內建語音發音與重點摘要",
                    "完全免費、完全私密運行"
                ],
                "highlight_box": "User: 幫我總結今年第三季的重點\nAgent: 已為您提煉三大核心結論...\nDone in 0.8s!",
                "narration": "你看，現在只要對著它問問題，它就能在零點幾秒內從成千上萬篇筆記中找出答案，甚至直接幫你寫好總結報告，效率直接翻倍！"
            },
            {
                "badge": "結尾彩蛋",
                "title": "立即動手打造專屬神器！",
                "subtitle": "點擊訂閱，帶你掌握 2026 最強 AI 工作流",
                "bullets": [
                    "完整專案配置與指令已放說明欄",
                    "歡迎在留言區分享你的點子",
                    "記得按讚、訂閱、開啟小鈴鐺！"
                ],
                "highlight_box": "Subscribe & Like!\n>>> Next Episode:\nAI Agent 自動操作系統進階篇",
                "narration": "是不是超級簡單？喜歡這類不寫程式的高效 AI 實戰教學，記得按讚、訂閱並開啟小鈴鐺，我們下一期再見！"
            }
        ]
    },
    "2": {
        "name": "2026最強工作流：瀏覽器AI一鍵抓取全網數據",
        "output_prefix": "2026最強工作流_網頁資料抓取",
        "scenes": [
            {
                "badge": "2026最強工作流",
                "title": "手殘黨救星！全網數據自動抓",
                "subtitle": "不用寫爬蟲代碼，瀏覽器直接變成資料收集器",
                "bullets": [
                    "告別複雜的 Request 與 Token",
                    "肉眼看到的內容，AI 幫你秒存表格",
                    "支援各類電商、新聞與即時行情"
                ],
                "highlight_box": "$ ai-scraper --target \"market\"\n>>> Analyzing DOM elements...\n>>> Extracted 50 items!\n>>> Saved to Excel.",
                "narration": "還在手動複製貼上網頁資料嗎？今天教你2026最新工作流，不用寫任何爬蟲代碼，讓AI直接幫你把網頁變成結構化 Excel！"
            },
            {
                "badge": "核心操作",
                "title": "只要框選畫面，AI 自動辨識",
                "subtitle": "多模態視覺模型精準提取關鍵欄位",
                "bullets": [
                    "自動過濾廣告與無效干擾",
                    "自動對齊欄位：品名、價格、庫存",
                    "一鍵導出 CSV 與 Excel 格式"
                ],
                "highlight_box": "Field: [產品名稱, 售價, 銷量]\n[Item 1]: 降噪耳機 | $2,990 | 1.2k sold\n[Item 2]: 機械鍵盤 | $1,880 | 850 sold",
                "narration": "你只要在畫面上框出想抓的區塊，AI 視覺模型就會自動讀取品名、價格和規格，乾淨俐落地幫你填進表格裡！"
            },
            {
                "badge": "訂閱頻道",
                "title": "解放雙手，下班不加班！",
                "subtitle": "把重複性苦工全部交給 AI",
                "bullets": [
                    "說明欄附一鍵安裝腳本",
                    "留言區告訴我你想抓取什麼網站",
                    "按讚訂閱，不錯過每週黑科技！"
                ],
                "highlight_box": "Workflow Completed!\nSaved 2 hours today!\nKeep learning with us.",
                "narration": "學會這招，原本要花兩小時的複製貼上，十秒鐘就搞定！記得按讚訂閱，我們下期見！"
            }
        ]
    }
}

def generate_video_from_template(template_id: str = "1", is_vertical: bool = False, voice: str = "zh-TW-YunJheNeural"):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tpl = PRESET_TEMPLATES.get(template_id, PRESET_TEMPLATES["1"])
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    aspect_tag = "shorts" if is_vertical else "16x9"
    filename = f"{tpl['output_prefix']}_{aspect_tag}_{timestamp}.mp4"
    output_path = os.path.join(OUTPUT_DIR, filename)

    print("=" * 60)
    print(f"🎬 開始全自動生成影片：【{tpl['name']}】")
    print(f"📐 影片比例：{'9:16 (YouTube Shorts)' if is_vertical else '16:9 (YouTube 長片)'}")
    print(f"🎯 輸出目錄：{os.path.abspath(output_path)}")
    print("=" * 60)

    compose_video(
        scenes=tpl["scenes"],
        output_video_path=output_path,
        is_vertical=is_vertical,
        voice=voice,
        watermark="雙AI協同開發 | 2026自動化"
    )

    print("=" * 60)
    print(f"🎉 影片生成成功！已存入統一資料夾：\n{os.path.abspath(output_path)}")
    print("=" * 60)
    return output_path

def generate_custom_video(topic: str, duration_minutes: float = 3.0, is_vertical: bool = False, voice: str = "zh-TW-YunJheNeural", custom_scenes: list = None):
    """
    支援自訂輸入腳本分鏡，或透過內建 AI 根據主題與指定分鐘數自動編寫腳本，並合成完整影片
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    if custom_scenes and len(custom_scenes) > 0:
        print("=" * 60)
        print(f"✍️ 使用自訂輸入腳本：【{topic}】，共 {len(custom_scenes)} 個場景分鏡。")
        scenes = []
        for i, s in enumerate(custom_scenes):
            scenes.append({
                "badge": s.get("badge", f"場景 0{i+1}"),
                "title": s.get("title", f"場景 {i+1}"),
                "subtitle": s.get("subtitle", ""),
                "bullets": s.get("bullets", []),
                "code": s.get("code", ""),
                "narration": s.get("narration", s.get("title", ""))
            })
    else:
        from src.script_generator import generate_script_by_ai
        print("=" * 60)
        print(f"🤖 正在啟動內建 AI 為您編寫【{topic}】({duration_minutes} 分鐘) 專屬影片腳本...")
        script_data = generate_script_by_ai(topic=topic, duration_minutes=duration_minutes)
        scenes = script_data["scenes"]
        print(f"✅ AI 腳本編寫完成！共編排了 {len(scenes)} 個高質感分鏡與自然旁白。")
    print("=" * 60)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    aspect_tag = "shorts" if is_vertical else "16x9"
    safe_topic = "".join([c for c in topic if c.isalnum() or c in ("_", "-")])[:20] or "自訂腳本"
    filename = f"AI生成_{safe_topic}_{int(duration_minutes)}分_{aspect_tag}_{timestamp}.mp4"
    output_path = os.path.join(OUTPUT_DIR, filename)

    compose_video(
        scenes=scenes,
        output_video_path=output_path,
        is_vertical=is_vertical,
        voice=voice,
        watermark="雙AI協同開發 | 2026自動化"
    )

    print("=" * 60)
    print(f"🎉 影片生成成功！已存入統一資料夾：\n{os.path.abspath(output_path)}")
    print("=" * 60)
    return output_path

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="一鍵免費生成 YouTube 影片工具 (支援 AI 自動寫腳本 & 聲音模仿)")
    parser.add_argument("--template", type=str, default=None, help="選擇預設模板 (1 或 2)")
    parser.add_argument("--topic", type=str, default=None, help="自訂主題，讓內建 AI 為您全自動寫腳本")
    parser.add_argument("--script-file", type=str, default=None, help="指定自訂腳本 JSON 檔案路徑")
    parser.add_argument("--duration", type=float, default=3.0, help="設定影片長度 (分鐘數，例如 1 代表 1 分鐘 Shorts，3 代表 3 分鐘長片)")
    parser.add_argument("--shorts", action="store_true", help="生成直式 9:16 短影音 (YouTube Shorts)")
    parser.add_argument("--voice", type=str, default="zh-TW-YunJheNeural", help="TTS配音角色 (男聲 YunJhe、女聲 HsiaoChen、或 clone:my_voice 模仿自己聲音)")
    parser.add_argument("--voice-sample", type=str, default=None, help="個人聲音樣本檔案路徑 (例如 voice_samples/my_voice.wav)")
    args = parser.parse_args()

    voice_choice = args.voice
    if args.voice_sample:
        voice_choice = f"clone:{args.voice_sample}"
    elif args.voice in ("clone", "my_voice"):
        voice_choice = "clone"

    custom_scenes = None
    if args.script_file and os.path.exists(args.script_file):
        with open(args.script_file, "r", encoding="utf-8") as sf:
            custom_scenes = json.load(sf)

    if args.topic or custom_scenes:
        topic_name = args.topic if args.topic else "自訂輸入腳本"
        generate_custom_video(topic_name, duration_minutes=args.duration, is_vertical=args.shorts, voice=voice_choice, custom_scenes=custom_scenes)
    else:
        tpl_id = args.template if args.template else "1"
        generate_video_from_template(tpl_id, is_vertical=args.shorts, voice=voice_choice)
