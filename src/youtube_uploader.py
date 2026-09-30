import os
import sys
import json
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
from typing import Dict, Optional

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.youtube_manager import load_queue, save_queue

CLIENT_SECRETS_FILE = os.path.join(PROJECT_ROOT, "client_secrets.json")
TOKEN_FILE = os.path.join(PROJECT_ROOT, "youtube_token.json")

# 清除代理變數，確保 Google OAuth 授權與 YouTube 上傳直連 Google 伺服器
for k in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'all_proxy', 'ALL_PROXY']:
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = "*"

CURRENT_AUTH_FLOW = None
AUTH_SERVER = None
AUTH_SERVER_LOCK = threading.Lock()
AUTH_PORT = 8502

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # 靜默日誌，避免干擾主伺服器輸出
        pass

    def do_GET(self):
        global CURRENT_AUTH_FLOW
        # 確保此線程環境無 proxy 干擾
        for k in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'all_proxy', 'ALL_PROXY']:
            os.environ.pop(k, None)
        os.environ["NO_PROXY"] = "*"

        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        if "code" in qs:
            code = qs["code"][0]
            try:
                if CURRENT_AUTH_FLOW:
                    auth_resp = f"https://localhost:{AUTH_PORT}{self.path}"
                    try:
                        CURRENT_AUTH_FLOW.fetch_token(authorization_response=auth_resp)
                    except Exception:
                        CURRENT_AUTH_FLOW.fetch_token(code=code)

                    creds = CURRENT_AUTH_FLOW.credentials
                    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                        f.write(creds.to_json())
                    
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    html = """
                    <!DOCTYPE html>
                    <html>
                    <head><meta charset="utf-8"><title>授權成功</title></head>
                    <body style="background:#090d16; color:#fff; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; display:flex; flex-direction:column; align-items:center; justify-content:center; height:85vh; margin:0;">
                        <div style="background:#0f172a; border:2px solid #10b981; border-radius:18px; padding:36px 40px; text-align:center; max-width:480px; box-shadow:0 0 35px rgba(16,185,129,0.35);">
                            <div style="font-size:52px; margin-bottom:14px;">🎉</div>
                            <h1 style="color:#10b981; margin:0 0 10px 0; font-size:22px; font-weight:800;">Google YouTube 授權成功！</h1>
                            <p style="color:#94a3b8; font-size:14px; line-height:1.6; margin-bottom:20px;">
                                頻道授權已成功綁定！系統正在背景為您全自動上傳影片。<br>
                                您可以關閉此視窗，回到 <strong>AI YouTube 影片生成工作台</strong> 查看上傳成果！
                            </p>
                            <button onclick="window.close()" style="background:#10b981; color:#000; font-weight:bold; border:none; padding:10px 24px; border-radius:8px; cursor:pointer; font-size:14px;">
                                關閉此視窗
                            </button>
                        </div>
                        <script>
                            setTimeout(() => { try { window.close(); } catch(e){} }, 4000);
                        </script>
                    </body>
                    </html>
                    """
                    self.wfile.write(html.encode("utf-8"))
                    return
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(f"<h3>授權交換失敗：{e}</h3>".encode("utf-8"))
                return
        elif "error" in qs:
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"<h3>Google OAuth 拒絕或取消：{qs.get('error')}</h3>".encode("utf-8"))
            return

        self.send_response(404)
        self.end_headers()

def start_auth_server_if_needed(port=AUTH_PORT):
    global AUTH_SERVER
    with AUTH_SERVER_LOCK:
        if AUTH_SERVER is None:
            try:
                server = HTTPServer(("0.0.0.0", port), OAuthCallbackHandler)
                AUTH_SERVER = server
                t = threading.Thread(target=server.serve_forever, daemon=True)
                t.start()
            except OSError:
                # 端口可能已被佔用或已在監聽中
                pass

def start_auth_flow(port=AUTH_PORT) -> Dict:
    global CURRENT_AUTH_FLOW
    from google_auth_oauthlib.flow import InstalledAppFlow

    if not os.path.exists(CLIENT_SECRETS_FILE):
        return {"success": False, "error": "找不到 client_secrets.json 檔案，請先匯入或建立憑證"}

    start_auth_server_if_needed(port=port)

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    CURRENT_AUTH_FLOW = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        SCOPES,
        redirect_uri=f"http://localhost:{port}/"
    )
    auth_url, _ = CURRENT_AUTH_FLOW.authorization_url(prompt="consent", access_type="offline")
    return {"success": True, "auth_url": auth_url}

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
        "ready": has_client_secrets and has_libraries and has_token
    }

def get_authenticated_service():
    """
    獲取 Google YouTube Data API v3 服務實例
    """
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_FILE, "w", encoding="utf-8") as token_f:
                token_f.write(creds.to_json())
        else:
            raise PermissionError("尚未完成 Google YouTube 帳號授權，請先進行授權！")

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

    # 首次授權引導：若尚未產生 youtube_token.json，自動啟動 Web 授權流程並回傳授權連結
    if not status_check["has_token"]:
        auth_res = start_auth_flow()
        if auth_res["success"]:
            return {
                "success": False,
                "need_auth": True,
                "auth_url": auth_res["auth_url"],
                "message": "首次使用需進行一次性 Google YouTube 授權綁定",
                "metadata": target_item
            }
        else:
            return {"success": False, "error": auth_res["error"]}

    # 已具備 Token，執行官方 API 斷點續傳
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

def update_video_metadata(video_id: str, title: Optional[str] = None, description: Optional[str] = None, tags: Optional[list] = None, category_id: str = "28") -> Dict:
    """
    透過 YouTube Data API 更新線上影片的元數據 (標題、說明欄、標籤等)
    """
    try:
        youtube = get_authenticated_service()
        body = {
            "id": video_id,
            "snippet": {
                "categoryId": category_id
            }
        }
        if title:
            body["snippet"]["title"] = title
        if description:
            body["snippet"]["description"] = description
        if tags is not None:
            body["snippet"]["tags"] = tags

        request = youtube.videos().update(
            part="snippet",
            body=body
        )
        response = request.execute()
        return {
            "success": True,
            "video_id": video_id,
            "title": response.get("snippet", {}).get("title"),
            "message": "線上影片資訊已成功更新！"
        }
    except Exception as e:
        return {"success": False, "error": f"更新 YouTube 影片資訊失敗：{str(e)}"}

