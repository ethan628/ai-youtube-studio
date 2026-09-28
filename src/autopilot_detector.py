import os
import sys
import re
import json
import urllib.request
import urllib.parse

def detect_mode_by_gemini(script_text: str, duration: float = 15.0, api_key: str = None) -> dict:
    """
    呼叫 Gemini API 分析使用者貼上的口播稿、步驟或學習主題（如：學習python），
    智慧判斷最適合的無人電腦操作模式，並自動生成結構化「學習教學腳本」(Learning Script)。
    若無 API Key 或調用失敗，自動由本地智能課程引擎即時生成。
    """
    if not script_text or not script_text.strip():
        script_text = "學習 Python"

    gemini_key = api_key or os.environ.get("GEMINI_API_KEY")
    
    # 嘗試呼叫 Gemini API
    if gemini_key:
        try:
            try:
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                prompt = _build_classification_prompt(script_text, duration)
                response = model.generate_content(prompt)
                res_text = response.text.strip()
                parsed = _clean_and_parse_json(res_text)
                if parsed and "mode" in parsed:
                    return _normalize_detector_result(parsed, script_text, duration)
            except Exception as e_pkg:
                res = _call_gemini_http(script_text, duration, gemini_key)
                if res and "mode" in res:
                    return _normalize_detector_result(res, script_text, duration)
        except Exception as e:
            print(f"⚠️ Gemini API 分析異常 ({e})，切換至本地智能課程引擎")

    # 本地啟發式課程生成引擎 (Fallback)
    return heuristic_mode_detector(script_text, duration)

def _build_classification_prompt(script_text: str, duration: float) -> str:
    return f"""你是一個頂級 AI YouTube 科技教學架構師與無人操作規劃器。
請分析使用者的口播稿、操作步驟或學習主題（例如「學習python」），判斷最適合以下四種「無人電腦操作」的哪一種模式：
1. terminal (終端機全自動操作)：命令列執行、Python、Git、Docker、套件安裝、環境設定等。
2. browser (網頁與AI工具操作)：AI 對話 (如 ChatGPT、DeepSeek)、網頁搜尋、Web UI 互動等。
3. editor (代碼編輯與自動編譯)：VS Code 撰寫程式碼、存檔、運行編譯等。
4. desktop (系統螢幕即時錄影)：純螢幕錄影、桌面操作、跨軟體展示。

使用者文字：
\"\"\"{script_text}\"\"\"

目標影片時長：{int(duration)} 秒。

請生成專業結構化的繁體中文「學習教學腳本」，以「純 JSON」格式輸出，不要包裹 markdown 代碼塊，格式如下：
{{
  "mode": "terminal" | "browser" | "editor" | "desktop",
  "mode_name": "對應繁體中文模式名稱",
  "confidence": 95,
  "reason": "繁體中文理由（約30~50字）",
  "title": "示範影片標題（例如：Python 基礎入門與實戰）",
  "summary": "一句話總結本學習腳本內容與教學核心",
  "steps": [
    {{
      "step": 1,
      "title": "步驟標題（例如：驗證 Python 3 環境）",
      "cmd": "執行的單行指令或代碼（例如：python3 --version）",
      "logs": ["預期的終端機輸出日誌第1行", "預期的輸出日誌第2行"],
      "narration": "該步驟的口播解說詞（約20~40字）"
    }},
    {{
      "step": 2,
      "title": "步驟標題（例如：執行第一行互動代碼）",
      "cmd": "python3 -c \\"print('Hello, Python!')\\"",
      "logs": ["Hello, Python!", "[OK] 執行成功"],
      "narration": "口播解說詞"
    }},
    {{
      "step": 3,
      "title": "步驟標題（例如：撰寫結構化實戰腳本）",
      "cmd": "cat > main.py << 'EOF'\\nprint('AI 實戰')\\nEOF",
      "logs": ["[OK] 檔案建立完成"],
      "narration": "口播解說詞"
    }},
    {{
      "step": 4,
      "title": "步驟標題（例如：運行腳本並驗收成果）",
      "cmd": "python3 main.py",
      "logs": ["AI 實戰", "[OK] 恭喜！學習腳本 100% 執行成功！"],
      "narration": "口播解說詞"
    }}
  ],
  "extracted_content": "可直接貼入終端機或編輯器的完整執行指令（多行以換行符分隔）",
  "narration": "整部影片的完整口播旁白總結"
}}"""

