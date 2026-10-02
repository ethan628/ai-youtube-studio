import os
import sys
import json
import glob
import threading
import urllib.parse
from datetime import datetime
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from src.composer import compose_video
from src.podcast_visualizer import convert_audio_to_podcast_video
from src.podcast_generator import generate_podcast_dialogue
from src.podcast_composer import generate_podcast_full
from create_video import PRESET_TEMPLATES, generate_video_from_template
from notebooklm_to_video import run_notebooklm_converter

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

PORT = 8501
OUTPUT_DIR = os.path.abspath("output_videos")
INPUT_DIR = os.path.abspath("inputs_notebooklm")
VOICE_SAMPLES_DIR = os.path.abspath("voice_samples")

# 全域生成狀態鎖
IS_GENERATING = False
CURRENT_STATUS = "閒置中"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI YouTube 影片全自動生成工作台</title>
    <style>
        :root {
            --bg: #0b0f19;
            --card-bg: #111827;
            --border: #1f2937;
            --cyan: #00f0ff;
            --purple: #a855f7;
            --text: #f3f4f6;
            --text-dim: #9ca3af;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Microsoft JhengHei", sans-serif; }
        body { background: var(--bg); color: var(--text); padding: 30px 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; border-bottom: 1px solid var(--border); padding-bottom: 20px; }
        .logo-title h1 { font-size: 26px; font-weight: 800; background: linear-gradient(90deg, var(--cyan), var(--purple)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .logo-title p { color: var(--text-dim); font-size: 14px; margin-top: 5px; }
        .btn-folder { background: #1e293b; color: var(--cyan); border: 1px solid var(--cyan); padding: 8px 16px; border-radius: 8px; cursor: pointer; text-decoration: none; font-size: 14px; font-weight: bold; }
        .btn-folder:hover { background: var(--cyan); color: #000; }
        
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 30px; }
        .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 14px; padding: 24px; }
        .card h2 { font-size: 18px; margin-bottom: 16px; display: flex; align-items: center; gap: 10px; color: var(--cyan); }
        
        .form-group { margin-bottom: 16px; }
        label { display: block; font-size: 14px; color: var(--text-dim); margin-bottom: 6px; }
        select, input[type="text"], textarea { width: 100%; background: #1e293b; border: 1px solid #334155; color: #fff; padding: 10px 12px; border-radius: 8px; font-size: 14px; }
        select:focus, input:focus, textarea:focus { border-color: var(--cyan); outline: none; }
        
        .btn-submit { width: 100%; background: linear-gradient(90deg, #0284c7, #9333ea); color: #fff; border: none; padding: 13px; border-radius: 8px; font-size: 15px; font-weight: bold; cursor: pointer; transition: 0.2s; }
        .btn-submit:hover:not(:disabled) { opacity: 0.9; transform: translateY(-1px); }
        .btn-submit:disabled { opacity: 0.5; cursor: not-allowed; }
        
        /* 載入進度提示卡 */
        #progressCard { display: none; background: #1e1b4b; border: 1px solid var(--purple); border-radius: 12px; padding: 16px 20px; margin-bottom: 24px; align-items: center; gap: 16px; }
        .spinner { width: 24px; height: 24px; border: 3px solid rgba(255,255,255,0.2); border-top-color: var(--cyan); border-radius: 50%; animation: spin 0.8s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        
        .gallery-section h2 { font-size: 20px; margin-bottom: 16px; color: #fff; display: flex; justify-content: space-between; align-items: center; }
        .video-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 20px; }
        .video-card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; padding: 12px; }
        video { width: 100%; border-radius: 8px; background: #000; max-height: 220px; }
        .video-info { margin-top: 10px; }
        .video-title { font-size: 14px; font-weight: bold; color: #fff; word-break: break-all; margin-bottom: 4px; }
        .video-meta { font-size: 12px; color: var(--text-dim); }

        .tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; background: #1e293b; color: var(--cyan); }
        .notice { font-size: 13px; line-height: 1.6; color: #94a3b8; background: #0f172a; padding: 12px; border-radius: 8px; border-left: 3px solid var(--purple); margin-bottom: 16px; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo-title">
                <h1>🎬 YouTube 影片全自動生成工作台</h1>
                <p>100% 完全免費 ⚡ Edge-TTS 自然語音 ⚡ 科技視覺動態卡片 ⚡ Google NotebookLM 一鍵轉影片</p>
            </div>
            <div>
                <button onclick="openFolder()" class="btn-folder">📂 開啟 output_videos 資料夾</button>
            </div>
        </header>

        <!-- 即時進度通知條 -->
        <div id="progressCard">
            <div class="spinner"></div>
            <div>
                <strong style="color:var(--cyan); font-size:15px;" id="statusTitle">影片生成進行中...</strong>
                <p style="color:#cbd5e1; font-size:13px; margin-top:4px;" id="statusDesc">正在調用 AI 進行配音合成、視覺畫面繪製與字幕對齊，預計需約 15~30 秒，請稍候！</p>
            </div>
        </div>

        <div class="grid">
            <!-- 模組 1: 一鍵 AI 影片生成 -->
            <div class="card">
                <h2>⚡ 模式一：一鍵生成 YouTube 影片</h2>
                <form id="presetForm" onsubmit="submitPreset(event)">
                    <div class="form-group">
                        <label>選擇預設模板（契合頻道爆款風格）：</label>
                        <select name="template" id="tplSelect">
                            <option value="1">【雙AI協同 EP5】不寫Python也能做！打造個人知識庫</option>
                            <option value="2">【2026最強工作流】手殘黨救星！全網數據自動抓</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>影片規格比例：</label>
                        <select name="aspect" id="aspectSelect">
                            <option value="16x9">16:9 橫向標準長影片 (YouTube 1080p 正片首選)</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>AI 配音角色 (微軟神經自然語音)：</label>
                        <select name="voice" id="voiceSelect">
                            <option value="zh-TW-YunJheNeural">台灣微軟男聲 (YunJhe - 穩重專業推薦)</option>
                            <option value="zh-TW-HsiaoChenNeural">台灣微軟女聲 (HsiaoChen - 清新自然)</option>
                        </select>
                    </div>
                    <button type="submit" id="btnPreset" class="btn-submit">🚀 開始全自動生成影片</button>
                </form>
            </div>

            <!-- 模組 2: Google NotebookLM 轉影片 -->
            <div class="card">
                <h2>🎙️ 模式二：Google NotebookLM 轉影片</h2>
                <div class="notice">
                    <strong>💡 使用方式：</strong><br>
                    1. 至 NotebookLM 生成雙主持 AI Podcast 語音並下載 (.m4a/.mp3)<br>
                    2. 放進 <code>inputs_notebooklm</code> 資料夾<br>
                    3. 在下方輸入主題標題，一鍵合成動態音波 1080p 影片！
                </div>
                <form id="notebookForm" onsubmit="submitNotebookLM(event)">
                    <div class="form-group">
                        <label>已偵測到 inputs_notebooklm 內的音訊：</label>
                        <select name="audio_file" id="audioSelect">
                            {{AUDIO_OPTIONS}}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>影片大標題：</label>
                        <input type="text" id="nbTitle" name="title" value="Google NotebookLM 深度對談" placeholder="輸入影片主題大標題">
                    </div>
                    <div class="form-group">
                        <label>影片副標題：</label>
                        <input type="text" id="nbSub" name="subtitle" value="AI 雙主講精華提煉 ⚡ 2026 最新洞察" placeholder="輸入副標題">
                    </div>
                    <button type="submit" id="btnNotebook" class="btn-submit" style="background: linear-gradient(90deg, #10b981, #06b6d4);">🎙️ 合成 NotebookLM Podcast 影片</button>
                </form>
            </div>
        </div>

        <!-- 產出影片展示庫 -->
        <div class="gallery-section">
            <h2>
                <span>📁 已生成影片庫（統一存於 output_videos 資料夾）</span>
                <span class="tag">共 {{VIDEO_COUNT}} 部影片</span>
            </h2>
            <div class="video-grid" id="videoGrid">
                {{VIDEO_CARDS}}
            </div>
        </div>
    </div>

    <script>
        function showLoading(title, desc) {
            document.getElementById("progressCard").style.display = "flex";
            document.getElementById("statusTitle").innerText = title;
            document.getElementById("statusDesc").innerText = desc;
            document.getElementById("btnPreset").disabled = true;
            document.getElementById("btnNotebook").disabled = true;
        }

        function hideLoading() {
            document.getElementById("progressCard").style.display = "none";
            document.getElementById("btnPreset").disabled = false;
            document.getElementById("btnNotebook").disabled = false;
        }

        async function submitPreset(e) {
            e.preventDefault();
            showLoading("⚡ 正在為您生成影片中...", "正在調用微軟 Edge-TTS 產生自然語音、繪製高質感卡片、精確對齊字幕... 約需 20~30 秒，完成後會自動更新！");
            
            try {
                const res = await fetch("/api/generate_preset", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({
                        template: document.getElementById("tplSelect").value,
                        aspect: document.getElementById("aspectSelect").value,
                        voice: document.getElementById("voiceSelect").value
                    })
                });
                const data = await res.json();
                if (data.success) {
                    alert("🎉 影片生成成功！已存入 output_videos 資料夾！");
                    window.location.reload();
                } else {
                    alert("❌ 生成失敗：" + (data.error || "未知錯誤"));
                }
            } catch (err) {
                alert("連線異常：" + err);
            } finally {
                hideLoading();
            }
        }

        async function submitNotebookLM(e) {
            e.preventDefault();
            const audio = document.getElementById("audioSelect").value;
            if (!audio) {
                alert("請先將 NotebookLM 音訊檔 (.m4a/.mp3) 放入 inputs_notebooklm 資料夾！");
                return;
            }
            showLoading("🎙️ 正在將音訊合成為 Podcast 影片...", "正在計算音頻動態聲波、繪製雙主播視覺卡片並生成 1080p 影片，請稍候...");
            try {
                const res = await fetch("/api/generate_notebooklm", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({
                        audio_file: audio,
                        title: document.getElementById("nbTitle").value,
                        subtitle: document.getElementById("nbSub").value
                    })
                });
                const data = await res.json();
                if (data.success) {
                    alert("🎉 NotebookLM 影片合成成功！已存入 output_videos 資料夾！");
                    window.location.reload();
                } else {
                    alert("❌ 合成失敗：" + (data.error || "未知錯誤"));
                }
            } catch (err) {
                alert("連線異常：" + err);
            } finally {
                hideLoading();
            }
        }

        function openFolder() {
            fetch("/api/open_folder");
        }
    </script>
</body>
</html>
"""

class VideoStudioHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/open_folder":
            if sys.platform.startswith("win"):
                os.startfile(OUTPUT_DIR)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        if parsed.path in ("/api/list_videos", "/list_videos"):
            mp4_files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "*.mp4")), key=os.path.getmtime, reverse=True)
            # 嚴格只收錄 16:9 橫向長片
            mp4_files = [f for f in mp4_files if not os.path.basename(f).startswith("Shorts預告_") and "shorts" not in os.path.basename(f).lower() and "9x16" not in os.path.basename(f).lower()]
            v_list = []
            for f in mp4_files:
                bname = os.path.basename(f)
                size_mb = os.path.getsize(f) / (1024 * 1024)
                v_list.append({
                    "filename": bname,
                    "size_mb": round(size_mb, 2),
                    "is_shorts": False,
                    "mtime": os.path.getmtime(f)
                })
            self.send_json_response({"success": True, "videos": v_list})
            return

        if parsed.path in ("/api/youtube_queue", "/youtube_queue"):
            from src.youtube_manager import sync_and_get_queue
            from src.youtube_uploader import check_youtube_api_readiness
            queue = sync_and_get_queue()
            api_status = check_youtube_api_readiness()
            self.send_json_response({"success": True, "queue": queue, "api_status": api_status})
            return

        if parsed.path in ("/api/list_recordings", "/list_recordings"):
            rec_files = sorted(glob.glob(os.path.join("output_recordings", "*.mp4")), key=os.path.getmtime, reverse=True)
            r_list = []
            for f in rec_files:
                bname = os.path.basename(f)
                size_mb = os.path.getsize(f) / (1024 * 1024)
                mtime = os.path.getmtime(f)
                mode_guess = "terminal"
                if "browser" in bname.lower(): mode_guess = "browser"
                elif "editor" in bname.lower(): mode_guess = "editor"
                elif "desktop" in bname.lower(): mode_guess = "desktop"
                r_list.append({
                    "filename": bname,
                    "size_mb": round(size_mb, 2),
                    "mtime": mtime,
                    "time_str": datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S"),
                    "mode": mode_guess
                })
            self.send_json_response({"success": True, "recordings": r_list})
            return

        if parsed.path in ("/api/list_voice_samples", "/list_voice_samples"):
            os.makedirs("voice_samples", exist_ok=True)
            samples = []
            for ext in ["mp3", "wav", "m4a", "webm", "aac", "ogg"]:
                for p in glob.glob(os.path.join("voice_samples", f"*.{ext}")):
                    bname = os.path.basename(p)
                    size_kb = round(os.path.getsize(p) / 1024, 1)
                    samples.append({
                        "filename": bname,
                        "size_kb": size_kb,
                        "url": f"/voice_samples/{urllib.parse.quote(bname)}"
                    })
            self.send_json_response({"success": True, "samples": samples})
            return

        if parsed.path in ("/api/list_songs", "/list_songs"):
            from src.singing_composer import PRESET_SONGS
            songs_list = []
            for sid, sinfo in PRESET_SONGS.items():
                songs_list.append({
                    "id": sid,
                    "name": sinfo["name"],
                    "genre": sinfo["genre"],
                    "description": sinfo["description"],
                    "default_lyrics": "\n".join(l["text"] for l in sinfo["lyrics_lines"])
                })
            self.send_json_response({"success": True, "songs": songs_list})
            return

        if parsed.path.startswith("/voice_samples/"):
            filename = urllib.parse.unquote(parsed.path[15:])
            filepath = os.path.join("voice_samples", filename)
            self.send_file_with_range(filepath)
            return

        if parsed.path.startswith("/recordings/"):
            filename = urllib.parse.unquote(parsed.path[12:])
            filepath = os.path.join("output_recordings", filename)
            self.send_file_with_range(filepath)
            return

        if parsed.path.startswith("/videos/"):
            filename = urllib.parse.unquote(parsed.path[8:])
            filepath = os.path.join(OUTPUT_DIR, filename)
            self.send_file_with_range(filepath)
            return

        if parsed.path.startswith("/output_videos/"):
            filename = urllib.parse.unquote(parsed.path[15:])
            filepath = os.path.join(OUTPUT_DIR, filename)
            self.send_file_with_range(filepath)
            return

        if parsed.path in ("/", "/index.html"):
            target_html = "工作台.html" if os.path.exists("工作台.html") else ("index.html" if os.path.exists("index.html") else None)
            if target_html:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                with open(target_html, "rb") as f:
                    self.wfile.write(f.read())
                return
            self.render_dashboard()
            return

        super().do_GET()

    def render_dashboard(self):
        mp4_files = sorted(glob.glob(os.path.join(OUTPUT_DIR, "*.mp4")), key=os.path.getmtime, reverse=True)
        # 嚴格只收錄 16:9 橫向長片
        mp4_files = [f for f in mp4_files if not os.path.basename(f).startswith("Shorts預告_") and "shorts" not in os.path.basename(f).lower() and "9x16" not in os.path.basename(f).lower()]
        video_cards_html = ""
        for v in mp4_files:
            bname = os.path.basename(v)
            size_mb = os.path.getsize(v) / (1024 * 1024)
            url_name = urllib.parse.quote(bname)
            video_cards_html += f"""
            <div class="video-card">
                <video controls preload="metadata">
                    <source src="/videos/{url_name}" type="video/mp4">
                    您的瀏覽器不支援影片播放。
                </video>
                <div class="video-info">
                    <div class="video-title">{bname}</div>
                    <div class="video-meta">大小：{size_mb:.2f} MB | <a href="/videos/{url_name}" download style="color:var(--cyan);text-decoration:none;">📥 下載檔案</a></div>
                </div>
            </div>
            """
        if not video_cards_html:
            video_cards_html = "<p style='color:#64748b;'>目前 output_videos 中尚無影片，請使用上方功能生成！</p>"

        audio_files = []
        for ext in ["m4a", "mp3", "wav", "aac"]:
            audio_files.extend(glob.glob(os.path.join(INPUT_DIR, f"*.{ext}")))
        
        audio_options_html = ""
        if audio_files:
            for a in audio_files:
                abname = os.path.basename(a)
                audio_options_html += f'<option value="{abname}">{abname}</option>'
        else:
            audio_options_html = '<option value="">(尚未偵測到音訊，請將檔案放入 inputs_notebooklm)</option>'

        content = HTML_TEMPLATE.replace("{{VIDEO_COUNT}}", str(len(mp4_files)))
        content = content.replace("{{VIDEO_CARDS}}", video_cards_html)
        content = content.replace("{{AUDIO_OPTIONS}}", audio_options_html)

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        
        # 支援 JSON 請求與 Form 請求
        data = {}
        if self.headers.get("Content-Type", "").startswith("application/json"):
            try:
                data = json.loads(body)
            except Exception:
                pass
        else:
            parsed_form = urllib.parse.parse_qs(body)
            for k, v in parsed_form.items():
                data[k] = v[0] if v else ""

        if self.path in ("/api/upload_voice_sample", "/upload_voice_sample"):
            # 支援從網頁端直接上傳錄製的個人語音樣本
            os.makedirs("voice_samples", exist_ok=True)
            ct = self.headers.get("Content-Type", "")
            save_path = os.path.join("voice_samples", "my_voice.webm")
            
            if "application/json" in ct:
                import base64
                b64_data = data.get("audio_base64", "")
                if "," in b64_data:
                    b64_data = b64_data.split(",", 1)[1]
                audio_bytes = base64.b64decode(b64_data)
                filename = data.get("filename", "my_voice.webm")
                save_path = os.path.join("voice_samples", filename)
                with open(save_path, "wb") as f:
                    f.write(audio_bytes)
            else:
                # 原始二進位
                self.rfile.seek(0)
                # re-read raw bytes
                raw_bytes = body.encode("utf-8") if isinstance(body, str) else body
                with open(save_path, "wb") as f:
                    f.write(raw_bytes)
            
            self.send_json_response({"success": True, "path": save_path, "filename": os.path.basename(save_path)})
            return

        if self.path in ("/api/delete_video", "/delete_video"):
            filename = data.get("filename", "")
            if not filename:
                self.send_json_response({"success": False, "error": "未提供影片檔名"}, status=400)
                return
            safe_name = os.path.basename(filename)
            target = os.path.join(OUTPUT_DIR, safe_name)
            if os.path.exists(target) and os.path.isfile(target):
                try:
                    os.remove(target)
                    self.send_json_response({"success": True, "filename": safe_name})
                except Exception as e:
                    self.send_json_response({"success": False, "error": f"刪除失敗: {e}"}, status=500)
            else:
                self.send_json_response({"success": False, "error": "檔案不存在"}, status=404)
            return

        if self.path in ("/api/create_shorts_teaser", "/create_shorts_teaser"):
            from src.shorts_teaser import make_shorts_teaser
            filename = data.get("filename", "")
            if not filename:
                self.send_json_response({"success": False, "error": "未提供原始影片檔名"}, status=400)
                return
            duration = float(data.get("duration", 30.0))
            title = data.get("title", None)
            cta = data.get("cta", None)

            safe_name = os.path.basename(filename)
            input_path = os.path.join(OUTPUT_DIR, safe_name)
            if not os.path.exists(input_path):
                alt_path = os.path.join("output_recordings", safe_name)
                if os.path.exists(alt_path):
                    input_path = alt_path
                else:
                    self.send_json_response({"success": False, "error": f"找不到原始影片: {safe_name}"}, status=404)
                    return

            try:
                out_path = make_shorts_teaser(
                    input_video_path=input_path,
                    duration=duration,
                    teaser_title=title if title and title.strip() else None,
                    cta_text=cta if cta and cta.strip() else None
                )
                self.send_json_response({
                    "success": True,
                    "file": out_path,
                    "filename": os.path.basename(out_path)
                })
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_json_response({"success": False, "error": str(e)}, status=500)
            return

        if self.path in ("/api/youtube_approve", "/youtube_approve"):
            from src.youtube_manager import approve_video_for_upload
            filename = data.get("filename", "")
            title = data.get("title", None)
            description = data.get("description", None)
            privacy_status = data.get("privacy_status", None)
            meta = {}
            if title: meta["title"] = title
            if description: meta["description"] = description
            if privacy_status: meta["privacy_status"] = privacy_status
            res = approve_video_for_upload(filename, meta if meta else None)
            self.send_json_response(res)
            return

        if self.path in ("/api/youtube_reject", "/youtube_reject"):
            from src.youtube_manager import reject_video
            filename = data.get("filename", "")
            reason = data.get("reason", "主人退回修改")
            res = reject_video(filename, reason)
            self.send_json_response(res)
            return

        if self.path in ("/api/youtube_upload", "/youtube_upload"):
            from src.youtube_uploader import upload_approved_video
            filename = data.get("filename", "")
            res = upload_approved_video(filename)
            self.send_json_response(res)
            return

        if self.path in ("/api/youtube_auth_start", "/youtube_auth_start"):
            from src.youtube_uploader import start_auth_flow
            res = start_auth_flow()
            self.send_json_response(res)
            return

        if self.path in ("/api/open_output_folder", "/open_output_folder"):
            try:
                import subprocess
                subprocess.Popen(["xdg-open", OUTPUT_DIR])
                self.send_json_response({"success": True})
            except Exception as e:
                self.send_json_response({"success": False, "error": str(e)}, status=500)
            return

        if self.path in ("/api/save_client_secrets", "/save_client_secrets"):
            try:
                content = data.get("content", "")
                if isinstance(content, dict):
                    content = json.dumps(content, indent=2, ensure_ascii=False)
                if not content or ("installed" not in content and "web" not in content):
                    self.send_json_response({"success": False, "error": "無效的 Google OAuth Client Secrets JSON 內容"}, status=400)
                    return
                with open("client_secrets.json", "w", encoding="utf-8") as f:
                    f.write(content)
                from src.youtube_uploader import check_youtube_api_readiness
                status = check_youtube_api_readiness()
                self.send_json_response({"success": True, "api_status": status})
            except Exception as e:
                self.send_json_response({"success": False, "error": str(e)}, status=500)
            return

        if self.path in ("/api/generate_script", "/generate_script"):
            from src.script_generator import generate_script_by_ai
            topic = data.get("topic", "") or "2026 最新實戰工作流"
            duration = float(data.get("duration", 3.0))
            style = data.get("style", "科技實戰")
            try:
                script = generate_script_by_ai(topic=topic, duration_minutes=duration, style=style)
                self.send_json_response({
                    "success": True,
                    "script": script,
                    "scenes": script.get("scenes", []),
                    "is_programming": script.get("is_programming", False)
                })
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_json_response({"success": False, "error": str(e)}, status=500)
            return

        if self.path in ("/api/generate_next_script", "/generate_next_script"):
            from src.script_generator import generate_next_episode_script
            current_topic = data.get("current_topic", "") or data.get("topic", "2026 最新實戰工作流")
            duration = float(data.get("duration", 3.0))
            style = data.get("style", "科技實戰")
            chosen_topic = data.get("chosen_topic", None)
            try:
                next_script = generate_next_episode_script(
                    current_topic=current_topic,
                    duration_minutes=duration,
                    style=style,
                    chosen_topic=chosen_topic
                )
                self.send_json_response({
                    "success": True,
                    "script": next_script,
                    "next_topic": next_script.get("title", ""),
                    "scenes": next_script.get("scenes", [])
                })
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_json_response({"success": False, "error": str(e)}, status=500)
            return

        if self.path in ("/api/predict_next_episode", "/predict_next_episode"):
            from src.script_generator import predict_next_episode
            current_topic = data.get("current_topic", "") or data.get("topic", "2026 最新 AI 全自動實戰工作流")
            duration = float(data.get("duration", 3.0))
            style = data.get("style", "科技實戰")
            try:
                pred = predict_next_episode(current_topic=current_topic, duration_minutes=duration, style=style)
                self.send_json_response({"success": True, "prediction": pred})
            except Exception as e:
                self.send_json_response({"success": False, "error": str(e)}, status=500)
            return

        if self.path in ("/api/detect_autopilot_mode", "/detect_autopilot_mode"):
            from src.autopilot_detector import detect_mode_by_gemini
            script_text = data.get("text", "") or data.get("script", "")
            duration = float(data.get("duration", 15.0))
            try:
                res = detect_mode_by_gemini(script_text, duration=duration)
                self.send_json_response({"success": True, "data": res})
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_json_response({"success": False, "error": str(e)}, status=500)
            return

        if self.path in ("/api/run_autopilot_recording", "/run_autopilot_recording"):
            from src.auto_pilot_recorder import run_autopilot_recording
            mode = data.get("mode", "terminal")
            title = data.get("title", "AI 電腦無人操作自動錄影")
            duration = float(data.get("duration", 15.0))
            prompt = data.get("prompt", None)
            commands = data.get("commands", None)
            narration = data.get("narration", None)
            aspect = data.get("aspect", "16x9")
            speed = float(data.get("speed", 1.0))
            show_subtitles = bool(data.get("show_subtitles", True))
            enable_audio = bool(data.get("enable_audio", True))
            is_vertical = (aspect == "shorts")

            try:
                out_path = run_autopilot_recording(
                    mode=mode,
                    title=title,
                    duration=duration,
                    prompt=prompt,
                    commands=commands,
                    narration=narration,
                    is_vertical=is_vertical,
                    speed=speed,
                    show_subtitles=show_subtitles,
                    enable_audio=enable_audio
                )
                vtt_file = out_path.rsplit(".", 1)[0] + ".vtt"
                vtt_name = os.path.basename(vtt_file) if os.path.exists(vtt_file) else None
                self.send_json_response({
                    "success": True,
                    "file": out_path,
                    "filename": os.path.basename(out_path),
                    "vtt_filename": vtt_name
                })
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_json_response({"success": False, "error": str(e)}, status=500)
            return

        if self.path in ("/api/delete_recording", "/delete_recording"):
            filename = data.get("filename", "")
            if not filename:
                self.send_json_response({"success": False, "error": "未提供錄影檔名"}, status=400)
                return
            safe_name = os.path.basename(filename)
            target = os.path.join("output_recordings", safe_name)
            if os.path.exists(target) and os.path.isfile(target):
                try:
                    os.remove(target)
                    self.send_json_response({"success": True, "filename": safe_name})
                except Exception as e:
                    self.send_json_response({"success": False, "error": f"刪除失敗: {e}"}, status=500)
            else:
                self.send_json_response({"success": False, "error": "檔案不存在"}, status=404)
            return

        if self.path in ("/api/generate_custom", "/generate_custom"):
            from create_video import generate_custom_video
            topic = data.get("topic", "2026 最新 AI 實戰工作流")
            duration = float(data.get("duration", 3.0))
            aspect = data.get("aspect", "16x9")
            voice = data.get("voice", "zh-TW-YunJheNeural")
            scenes = data.get("scenes", None)
            is_vertical = (aspect == "shorts")

            try:
                out_path = generate_custom_video(topic=topic, duration_minutes=duration, is_vertical=is_vertical, voice=voice, custom_scenes=scenes)
                self.send_json_response({"success": True, "file": out_path})
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_json_response({"success": False, "error": str(e)}, status=500)
            return

        if self.path in ("/api/generate_preset", "/generate_preset"):
            template_id = data.get("template", "1")
            aspect = data.get("aspect", "16x9")
            voice = data.get("voice", "zh-TW-YunJheNeural")
            is_vertical = (aspect == "shorts")

            try:
                out_path = generate_video_from_template(template_id=template_id, is_vertical=is_vertical, voice=voice)
                self.send_json_response({"success": True, "file": out_path})
            except Exception as e:
                self.send_json_response({"success": False, "error": str(e)}, status=500)
            return

        if self.path in ("/api/generate_notebooklm", "/generate_notebooklm"):
            audio_name = data.get("audio_file", "")
            title = data.get("title", "Google NotebookLM 深度對談")
            subtitle = data.get("subtitle", "AI 雙主講精華提煉 ⚡ 2026 最新洞察")

            audio_path = os.path.join(INPUT_DIR, audio_name) if audio_name else None
            try:
                out_path = run_notebooklm_converter(audio_path, title, subtitle)
                if out_path:
                    self.send_json_response({"success": True, "file": out_path})
                else:
                    self.send_json_response({"success": False, "error": "找不到音訊檔案"}, status=400)
            except Exception as e:
                self.send_json_response({"success": False, "error": str(e)}, status=500)
            return

        if self.path in ("/api/generate_podcast_script", "/generate_podcast_script"):
            topic = data.get("topic", "2026 AI 自動化工作流革命")
            duration = float(data.get("duration", 3.0))
            style = data.get("style", "科技趨勢對談")
            api_key = data.get("api_key", None)
            try:
                meta = generate_podcast_dialogue(topic=topic, duration_minutes=duration, style=style, api_key=api_key)
                self.send_json_response({"success": True, "podcast": meta})
            except Exception as e:
                self.send_json_response({"success": False, "error": str(e)}, status=500)
            return

        if self.path in ("/api/render_podcast", "/render_podcast"):
            topic = data.get("topic", "2026 AI 自動化工作流革命")
            duration = float(data.get("duration", 3.0))
            style = data.get("style", "科技趨勢對談")
            dialogue = data.get("dialogue", None)
            api_key = data.get("api_key", None)
            try:
                result = generate_podcast_full(
                    topic=topic,
                    duration_minutes=duration,
                    style=style,
                    custom_dialogue=dialogue,
                    api_key=api_key
                )
                self.send_json_response(result)
            except Exception as e:
                self.send_json_response({"success": False, "error": str(e)}, status=500)
            return

        if self.path in ("/api/generate_singing", "/generate_singing"):
            from src.singing_composer import generate_singing_full
            song_id = data.get("song_id", "happy_birthday")
            lyrics = data.get("lyrics", None)
            voice_sample = data.get("voice_sample", None)
            style = data.get("style", "pop")
            reverb = data.get("reverb", "ktv")

            sample_path = None
            if voice_sample and voice_sample != "default":
                sample_path = os.path.join(VOICE_SAMPLES_DIR, voice_sample) if not os.path.isabs(voice_sample) else voice_sample

            try:
                result = generate_singing_full(
                    song_id=song_id,
                    custom_lyrics=lyrics,
                    sample_voice_path=sample_path,
                    style=style,
                    reverb_type=reverb
                )
                self.send_json_response(result)
            except Exception as e:
                self.send_json_response({"success": False, "error": str(e)}, status=500)
            return

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
    def send_file_with_range(self, filepath: str, content_type: str = None):
        """
        支援標準 HTTP 206 Partial Content 與 Accept-Ranges: bytes。
        支援 HTML5 影片與音訊進度條任意拖曳、快轉跳轉，絕不跳回開頭。
        """
        if not os.path.exists(filepath):
            self.send_error(404, "File not found")
            return

        file_size = os.path.getsize(filepath)
        if not content_type:
            lower = filepath.lower()
            if lower.endswith(".mp4"):
                content_type = "video/mp4"
            elif lower.endswith(".vtt"):
                content_type = "text/vtt; charset=utf-8"
            elif lower.endswith(".srt"):
                content_type = "text/plain; charset=utf-8"
            elif lower.endswith(".mp3"):
                content_type = "audio/mpeg"
            elif lower.endswith(".wav"):
                content_type = "audio/wav"
            elif lower.endswith(".webm"):
                content_type = "audio/webm"
            else:
                content_type = "application/octet-stream"

        range_header = self.headers.get("Range")
        if range_header and range_header.startswith("bytes="):
            try:
                parts = range_header[6:].split("-")
                start = int(parts[0]) if parts[0] else 0
                end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1
                if start >= file_size or start > end:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{file_size}")
                    self.end_headers()
                    return

                length = end - start + 1
                self.send_response(206)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(length))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                with open(filepath, "rb") as f:
                    f.seek(start)
                    bytes_left = length
                    while bytes_left > 0:
                        chunk_size = min(65536, bytes_left)
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        try:
                            self.wfile.write(chunk)
                        except (BrokenPipeError, ConnectionResetError):
                            return
                        bytes_left -= len(chunk)
                return
            except Exception:
                pass

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(file_size))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return

    def send_json_response(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

def start_server():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), VideoStudioHandler)
    print("=" * 60)
    print(f"🌟 AI YouTube 影片生成工作台 Web UI 已啟動！")
    print(f"👉 請在瀏覽器開啟：http://127.0.0.1:{PORT}")
    print("=" * 60)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n工作台已關閉。")

if __name__ == "__main__":
    start_server()
