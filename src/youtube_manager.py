import os
import sys
import json
import time
import glob
from typing import Dict, List, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

QUEUE_FILE = os.path.join(PROJECT_ROOT, "publish_queue.json")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output_videos")

from src.script_generator import is_programming_topic

def clean_title_from_filename(filename: str) -> str:
    """從檔名解析乾淨的主題名稱"""
    bname = os.path.basename(filename)
    clean = bname.replace(".mp4", "").replace("AI生成_", "").replace("Shorts預告_", "")
    parts = clean.split("_")
    return parts[0] if parts else clean

def generate_seo_metadata(filename: str, custom_topic: Optional[str] = None) -> Dict:
    """
    根據影片屬性自動生成高點擊率標題、完整結構化說明欄、時間軸與 SEO 標籤 (專注 16:9 橫向長影片)。
    嚴格遵循規範：非程式主題嚴禁出現任何代碼、終端機命令、pip 或 Python 標籤。
    """
    topic = custom_topic or clean_title_from_filename(filename)
    from src.rubiks_cube_engine import is_rubiks_cube_topic
    is_rubik = is_rubiks_cube_topic(topic)
    is_code = False if is_rubik else is_programming_topic(topic)
    
    if is_rubik:
        title = f"【新手必看】{topic}｜零基礎魔術方塊七步還原法教學（含3D解法動畫與公式口訣）"
        if len(title) > 98:
            title = f"【新手必看】{topic[:40]}｜魔術方塊七步還原法（含3D動畫與公式）"

        desc = (
            f"🎲 本集深度解析：{topic}\n\n"
            f"想要徹底解開手中的魔術方塊，卻總是被複雜的公式搞得暈頭轉向嗎？\n"
            f"今天這部影片為大家帶來最清晰、最容易上手的「七步層先法」還原教學！\n"
            f"搭配即時 3D 旋轉解法動畫與朗朗上口的口訣，手把手帶你一步一步完全復原六面！\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⏱️ 影片章節導覽 (Timestamps)：\n"
            f"00:00 - 魔方結構認識與基礎旋轉手法\n"
            f"00:35 - 步驟一：白色小花與底層十字 (White Cross)\n"
            f"01:20 - 步驟二：黃金口訣上左下右，搞定第一層 (First Layer)\n"
            f"02:10 - 步驟三：中層稜塊推入，完成前兩層 (F2L)\n"
            f"02:55 - 步驟四：頂面黃色十字 (Yellow Cross)\n"
            f"03:40 - 步驟五：小魚公式翻出頂面全黃 (OLL)\n"
            f"04:25 - 步驟六：車燈換角與換稜，六面完全復原！(PLL)\n"
            f"05:10 - 總結與提速練習心法\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🧩 本集必背核心公式口訣表 (Cheat Sheet)：\n\n"
            f"1. 【黃金右手口訣】：上 左 下 右 (R U R' U')\n"
            f"   - 用途：底層角塊歸位，重複 1~5 次自動歸位\n\n"
            f"2. 【中層稜塊公式】：U R U' R' U' F' U F\n"
            f"   - 用途：頂層無黃稜塊向右推進中層槽位\n\n"
            f"3. 【頂面十字公式】：F R U R' U' F'\n"
            f"   - 用途：點 -> 折線 -> 水平一字 -> 黃色十字\n\n"
            f"4. 【小魚翻頂公式 (OLL)】：R U R' U R U2 R'\n"
            f"   - 口訣：上左下左 上左左下（魚頭朝向左下角）\n\n"
            f"5. 【六面全解公式 (PLL)】：R U R' F' R U R' U' R' F R2 U' R'\n"
            f"   - 用途：雙同色車燈置於後方，換角換稜六面全解\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💡 魔方練習心法：\n"
            f"• 中心塊永遠不變，看清中心定位各面顏色。\n"
            f"• 每天練習 10 分鐘，讓公式轉化為肌肉記憶。\n"
            f"• 先求步步精確不失誤，手速自然會飛快提升！\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔔 記得按讚、訂閱並開啟小鈴鐺，第一時間掌握更多魔方速解與思維技巧！\n"
            f"歡迎在留言區分享你的復原成績，我會親自回覆交流！\n\n"
            f"#魔術方塊 #魔方教學 #三階魔方 #魔方解法 #層先法 #RubiksCube #3D動畫教學 #益智遊戲 #益智玩具 #速解魔方"
        )
        tags = [
            "魔術方塊", "魔方教學", "魔方解法", "三階魔方", "層先法",
            "RubiksCube", "3D動畫教學", "益智遊戲", "速解魔方", topic
        ]
        category_id = "27"  # Education (教育)
    elif is_code:
        title = f"【2026必看】{topic}｜零基礎手把手全自動工作流實戰教學（附核心代碼）"
        if len(title) > 98:
            title = f"【2026實戰】{topic[:40]}｜全自動高質感教學（附核心代碼）"

        desc = (
            f"🔥 本集深度解析：{topic}\n\n"
            f"告別繁瑣手動剪輯！今天為大家全面展示這套全自動影音生產管線。\n"
            f"從自然語音生成、動態視覺排版、精準字幕對齊到高畫質渲染，完整拆解核心細節！\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⏱️ 影片章節導覽 (Timestamps)：\n"
            f"00:00 - 精彩開場與痛點分析\n"
            f"00:35 - 核心架構與底層原理拆解\n"
            f"01:20 - 零門檻實作：三步搞定全自動生成\n"
            f"02:40 - 實戰避坑指南與關鍵細節\n"
            f"03:30 - 總結與專案架構回顧\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💻 本集自動化核心 Python 實戰代碼：\n\n"
            f"# === AI YouTube 全自動影音生產核心管線 ===\n"
            f"import asyncio\n"
            f"from src.composer import compose_video\n\n"
            f"async def generate_my_video():\n"
            f"    # 一鍵自動化：Edge-TTS 語音合成 + 視覺卡片排版 + 字幕對齊 + 1080p 渲染\n"
            f"    video_path = await compose_video(\n"
            f"        topic=\"{topic}\",\n"
            f"        duration_minutes=13,\n"
            f"        aspect_ratio=\"16:9\",\n"
            f"        voice=\"zh-TW-YunJheNeural\"\n"
            f"    )\n"
            f"    print(f\"🎉 影片已成功生成: {{video_path}}\")\n\n"
            f"if __name__ == \"__main__\":\n"
            f"    asyncio.run(generate_my_video())\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🛠️ 終端機快速啟動指令：\n"
            f"1. 安裝依賴環境：\n"
            f"   pip install -r requirements.txt\n\n"
            f"2. 一鍵生成影片：\n"
            f"   python create_video.py --topic \"{topic}\" --duration 13\n\n"
            f"3. 啟動 Web UI 工作台：\n"
            f"   python web_ui.py\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔔 記得按讚、訂閱並開啟小鈴鐺，第一時間掌握最新 AI 自動化黑科技！\n"
            f"歡迎在留言區分享你的想法，我會親自回覆交流！\n\n"
            f"#AI生成影片 #YouTube自動化 #Python #EdgeTTS #FFmpeg #2026趨勢 #自媒體經營"
        )
        tags = [
            "AI生成影片", "YouTube自動化", "Python自動化", "Edge-TTS",
            "FFmpeg", "自媒體經營", "2026趨勢", "工作流", topic
        ]
        category_id = "28"  # Science & Technology
    else:
        title = f"【2026必看】{topic}｜高效實踐方法論與成長指南（附精華筆記與行動清單）"
        if len(title) > 98:
            title = f"【2026實戰】{topic[:40]}｜深度解析與實踐指南（附精華筆記）"

        desc = (
            f"🔥 本集深度解析：{topic}\n\n"
            f"你是否也常覺得在「{topic}」的過程中投入了大量心力，卻往往難以看見突破性的成長？\n"
            f"今天這部影片為大家完整拆解核心思維模型、底層運作機制與可持續落地的實踐閉環，幫你省下 80% 的摸索時間！\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⏱️ 影片章節導覽 (Timestamps)：\n"
            f"00:00 - 核心痛點分析與破局思維\n"
            f"00:35 - 底層邏輯與三大核心機制拆解\n"
            f"01:20 - 零門檻實踐：三步驟快速啟動行動系統\n"
            f"02:40 - 實戰避坑指南：新手常踩的 3 個思維盲區\n"
            f"03:30 - 本集精華總結與長期成長複利公式\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💡 本集核心精華筆記 (Key Takeaways)：\n\n"
            f"1. 認知升級：抓出核心關鍵槓桿點，不再被表面瑣碎的雜訊消耗精力。\n"
            f"2. 機制重於意志力：將目標拆解為微行動，並綁定到日常生活節奏中。\n"
            f"3. 成長複利：每天持續進步 1%，一年後將帶來 37 倍的巨大質變！\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🎯 快速實踐行動三步驟 (Action Steps)：\n\n"
            f"步驟一【盤點現狀】：明確列出當前卡關的最核心瓶頸，排除外部干擾。\n"
            f"步驟二【微量啟動】：設計一個 5 分鐘內即可開始的最小可行動作，降低阻力。\n"
            f"步驟三【固定覆盤】：每週保留 15 分鐘精煉覆盤，持續迭代個人行動系統。\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔔 記得按讚、訂閱並開啟小鈴鐺，持續掌握更多高價值乾貨與深度思考！\n"
            f"歡迎在留言區分享你的心得，我會親自回覆交流！\n\n"
            f"#{topic} #思維模型 #個人成長 #高效工作法 #方法論 #自媒體經營 #2026趨勢 #精華筆記"
        )
        tags = [
            topic, "思維模型", "個人成長", "高效工作法", "方法論",
            "自媒體經營", "2026趨勢", "精華筆記", "深度解析"
        ]
        category_id = "27"  # Education (教育/成長)

    return {
        "title": title,
        "description": desc,
        "tags": tags,
        "category_id": category_id,
        "privacy_status": "unlisted",  # 預設不公開，安全供主人預覽
        "is_programming": is_code
    }