def _call_gemini_http(script_text: str, duration: float, api_key: str) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{
            "parts": [{"text": _build_classification_prompt(script_text, duration)}]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 800
        }
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=12) as response:
        res_data = json.loads(response.read().decode("utf-8"))
        raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
        return _clean_and_parse_json(raw_text)

def _clean_and_parse_json(raw: str) -> dict:
    clean = raw.strip()
    if clean.startswith("```json"):
        clean = clean[7:]
    elif clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]
    clean = clean.strip()
    return json.loads(clean)

def _normalize_detector_result(data: dict, script_text: str, duration: float) -> dict:
    mode_names = {
        "terminal": "💻 終端機全自動操作",
        "browser": "🌐 網頁與 AI 工具操作",
        "editor": "📝 代碼編輯與自動編譯",
        "desktop": "🖥️ 系統螢幕即時錄影"
    }
    mode = data.get("mode", "terminal").lower()
    if mode not in mode_names:
        mode = "terminal"
    
    title = data.get("title", "AI 學習操作實戰")
    steps = data.get("steps", [])
    if not steps:
        built_ls = build_tailored_learning_script(script_text, mode, title, duration)
        steps = built_ls["steps"]
        summary = built_ls["summary"]
    else:
        summary = data.get("summary", "本教學腳本引導新手掌握核心工作流與實戰技能。")

    return {
        "mode": mode,
        "mode_name": mode_names[mode],
        "confidence": int(data.get("confidence", 95)),
        "reason": data.get("reason", "根據語意特徵與操作關鍵詞推薦最適模式並規劃學習腳本"),
        "title": title,
        "extracted_content": data.get("extracted_content", "\n".join([s["cmd"] for s in steps if "cmd" in s])),
        "narration": data.get("narration", " ".join([s.get("narration", "") for s in steps])),
        "learning_script": {
            "title": title,
            "summary": summary,
            "duration": int(duration),
            "steps": steps
        }
    }

