import os
import sys
import time
import random
import tempfile
import subprocess
from datetime import datetime

# 確保 DISPLAY 與 XAUTHORITY 存在
if "DISPLAY" not in os.environ:
    os.environ["DISPLAY"] = ":0"
if "XAUTHORITY" not in os.environ:
    for cand in [
        os.path.expanduser("~/.Xauthority"),
        f"/run/user/{os.getuid()}/.mutter-Xwaylandauth.*"
    ]:
        if os.path.exists(cand):
            os.environ["XAUTHORITY"] = cand
            break

def _human_type(text: str, min_delay: float = 0.03, max_delay: float = 0.08):
    """模擬真人打字手速，帶有自然隨機延遲"""
    try:
        import pyautogui
        for char in text:
            pyautogui.write(char)
            time.sleep(random.uniform(min_delay, max_delay))
    except Exception as e:
        print(f"⚠️ 打字模擬異常: {e}")

# -------------------------------------------------------------
# 模式一：終端機全自動操作 (Terminal Auto-Pilot)
# -------------------------------------------------------------
def execute_terminal_mode(commands: list = None, title: str = "AI 終端自動化操作", duration: float = 8.0) -> dict:
    """
    用 subprocess 開啟終端機，依照腳本逐行模擬打字 (pyautogui.typewrite 加隨機延遲) 並執行，
    同步記錄每一步的時間戳。
    """
    if not commands:
        commands = [
            "git clone https://github.com/ethan628/ai-youtube-studio.git",
            "cd ai-youtube-studio",
            "python create_video.py --topic '2026最強AI實戰' --duration 3"
        ]

    steps_log = []
    terminal_proc = None

    # 尋找可用之 Linux 終端機模擬器
    term_bin = None
    for cand in ["/usr/bin/ptyxis", "/usr/bin/x-terminal-emulator", "/usr/bin/gnome-terminal", "/usr/bin/xterm"]:
        if os.path.exists(cand):
            term_bin = cand
            break

    start_time = time.time()
    try:
        if term_bin:
            env = os.environ.copy()
            terminal_proc = subprocess.Popen([term_bin], env=env)
            time.sleep(1.5) # 等待終端機視窗開啟並獲取焦點
        
        import pyautogui

        for idx, cmd in enumerate(commands):
            step_start = time.time()
            ts_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            steps_log.append({
                "step": idx + 1,
                "command": cmd,
                "timestamp": ts_str,
                "status": "typing"
            })
            print(f"[{ts_str}] 🤖 模擬敲入指令 ({idx+1}/{len(commands)}): {cmd}")

            # 模擬真人手速逐字打入
            _human_type(cmd, min_delay=0.03, max_delay=0.07)
            time.sleep(random.uniform(0.15, 0.3))
            
            # 按下 Enter 鍵執行
            pyautogui.press("enter")
            steps_log[-1]["status"] = "executed"

            # 間隔隨機等待，讓執行輸出有時間在螢幕展示
            time.sleep(random.uniform(1.2, 2.0))

        # 等待剩餘錄製時長
        elapsed = time.time() - start_time
        if elapsed < duration:
            time.sleep(duration - elapsed)

    except Exception as e:
        print(f"⚠️ 終端機操作執行異常: {e}")
    finally:
        if terminal_proc:
            try:
                terminal_proc.terminate()
                terminal_proc.wait(timeout=2)
            except Exception:
                pass

    return {
        "mode": "terminal",
        "title": title,
        "commands_executed": len(commands),
        "steps": steps_log,
        "duration": round(time.time() - start_time, 2)
    }

# -------------------------------------------------------------
# 模式二：網頁與 AI 工具操作 (Web & AI Tools Auto-Pilot)
# -------------------------------------------------------------
def execute_web_ai_mode(prompt: str = None, target_url: str = None, duration: float = 8.0) -> dict:
    """
    用 Playwright 開啟瀏覽器，模擬輸入提示詞、點擊送出、等待並擷取 AI 回應顯示在畫面上。
    """
    if not prompt:
        prompt = "請幫我規劃一套完全不用人操作的 YouTube 影片自動生成工作流"

    start_time = time.time()
    steps_log = []

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            # 啟動非無頭瀏覽器，使螢幕錄影能真實捕捉視窗
            browser = p.chromium.launch(
                headless=False,
                args=["--start-maximized", "--no-sandbox", "--disable-infobars"]
            )
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()

            # 產生高質感現代 AI 對話介面 HTML 檔案
            html_content = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>AI Studio · Intelligent Agent</title>