def load_queue() -> List[Dict]:
    """載入發布審核佇列"""
    if os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_queue(queue_data: List[Dict]):
    """儲存發布審核佇列"""
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue_data, f, ensure_ascii=False, indent=2)

def sync_and_get_queue() -> List[Dict]:
    """
    同步 output_videos 資料夾內的影片並更新審核佇列：
    - 任何新產生的影片會自動排入佇列，並標記為 pending_review (待主人審核)
    - 保留已審核 (approved) 或已發布 (uploaded) 的歷史記錄
    """
    queue = load_queue()
    existing_filenames = {}
    for item in queue:
        fn = item.get("filename")
        if not fn and item.get("video_path"):
            fn = os.path.basename(item["video_path"])
            item["filename"] = fn
        if fn:
            existing_filenames[fn] = item

    mp4_files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "*.mp4")), key=os.path.getmtime, reverse=True)
    # 依主人指示：嚴格只收錄 16:9 橫向長影片 (全面排除任何 Shorts 與短預告)
    mp4_files = [
        f for f in mp4_files 
        if not os.path.basename(f).startswith("Shorts預告_") 
        and "shorts" not in os.path.basename(f).lower() 
        and "9x16" not in os.path.basename(f).lower()
    ]
    
    updated_queue = []
    found_filenames = set()

    for file_path in mp4_files:
        bname = os.path.basename(file_path)
        found_filenames.add(bname)
        size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)
        mtime = os.path.getmtime(file_path)
        is_shorts = False

        if bname in existing_filenames:
            # 保留現有狀態與自訂元數據
            item = existing_filenames[bname]
            item["size_mb"] = size_mb
            item["file_exists"] = True
            item["is_shorts"] = False
            updated_queue.append(item)
        else:
            # 新影片：自動生成 SEO 元數據並標記為待審核
            seo = generate_seo_metadata(bname)
            item = {
                "id": f"vid_{int(mtime)}_{len(updated_queue)}",
                "filename": bname,
                "video_path": os.path.relpath(file_path, PROJECT_ROOT),
                "is_shorts": is_shorts,
                "size_mb": size_mb,
                "mtime": mtime,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime)),
                "title": seo["title"],
                "description": seo["description"],
                "tags": seo["tags"],
                "category_id": seo["category_id"],
                "privacy_status": seo["privacy_status"],
                "status": "pending_review",  # 🟡 核心鐵律：預設永遠為待審核
                "approval_note": "等待主人審核與指示",
                "file_exists": True
            }
            updated_queue.append(item)

    save_queue(updated_queue)
    return updated_queue