def heuristic_mode_detector(script_text: str, duration: float = 15.0) -> dict:
    """
    本地智慧啟發式語意分類器與課程生成引擎 (Heuristic Curriculum Generator)
    在無 API Key 時提供 100% 穩定、豐富生動的學習教學腳本與分步操作。
    """
    text = script_text or "學習 Python"
    lower = text.lower()
    
    scores = {"terminal": 0, "browser": 0, "editor": 0, "desktop": 0}
    reasons = {"terminal": [], "browser": [], "editor": [], "desktop": []}

    # 1. 終端機特徵
    terminal_kws = [
        ("git", "Git 版本控制", 30), ("clone", "程式庫 Clone", 25), ("pip", "Pip 套件管理", 30),
        ("python", "Python 執行指令", 35), ("npm", "NPM 套件指令", 25), ("docker", "容器指令", 30),
        ("bash", "Shell 腳本", 20), ("cd ", "目錄切換", 20), ("sudo", "系統管理指令", 20),
        ("install", "安裝指令", 15), ("指令", "命令列關鍵詞", 15), ("終端機", "終端操作", 30),
        ("學習", "課程學習實戰", 25), ("教學", "步驟教學示範", 25), ("$", "命令提示符", 20)
    ]
    for kw, label, pts in terminal_kws:
        if kw in lower:
            scores["terminal"] += pts
            if label not in reasons["terminal"]: reasons["terminal"].append(label)

    # 2. 網頁與 AI 提問特徵
    browser_kws = [
        ("http", "網頁連結", 30), ("www", "網頁網址", 30), ("瀏覽器", "瀏覽器操作", 35),
        ("chatgpt", "ChatGPT 對話", 35), ("claude", "Claude AI 互動", 35), ("deepseek", "DeepSeek 對話", 35),
        ("提示詞", "AI 提示詞輸入", 30), ("prompt", "Prompt 提問", 30), ("搜尋", "搜尋動作", 20),
        ("問 ai", "AI 提問", 25), ("回答", "AI 串流生成", 15)
    ]
    for kw, label, pts in browser_kws:
        if kw in lower:
            scores["browser"] += pts
            if label not in reasons["browser"]: reasons["browser"].append(label)

    # 3. 代碼編輯特徵
    editor_kws = [
        ("vs code", "VS Code 編輯器", 35), ("vscode", "VS Code 編輯器", 35), ("def ", "Python 函數定義", 30),
        ("class ", "類別宣告", 25), ("import ", "模組導入", 30), ("代碼", "程式碼撰寫", 25),
        ("寫程式", "程式開發", 25), ("存檔", "Ctrl+S 存檔", 25), ("編譯", "代碼編譯", 25)
    ]
    for kw, label, pts in editor_kws:
        if kw in lower:
            scores["editor"] += pts
            if label not in reasons["editor"]: reasons["editor"].append(label)

    # 4. 系統螢幕即時錄影特徵
    desktop_kws = [
        ("桌面", "桌面操作", 30), ("螢幕", "螢幕展示", 30), ("錄製", "全螢幕錄製", 25),
        ("視窗", "視窗切換", 20), ("軟體", "應用軟體操作", 20)
    ]
    for kw, label, pts in desktop_kws:
        if kw in lower:
            scores["desktop"] += pts
            if label not in reasons["desktop"]: reasons["desktop"].append(label)

    # 決定最佳模式
    best_mode = "terminal"
    max_score = scores["terminal"]
    for m in ["browser", "editor", "desktop"]:
        if scores[m] > max_score:
            max_score = scores[m]
            best_mode = m

    mode_names = {
        "terminal": "💻 終端機全自動操作",
        "browser": "🌐 網頁與 AI 工具操作",
        "editor": "📝 代碼編輯與自動編譯",
        "desktop": "🖥️ 系統螢幕即時錄影"
    }

    # 提煉乾淨標題
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    raw_first_line = lines[0] if lines else "AI 全自動操作實戰"
    clean_title = re.sub(r'^[0-9\.\-\:\#\*\s]+', '', raw_first_line)[:24] or "AI 自動化操作實戰"

    # 生成對應主題之學習腳本
    learning_script = build_tailored_learning_script(text, best_mode, clean_title, duration)
    title = learning_script["title"]
    reason = f"系統偵測到主題為「{clean_title}」，已自動為您規劃完整的【{title}】4 步學習教學腳本與終端機執行指令！"

    return {
        "mode": best_mode,
        "mode_name": mode_names[best_mode],
        "confidence": 98,
        "reason": reason,
        "title": title,
        "extracted_content": learning_script["full_commands"],
        "narration": learning_script["full_narration"],
        "learning_script": learning_script
    }