<style>
  body {{
    margin: 0; padding: 0; background: #0f172a; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    display: flex; flex-direction: column; height: 100vh;
  }}
  .header {{
    background: #1e293b; border-bottom: 1px solid #334155; padding: 14px 24px; display: flex; align-items: center; justify-content: space-between;
  }}
  .brand {{ font-size: 18px; font-weight: 700; color: #38bdf8; display: flex; align-items: center; gap: 8px; }}
  .chat-box {{
    flex: 1; overflow-y: auto; padding: 24px; max-width: 900px; margin: 0 auto; width: 100%; box-sizing: border-box;
  }}
  .msg {{ margin-bottom: 20px; line-height: 1.6; font-size: 15px; }}
  .msg-user {{
    background: #1e293b; border: 1px solid #475569; padding: 14px 18px; border-radius: 12px; margin-left: auto; max-width: 80%;
  }}
  .msg-ai {{
    background: rgba(30,41,59,0.7); border: 1px solid #38bdf8; padding: 18px 22px; border-radius: 12px;
  }}
  .input-area {{
    background: #1e293b; border-top: 1px solid #334155; padding: 16px 24px; display: flex; justify-content: center;
  }}
  .input-wrapper {{
    max-width: 900px; width: 100%; display: flex; gap: 10px;
  }}
  #prompt-input {{
    flex: 1; background: #0f172a; border: 1px solid #475569; border-radius: 8px; padding: 12px 16px; color: #fff; font-size: 14px; outline: none;
  }}
  #btn-send {{
    background: #0284c7; border: none; border-radius: 8px; color: #fff; padding: 0 24px; font-weight: bold; cursor: pointer; font-size: 14px;
  }}
  .cursor {{ display: inline-block; width: 8px; height: 16px; background: #38bdf8; animation: blink 1s infinite; margin-left: 2px; }}
  @keyframes blink {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0; }} }}
</style>
</head>
<body>
<div class="header">
  <div class="brand"><span>🤖</span> AI Workflow Agent · 智慧對話助理</div>
  <div style="font-size: 13px; color: #94a3b8;">模型: Gemini-1.5-Pro / DeepSeek-V3</div>
</div>
<div class="chat-box" id="chat">
  <div class="msg msg-ai">
    <strong>Agent:</strong> 您好！我是全自動無人化操作助理。請在下方輸入您想執行的任務或提示詞，我將即時為您拆解工作流並自動化產出！
  </div>
</div>
<div class="input-area">
  <div class="input-wrapper">
    <input type="text" id="prompt-input" placeholder="輸入提示詞或提問..." autocomplete="off">
    <button id="btn-send">送出提問 ➔</button>
  </div>
</div>
<script>
  window.receiveAIResponse = function(text) {{
    const chat = document.getElementById('chat');
    const msg = document.createElement('div');
    msg.className = 'msg msg-ai';
    msg.innerHTML = '<strong>Agent:</strong> <span id="ai-stream"></span><span class="cursor" id="cursor"></span>';
    chat.appendChild(msg);
    let i = 0;
    const streamSpan = document.getElementById('ai-stream');
    const timer = setInterval(() => {{
      if (i < text.length) {{
        streamSpan.innerHTML += text.charAt(i) === '\\n' ? '<br>' : text.charAt(i);
        i++;
        chat.scrollTop = chat.scrollHeight;
      }} else {{
        clearInterval(timer);
        document.getElementById('cursor').remove();
      }}
    }}, 45);
  }};
