import os
import sys
import json
import time
from typing import Dict, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.youtube_manager import load_queue, save_queue

CLIENT_SECRETS_FILE = os.path.join(PROJECT_ROOT, "client_secrets.json")
TOKEN_FILE = os.path.join(PROJECT_ROOT, "youtube_token.json")

def check_youtube_api_readiness() -> Dict:
    """
    檢查系統 YouTube API 上傳環境是否就緒
    """
    has_client_secrets = os.path.exists(CLIENT_SECRETS_FILE)
    has_token = os.path.exists(TOKEN_FILE)
    
    try:
        import googleapiclient.discovery
        import google_auth_oauthlib.flow
        has_libraries = True
    except ImportError:
        has_libraries = False

    return {
        "has_client_secrets": has_client_secrets,
        "has_token": has_token,
        "has_libraries": has_libraries,
        "ready": has_client_secrets and has_libraries
    }

def get_authenticated_service():
    """
    獲取 Google YouTube Data API v3 服務實例
    """
    from googleapiclient.discovery import build
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRETS_FILE):
                raise FileNotFoundError(
                    f"找不到 Google OAuth 客戶端憑證：{CLIENT_SECRETS_FILE}。\n"
                    "請至 Google Cloud Console 建立 OAuth 2.0 Client ID，並將 JSON 下載重命名為 client_secrets.json 放進專案根目錄。"
                )
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w", encoding="utf-8") as token_f:
            token_f.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)

def upload_approved_video(filename: str) -> Dict:
    """
    【嚴格審核鐵律】只有在佇列中被主人標記為 'approved' 的影片才能被上傳！
    """
    queue = load_queue()
    target_item = next((item for item in queue if item["filename"] == filename), None)

    if not target_item:
        return {"success": False, "error": f"影片未在發布佇列中：{filename}"}

    if target_item.get("status") != "approved":
        return {
            "success": False,
            "error": "【防呆安全攔截】此影片尚未經由主人親自審核通過！必須先點擊「審核通過」才能執行上傳！"
        }

    status_check = check_youtube_api_readiness()
    if not status_check["has_libraries"]:
        return {
            "success": False,
            "error": "尚未安裝 Google API 套件。請執行：.venv/bin/pip install google-api-python-client google-auth-oauthlib google-auth-httplib2",
            "manual_ready": True,
            "metadata": target_item
        }

    if not status_check["has_client_secrets"]:
        return {
            "success": False,
            "error": "尚未偵測到 client_secrets.json 憑證檔。您可以直接在 YouTube Studio 手動上傳（工作台已為您準備好完整 SEO 標題與說明文案）！",
            "manual_ready": True,
            "metadata": target_item
        }

    # 執行官方 API 斷點續傳
    try:
        from googleapiclient.http import MediaFileUpload
        youtube = get_authenticated_service()
        
        file_path = os.path.join(PROJECT_ROOT, "output_videos", filename)
        body = {
            "snippet": {
                "title": target_item["title"],
                "description": target_item["description"],
                "tags": target_item.get("tags", []),
                "categoryId": target_item.get("category_id", "28")
            },
            "status": {
                "privacyStatus": target_item.get("privacy_status", "unlisted"),
                "selfDeclaredMadeForKids": False
            }
        }

        media = MediaFileUpload(file_path, chunksize=1024*1024*2, resumable=True)
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"上傳進度：{int(status.progress() * 100)}%")

        video_id = response.get("id")
        target_item["status"] = "uploaded"
        target_item["uploaded_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        target_item["youtube_video_id"] = video_id
        target_item["youtube_url"] = f"https://youtu.be/{video_id}"
        save_queue(queue)

        return {
            "success": True,
            "video_id": video_id,
            "url": f"https://youtu.be/{video_id}",
            "message": f"🎉 影片已成功上傳至 YouTube（狀態：{target_item.get('privacy_status')}）！"
        }

    except Exception as e:
        return {"success": False, "error": f"YouTube 上傳過程中斷：{str(e)}"}