def build_tailored_learning_script(text: str, mode: str, clean_title: str, duration_sec: float = 15.0) -> dict:
    """
    根據使用者輸入的主題（如：學習python、Docker入門、Git指令、AI生片等），
    自動生成結構化「學習教學腳本」(含多個學習步驟、執行指令/代碼、終端機即時輸出日誌、口播講解詞)。
    """
    lower = text.lower()
    
    # 1. Python 專屬實戰學習腳本
    if any(k in lower for k in ["python", "py", "爬蟲", "pandas", "numpy"]):
        title = "Python 基礎入門與實戰教學"
        summary = "本教學涵蓋 Python 環境驗證、執行第一支程式碼、結構化腳本撰寫到自動化執行全流程。"
        steps = [
            {
                "step": 1,
                "title": "驗證 Python 3 開發環境",
                "cmd": "python3 --version",
                "logs": [
                    "Python 3.14.4 (繁體中文開發環境已就緒)",
                    "GCC 13.2.0 on linux x86_64",
                    "[OK] Python 解譯器運行正常"
                ],
                "narration": "哈囉大家好！今天我們來快速學習 Python。第一步先在終端機確認 Python 3 環境，確保解譯器正確安裝。"
            },
            {
                "step": 2,
                "title": "執行第一行 Python 互動代碼",
                "cmd": 'python3 -c "print(\'Hello, Python 2026 AI Studio!\')"',
                "logs": [
                    "Hello, Python 2026 AI Studio!",
                    "[OK] 互動式語法執行成功，毫秒級輸出！"
                ],
                "narration": "接著我們透過單行指令執行第一支程式，輸出 Hello Python，驗證語法執行引擎運作正常！"
            },
            {
                "step": 3,
                "title": "撰寫結構化 Python 實戰腳本",
                "cmd": "cat > learn_python.py << 'EOF'\nskills = ['變數宣告', '迴圈控制', 'AI自動化']\nfor i, s in enumerate(skills, 1):\n    print(f'第{i}講：掌握 {s}')\nEOF",
                "logs": [
                    "[OK] 成功建立 learn_python.py 學習檔案",
                    "程式碼行數: 4 行 | 編碼: UTF-8"
                ],
                "narration": "現在我們建立一個實戰腳本，定義 Python 核心技能清單，並透過迴圈逐行輸出，快速掌握語法結構！"
            },
            {
                "step": 4,
                "title": "編譯並執行 Python 腳本",
                "cmd": "python3 learn_python.py",
                "logs": [
                    "第1講：掌握 變數宣告",
                    "第2講：掌握 迴圈控制",
                    "第3講：掌握 AI自動化",
                    "[OK] 恭喜！Python 學習腳本 100% 執行成功！"
                ],
                "narration": "最後執行剛才撰寫的腳本，終端機瞬間輸出結果，恭喜大家成功掌握 Python 基礎工作流！"
            }
        ]
        full_cmds = "python3 --version\npython3 -c \"print('Hello, Python 2026 AI Studio!')\"\npython3 learn_python.py"
        full_narr = "哈囉大家好！今天我們來快速學習 Python 基礎操作。第一步先在終端機確認環境，接著執行第一支程式輸出 Hello Python，並撰寫實戰腳本建立學習地圖，最後一鍵執行輸出成果，輕鬆掌握 Python 基礎！"

    # 2. Docker 容器學習腳本
    elif any(k in lower for k in ["docker", "container", "容器"]):
        title = "Docker 容器化入門與實戰教學"
        summary = "本教學涵蓋 Docker 版本檢驗、映像檔拉取、啟動輕量容器與容器生命週期管理。"
        steps = [
            {
                "step": 1,
                "title": "檢查 Docker 守護進程狀態",
                "cmd": "docker --version",
                "logs": ["Docker version 27.1.1, build 6312e80", "[OK] Docker Daemon 運行正常"],
                "narration": "第一步我們透過命令列檢查 Docker 引擎版本與背景服務狀態，確保容器環境就緒。"
            },
            {
                "step": 2,
                "title": "拉取極簡 Alpine 官方映像檔",
                "cmd": "docker pull alpine:latest",
                "logs": ["latest: Pulling from library/alpine", "Digest: sha256:beef123...", "Status: Downloaded newer image [OK]"],
                "narration": "接著從 Docker Hub 下載極簡 Alpine Linux 映像檔，體積僅 5MB，適合秒級啟動！"
            },
            {
                "step": 3,
                "title": "在隔離容器中執行第一條指令",
                "cmd": 'docker run --rm alpine echo "Hello from Docker Isolated Sandbox!"',
                "logs": ["Hello from Docker Isolated Sandbox!", "[OK] 容器執行完畢並自動清理 (--rm)"],
                "narration": "現在我們啟動隔離容器，輸出 Hello Docker，並利用 rm 參數在執行完畢後自動釋放資源。"
            },
            {
                "step": 4,
                "title": "檢視本機容器與映像檔清單",
                "cmd": "docker images && docker ps -a",
                "logs": ["REPOSITORY   TAG       IMAGE ID       SIZE", "alpine       latest    a78b40813959   7.8MB", "[OK] 容器管理管線驗證完成！"],
                "narration": "最後檢視容器與映像檔清單，確認儲存空間配置，順利完成 Docker 容器實戰！"
            }
        ]
        full_cmds = "docker --version\ndocker pull alpine:latest\ndocker run --rm alpine echo 'Hello Docker!'\ndocker images"
        full_narr = "今天帶大家快速上手 Docker 容器化技術！從版本檢驗、拉取官方映像檔、執行隔離容器到清單管理，輕鬆掌握現代容器維運核心技能！"

    # 3. Git 版本控制學習腳本
    elif any(k in lower for k in ["git", "github", "版本控制"]):
        title = "Git 版本控制入門與代碼提交實戰"
        summary = "本教學涵蓋 Git 倉庫狀態檢驗、檔案暫存提交、日誌追蹤與分支管理。"
        steps = [
            {
                "step": 1,
                "title": "檢查 Git 倉庫工作區狀態",
                "cmd": "git status",
                "logs": ["位於分支 main", "您的分支與上游分支 'origin/main' 一致。", "無未追蹤的檔案，工作目錄乾淨 [OK]"],
                "narration": "第一步執行 git status，即時掌握目前分支名稱與檔案異動狀態，確保工作區整潔。"
            },
            {
                "step": 2,
                "title": "檢視近期提交歷史紀錄",
                "cmd": "git log --oneline -n 3",
                "logs": ["a1b2c3d feat: 完成 AI 自動化工作流核心模組", "e4f5g6h fix: 優化視覺排版與字幕圖層", "i7j8k9l chore: 初始化專案結構與相依套件"],
                "narration": "接著透過單行日誌檢視近三次 Commit 紀錄，清楚追蹤版本演進歷程。"
            },
            {
                "step": 3,
                "title": "建立新功能分支",
                "cmd": "git checkout -b feature/ai-pipeline",
                "logs": ["Switched to a new branch 'feature/ai-pipeline'", "[OK] 成功切換至功能分支"],
                "narration": "現在我們建立一個獨立的功能開發分支，讓後續的修改不影響主線 main 分支。"
            },
            {
                "step": 4,
                "title": "驗證分支切換並檢視分支清單",
                "cmd": "git branch",
                "logs": ["* feature/ai-pipeline", "  main", "[OK] Git 版本控制實戰完成！"],
                "narration": "最後確認分支切換成功，學會標準的 Git 團隊協同開發工作流！"
            }
        ]
        full_cmds = "git status\ngit log --oneline -n 3\ngit checkout -b feature/ai-pipeline\ngit branch"
        full_narr = "掌握 Git 是每一位開發者的必備技能！今天我們完整示範檢查倉庫狀態、查閱歷史紀錄與建立功能分支，建立紮實的版本控制基礎！"

    # 4. 網頁 AI 或提示詞學習 (Browser 模式)
    elif mode == "browser" or any(k in lower for k in ["ai", "chatgpt", "deepseek", "claude", "prompt"]):
        title = f"{clean_title} · AI 工具對話實戰"
        summary = "在瀏覽器中模擬向頂級大模型輸入精準提示詞，並即時串流觀看結構化回應。"
        steps = [
            {
                "step": 1,
                "title": "打開 AI 助理對話介面",
                "cmd": "聚焦瀏覽器提示詞輸入框",
                "logs": ["🔒 https://chat.ai-studio.local/workspace", "[OK] AI 推論引擎連線成功"],
                "narration": "在瀏覽器中開啟 AI 智慧對話助理，系統已為您載入最新大模型。"
            },
            {
                "step": 2,
                "title": "輸入結構化提示詞",
                "cmd": f"請幫我規劃一套關於「{clean_title}」的 7 天速成學習地圖，包含觀念拆解與實作練習",
                "logs": [f"提問：請幫我規劃一套關於「{clean_title}」的 7 天速成學習地圖..."],
                "narration": "向 AI 輸入精準提問，要求拆解學習路徑與核心觀念。"
            },
            {
                "step": 3,
                "title": "點擊送出並即時串流解答",
                "cmd": "點擊 Send ➔ 送出提問",
                "logs": ["🤖 AI 正在即時生成回答...", "Day 1: 核心觀念建立與環境配置", "Day 2: 基礎語法與動手實踐", "Day 3: 實務專案開發與成果輸出"],
                "narration": "送出提問後，畫面即時串流輸出結構化學習計畫，效率提升十倍！"
            }
        ]
        full_cmds = f"請幫我規劃一套關於「{clean_title}」的 7 天速成學習地圖，包含觀念拆解與實作練習"
        full_narr = f"現在向 AI 助手提問【{clean_title}】的最佳學習路徑，大模型會即時生成清晰的步驟指南與實務練習！"

    # 5. 代碼編輯 (VS Code 模式)
    elif mode == "editor" or any(k in lower for k in ["代碼", "code", "vscode", "編輯器"]):
        title = f"{clean_title} · 代碼編程實戰"
        summary = "在 VS Code 中模擬逐行打入代碼、語法高亮、Ctrl+S 存檔並一鍵執行。"
        steps = [
            {
                "step": 1,
                "title": "開啟 VS Code 編輯器並新增檔案",
                "cmd": "code main.py",
                "logs": ["[VS Code] 已建立 main.py 編輯視窗", "語言模式: Python"],
                "narration": "打開 VS Code 編輯器，準備編寫核心模組。"
            },
            {
                "step": 2,
                "title": "撰寫函數與資料處理邏輯",
                "cmd": "def main():\n    skills = ['自動化', 'AI模型', '影片生成']\n    print(f'[AI Studio] 核心技能：{skills}')\nmain()",
                "logs": ["語法檢查: 0 errors, 0 warnings [OK]"],
                "narration": "逐行敲入函數定義與資料處理邏輯，享受現代編輯器的語法高亮與智慧補全。"
            },
            {
                "step": 3,
                "title": "快捷鍵存檔與點擊執行",
                "cmd": "Ctrl+S 存檔 -> F5 執行",
                "logs": ["[Terminal] python main.py", "[AI Studio] 核心技能：['自動化', 'AI模型', '影片生成']", "[OK] 程式執行成功！"],
                "narration": "按下 Ctrl+S 存檔並點擊 Run 執行，下方終端機即時輸出正確結果！"
            }
        ]
        full_cmds = "def main():\n    skills = ['自動化', 'AI模型', '影片生成']\n    print(f'[AI Studio] 核心技能：{skills}')\nmain()"
        full_narr = f"現在進入代碼編輯器，全自動打入【{clean_title}】實作程式碼，存檔後一鍵運行，體驗高效率開發工作流！"

    # 6. 通用學習主題 (預設強大模板)
    else:
        title = f"{clean_title} · 實戰學習指南"
        summary = f"本學習腳本引導新手全面掌握「{clean_title}」的核心步驟、指令操作與輸出成果。"
        steps = [
            {
                "step": 1,
                "title": f"步驟 1：初始化 {clean_title} 執行環境",
                "cmd": f"# 1. 檢查並初始化環境\necho \"[Init] 準備 {clean_title} 學習環境...\"",
                "logs": [f"[Init] 準備 {clean_title} 學習環境...", "[OK] 系統環境已就緒 (Status: OK)"],
                "narration": f"哈囉大家好！今天我們來學習【{clean_title}】。第一步先進行環境確認與前置設定。"
            },
            {
                "step": 2,
                "title": f"步驟 2：執行核心功能驗證",
                "cmd": f"# 2. 核心功能驗證\necho \"[Test] 執行 {clean_title} 核心指令...\"",
                "logs": [f"[Test] 執行 {clean_title} 核心指令...", "輸出結果: 100% 成功通過測試！"],
                "narration": f"第二步執行核心操作，驗證各項功能都能正確運作並產生預期結果。"
            },
            {
                "step": 3,
                "title": f"步驟 3：撰寫自動化實戰腳本",
                "cmd": f"# 3. 建立實戰工作流\necho \"[Build] 建立自動化工作流...\"",
                "logs": [f"[Build] 建立自動化工作流...", "[OK] 成功整合所有流程環節"],
                "narration": "接著將各個步驟串聯成自動化閉環，大幅節省日常重複手動時間。"
            },
            {
                "step": 4,
                "title": f"步驟 4：執行並驗收最終成果",
                "cmd": f"# 4. 執行並輸出成果\necho \"[OK] 【{clean_title}】學習任務順利達成！\"",
                "logs": [f"[OK] 【{clean_title}】學習任務順利達成！", "輸出狀態: 100% 成功完成"],
                "narration": f"最後一鍵執行驗收成果，恭喜大家順利掌握【{clean_title}】的完整實戰方法！"
            }
        ]
        full_cmds = f"echo '[Init] 準備 {clean_title}...'\necho '[Test] 執行核心指令...'\necho '[OK] 【{clean_title}】學習完成！'"
        full_narr = f"哈囉大家好！今天我們來學習【{clean_title}】。從環境確認、核心指令測試到自動化工作流，帶大家輕鬆掌握關鍵技能！"

    return {
        "title": title,
        "summary": summary,
        "duration": int(duration_sec),
        "steps": steps,
        "full_commands": full_cmds,
        "full_narration": full_narr
    }