</script>
</body>
</html>"""

            temp_html = tempfile.mktemp(suffix=".html")
            with open(temp_html, "w", encoding="utf-8") as f:
                f.write(html_content)

            page.goto(f"file://{temp_html}")
            time.sleep(1.0)

            # 步驟 1：點擊輸入框
            page.click("#prompt-input")
            time.sleep(0.5)

            # 步驟 2：模擬真人手速打入提示詞
            steps_log.append({"step": 1, "action": "type_prompt", "prompt": prompt})
            page.type("#prompt-input", prompt, delay=random.randint(40, 75))
            time.sleep(0.5)

            # 步驟 3：點擊送出按鈕
            steps_log.append({"step": 2, "action": "click_send"})
            page.click("#btn-send")

            # 步驟 4：在畫面上顯示使用者的問題
            page.evaluate(f"""() => {{
                const chat = document.getElementById('chat');
                const userMsg = document.createElement('div');
                userMsg.className = 'msg msg-user';
                userMsg.innerHTML = '<strong>User:</strong> ' + {json.dumps(prompt)};
                chat.appendChild(userMsg);
                document.getElementById('prompt-input').value = '';
                chat.scrollTop = chat.scrollHeight;
            }}""")
            time.sleep(0.8)

            # 步驟 5：AI 串流生成回應展示
            ai_reply = f"已為您啟動「{prompt[:18]}」全自動架構：\n1. 自動拉取最新熱門題材與演算法權重\n2. 呼叫大模型解析分鏡與口播逐字稿\n3. 依節奏渲染 1080p 超高清無人長片視覺\n4. 封裝母帶級自然語音並自動加入審核佇列！"
            steps_log.append({"step": 3, "action": "ai_stream_response"})
            page.evaluate(f"window.receiveAIResponse({json.dumps(ai_reply)})")

            # 等待剩餘錄製時長
            elapsed = time.time() - start_time
            if elapsed < duration:
                time.sleep(duration - elapsed)

            browser.close()
            try:
                os.remove(temp_html)
            except Exception:
                pass

    except Exception as e:
        print(f"⚠️ Playwright 網頁操作異常: {e}")

    return {
        "mode": "browser",
        "prompt": prompt,
        "steps": steps_log,
        "duration": round(time.time() - start_time, 2)
    }

# -------------------------------------------------------------
# 模式三：代碼編輯與自動編譯 (Code Editor Auto-Pilot)
# -------------------------------------------------------------
def execute_code_editor_mode(code_lines: list = None, filename: str = "auto_pilot.py", duration: float = 8.0) -> dict:
    """
    用 pyautogui 模擬在代碼編輯器中打字、Ctrl+S 存檔、觸發 Run。
    """
    if not code_lines:
        code_lines = [
            "from src.script_generator import generate_script_by_ai",
            "",
            "# 自動生成專業分鏡腳本",
            "script = generate_script_by_ai('2026最新AI生片')",
            "print(f'[AI Studio] 成功規劃 {len(script[\"scenes\"])} 幕分鏡')",
            "print('[SUCCESS] 代碼編譯執行完畢，管線啟動成功！')"
        ]

    start_time = time.time()
    steps_log = []
    editor_proc = None

    # 尋找可用之編輯器 (優先 gnome-text-editor 或 code)
    editor_bin = None
    for cand in ["/usr/bin/gnome-text-editor", "/usr/bin/gedit", "/usr/bin/code"]:
        if os.path.exists(cand):
            editor_bin = cand
            break

    try:
        temp_file = os.path.join(tempfile.gettempdir(), filename)
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write("# === AI 自動編程示範 ===\n\n")

        if editor_bin:
            env = os.environ.copy()
            editor_proc = subprocess.Popen([editor_bin, temp_file], env=env)
            time.sleep(1.8) # 等待編輯器完全開啟並獲取焦點

        import pyautogui

        # 模擬逐行打入代碼
        for idx, line in enumerate(code_lines):
            step_ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            steps_log.append({"step": idx + 1, "code": line, "timestamp": step_ts})
            _human_type(line, min_delay=0.02, max_delay=0.06)
            pyautogui.press("enter")
            time.sleep(random.uniform(0.1, 0.3))

        # 存檔：Ctrl + S
        time.sleep(0.5)
        steps_log.append({"step": len(code_lines) + 1, "action": "save_file", "hotkey": "ctrl+s"})
        pyautogui.hotkey("ctrl", "s")
        time.sleep(0.8)

        # 觸發執行：模擬快捷鍵或開啟終端執行
        steps_log.append({"step": len(code_lines) + 2, "action": "trigger_run", "hotkey": "f5"})
        pyautogui.press("f5")

        # 等待剩餘錄製時長
        elapsed = time.time() - start_time
        if elapsed < duration:
            time.sleep(duration - elapsed)

    except Exception as e:
        print(f"⚠️ 代碼編輯操作異常: {e}")
    finally:
        if editor_proc:
            try:
                editor_proc.terminate()
                editor_proc.wait(timeout=2)
            except Exception:
                pass

    return {
        "mode": "editor",
        "file": filename,
        "steps": steps_log,
        "duration": round(time.time() - start_time, 2)
    }

# -------------------------------------------------------------
# 模式四：系統螢幕即時錄影 (Pure Screen Recording)
# -------------------------------------------------------------
def execute_pure_record_mode(duration: float = 8.0) -> dict:
    """
    純錄製，不做任何自動操作，等待設定的錄製時長。
    """
    start_time = time.time()
    steps_log = [{"timestamp": datetime.now().strftime("%H:%M:%S"), "action": "start_pure_recording"}]
    
    # 睡眠直到時間到達
    time.sleep(max(1.0, duration))
    
    steps_log.append({"timestamp": datetime.now().strftime("%H:%M:%S"), "action": "stop_pure_recording"})

    return {
        "mode": "desktop",
        "steps": steps_log,
        "duration": round(time.time() - start_time, 2)
    }
