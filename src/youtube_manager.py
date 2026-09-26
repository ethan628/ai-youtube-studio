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

def clean_title_from_filename(filename: str) -> str:
    """從檔名解析乾淨的主題名稱"""
    bname = os.path.basename(filename)
    clean = bname.replace(".mp4", "").replace("AI生成_", "").replace("Shorts預告_", "")
    parts = clean.split("_")
    return parts[0] if parts else clean

def generate_seo_metadata(filename: str, custom_topic: Optional[str] = None) -> Dict:
    """
    根據影片屬性自動生成高點擊率標題、完整結構化說明欄、時間軸與 SEO 標籤
    """
    topic = custom_topic or clean_title_from_filename(filename)
    is_shorts = "shorts" in filename.lower() or "9x16" in filename.lower()
    
    if is_shorts:
        title = f"🔥 {topic}！30秒帶你掌握核心黑科技 #Shorts"
        if len(title) > 95:
            title = f"🔥 {topic[:35]}... #Shorts"
            
        desc = (
            f"⚡ 30 秒快速了解【{topic}】精華重點！\n\n"
            f"👉 想看手把手完整 1080p 深度教學？\n"
            f"請至頻道主頁觀看完整正片與領取開源代碼！\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📌 關注頻道，解鎖更多 2026 最新 AI 全自動實戰工作流！\n"
            f"喜歡這支短片請按讚、分享並訂閱開啟小鈴鐺 🔔\n\n"
            f"#Shorts #AI工具 #自動化 #科技實戰 #YouTube營運 #{topic[:10].replace(' ', '')}"
        )
        tags = ["Shorts", "AI工具", "全自動", "科技新知", "實戰教學", topic]
    else:
        title = f"【2026必看】{topic}｜零基礎手把手全自動工作流實戰教學（附開源資源）"
        if len(title) > 98:
            title = f"【2026實戰】{topic[:40]}｜全自動高質感教學（附開源配置）"

        desc = (
            f"🔥 本集深度解析：{topic}\n\n"
            f"告別繁瑣手動剪輯！今天為大家全面展示這套全自動影音生產管線。\n"
            f"從自然語音生成、動態視覺排版、精準字幕對齊到一鍵短影音預告，完整拆解核心細節！\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"⏱️ 影片章節導覽 (Timestamps)：\n"
            f"00:00 - 精彩預告與痛點分析\n"
            f"00:35 - 核心架構與底層原理拆解\n"
            f"01:20 - 零門檻實作：三步搞定全自動生成\n"
            f"02:40 - 實戰避坑指南與關鍵細節\n"
            f"03:30 - 總結與專案開源配置分享\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💡 專案開源倉庫與範例配置：\n"
            f"👉 GitHub: https://github.com/ethan628/ai-youtube-studio\n\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔔 記得按讚、訂閱並開啟小鈴鐺，第一時間掌握最新 AI 自動化黑科技！\n"
            f"歡迎在留言區分享你的想法，我會親自回覆交流！\n\n"
            f"#AI生成影片 #YouTube自動化 #Python #EdgeTTS #FFmpeg #2026趨勢 #自媒體經營"
        )
        tags = [
            "AI生成影片", "YouTube自動化", "Python自動化", "Edge-TTS",
            "FFmpeg", "自媒體經營", "2026趨勢", "工作流", topic
        ]

    return {
        "title": title,
        "description": desc,
        "tags": tags,
        "category_id": "28",  # Science & Technology
        "privacy_status": "unlisted"  # 預設不公開，安全供主人預覽
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
    existing_filenames = {item["filename"]: item for item in queue}

    mp4_files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "*.mp4")), key=os.path.getmtime, reverse=True)
    
    updated_queue = []
    found_filenames = set()

    for file_path in mp4_files:
        bname = os.path.basename(file_path)
        found_filenames.add(bname)
        size_mb = round(os.path.getsize(file_path) / (1024 * 1024), 2)
        mtime = os.path.getmtime(file_path)
        is_shorts = "shorts" in bname.lower() or "9x16" in bname.lower()

        if bname in existing_filenames:
            # 保留現有狀態與自訂元數據
            item = existing_filenames[bname]
            item["size_mb"] = size_mb
            item["file_exists"] = True
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