def approve_video_for_upload(filename: str, updated_metadata: Optional[Dict] = None) -> Dict:
    """
    主人審核通過影片：標記為 approved，並保存最終確認的標題與說明文
    """
    queue = load_queue()
    target_item = None

    for item in queue:
        if item["filename"] == filename:
            item["status"] = "approved"
            item["approved_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            item["approval_note"] = "✅ 主人已親自審核通過，隨時可上傳發布"
            if updated_metadata:
                if "title" in updated_metadata and updated_metadata["title"]:
                    item["title"] = updated_metadata["title"]
                if "description" in updated_metadata and updated_metadata["description"]:
                    item["description"] = updated_metadata["description"]
                if "privacy_status" in updated_metadata:
                    item["privacy_status"] = updated_metadata["privacy_status"]
            target_item = item
            break

    if target_item:
        save_queue(queue)
        return {"success": True, "item": target_item}
    return {"success": False, "error": f"找不到佇列中的影片: {filename}"}

def reject_video(filename: str, reason: str = "主人退回修改") -> Dict:
    """
    主人退回影片
    """
    queue = load_queue()
    target_item = None

    for item in queue:
        if item["filename"] == filename:
            item["status"] = "rejected"
            item["approval_note"] = f"❌ 已退回：{reason}"
            target_item = item
            break

    if target_item:
        save_queue(queue)
        return {"success": True, "item": target_item}
    return {"success": False, "error": f"找不到佇列中的影片: {filename}"}
