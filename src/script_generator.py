import os
import sys
import json
import math
import urllib.request
import urllib.parse

def estimate_scenes_and_words(duration_minutes: float):
    """
    計算指定分鐘數所需的場景數與總字數
    標準語音速率：每分鐘約 210~240 中文字 (取 225 字/分)
    每個場景時間約 20~30 秒 (取平均 25 秒/場景)
    """
    duration_minutes = max(0.5, float(duration_minutes))
    total_seconds = duration_minutes * 60
    target_words = int(duration_minutes * 225)
    
    # 每個場景約 25 秒
    num_scenes = max(2, round(total_seconds / 25))
    words_per_scene = max(40, int(target_words / num_scenes))
    
    return {
        "duration_minutes": duration_minutes,
        "total_seconds": total_seconds,
        "target_words": target_words,
        "num_scenes": num_scenes,
        "words_per_scene": words_per_scene
    }

def generate_script_by_ai(topic: str, duration_minutes: float = 3.0, style: str = "科技實戰", api_key: str = None) -> dict:
    """
    內建 AI 腳本生成器：
    根據主題、設定的影片分鐘數，自動生成多場景結構化腳本 (含 Badge, Title, Subtitle, Bullets, Highlight Box, Narration)
    若有 GEMINI_API_KEY 或 OPENAI_API_KEY 會優先調用大模型；
    若無 API Key 則啟動內建的智能結構化腳本演算法，免 Key 亦可立即生成精準長度之腳本。
    """
    plan = estimate_scenes_and_words(duration_minutes)
    
    # 檢查是否有雲端 API Key
    gemini_key = api_key or os.environ.get("GEMINI_API_KEY")
    openai_key = api_key or os.environ.get("OPENAI_API_KEY")

    if gemini_key:
        try:
            return _call_gemini_api(topic, plan, style, gemini_key)
        except Exception as e:
            print(f"⚠️ Gemini API 調用異常 ({e})，自動切換至內建智能腳本引擎！")
    elif openai_key:
        try:
            return _call_openai_api(topic, plan, style, openai_key)
        except Exception as e:
            print(f"⚠️ OpenAI API 調用異常 ({e})，自動切換至內建智能腳本引擎！")

    # 內建免 Key 智能腳本生成引擎
    return _generate_smart_built_in_script(topic, plan, style)

def _generate_smart_built_in_script(topic: str, plan: dict, style: str) -> dict:
    """
    內建智能生成演算法：根據影片分鐘數與主題，自動擴展對應長度的專業分鏡
    """
    duration_min = plan["duration_minutes"]
    num_scenes = plan["num_scenes"]
    clean_topic = topic.strip() if topic.strip() else "2026 最新 AI 全自動實戰工作流"

    # 標準 YouTube 高觀看結構原型池
    stage_templates = [
        {
            "stage": "hook",
            "badge": "🔥 爆款開場",
            "title_suffix": "：告別低效手動！",
            "subtitle": f"徹底顛覆傳統作法，用 AI 自動化省下 80% 時間",
            "bullets": [
                "痛點直擊：手動處理耗時又容易出錯",
                "零程式門檻：一般人也能輕鬆上手的全新架構",
                f"目標達成：{duration_min} 分鐘完整掌握核心秘訣"
            ],
            "code_box": f"$ ai-pipeline --init \"{clean_topic[:20]}\"\n>>> Loading AI Engine...\n>>> Ready to Automate: 100%",
            "narration_tpl": f"哈囉大家好，歡迎來到雙AI協同頻道！你是不是也常覺得處理「{clean_topic}」特別耗時間？今天這部影片，帶你用最新的 AI 工作流，徹底告別手動繁瑣步驟！"
        },
        {
            "stage": "concept",
            "badge": "⚡ 核心架構",
            "title_suffix": "：三大核心機制拆解",
            "subtitle": "多模型協同運作，各司其職發揮極致威力",
            "bullets": [
                "資料層：自動收集並清洗關鍵資訊",
                "推理層：大模型智能決策與邏輯推理",
                "執行層：一鍵自動化輸出最終成果"
            ],
            "code_box": "[Workflow Engine]\nInput Data -> AI Reasoning\n-> Structured Action -> Done!",
            "narration_tpl": f"要搞定「{clean_topic}」，核心關鍵就在於架構分工。讓 AI 負責邏輯分析與繁瑣處理，你只需要專注在決策與靈感輸出。"
        },
        {
            "stage": "step1",
            "badge": "🛠️ 實戰第一步",
            "title_suffix": "：環境與工具一鍵就緒",
            "subtitle": "不需要複雜的安裝設定，開箱即用",
            "bullets": [
                "支援 Windows、Mac 與 Linux 跨平台",
                "模組化設計：免設定複雜 API 即可開跑",
                "直覺化操作：界面與指令雙軌支援"
            ],
            "code_box": "$ setup-agent --quick-start\n[✔] Dependencies installed\n[✔] Studio ready!",
            "narration_tpl": "第一步非常簡單，我們完全不需要配置昂貴的伺服器或複雜環境，只要透過預設好的工作台，一鍵就能把整個系統啟動起來。"
        },
        {
            "stage": "step2",
            "badge": "🚀 實戰第二步",
            "title_suffix": "：核心邏輯與流程串接",
            "subtitle": "將繁複的流程轉化為全自動閉環",
            "bullets": [
                "自動化管線監控：實時掌握運行狀態",
                "異常自動重試與修復機制",
                "毫秒級響應速度，告別等待焦慮"
            ],
            "code_box": "$ run-task --mode continuous\n>>> Processing batch items...\n>>> Status: 200 OK (0.42s)",
            "narration_tpl": "接下來就是最精彩的部分：我們把剛才設定好的規則交給系統自動運轉，你會發現原本要花好幾天的繁瑣流程，現在幾秒鐘就處理完畢！"
        },
        {
            "stage": "demo",
            "badge": "🎯 成果示範",
            "title_suffix": "：實機震撼效果展示",
            "subtitle": "只需一句話指令，成果直接呈現眼前",
            "bullets": [
                "高精準度：輸出品質超越手動成果",
                "多格式支援：表格、圖文、影音一應俱全",
                "即時預覽與一鍵導出"
            ],
            "code_box": "User: 產生完整分析報表\nAgent: Generating report...\nSaved: output_final.mp4 [Success!]",
            "narration_tpl": "你看畫面上的實際成果！從輸入指令到完整產出，不僅速度極快，而且細節豐富，這就是最新 AI 協同帶來的生產力革命。"
        },
        {
            "stage": "tips",
            "badge": "💡 進階秘訣",
            "title_suffix": "：避坑指南與關鍵細節",
            "subtitle": "老手才知道的隱藏設定，讓效果再提升 200%",
            "bullets": [
                "提示詞優化：如何引導 AI 給出最精準解答",
                "快取機制：節省時間與算力消耗",
                "靈活調參：自訂最適合你工作習慣的模式"
            ],
            "code_box": "Optimization Tips:\n- Use structured markdown inputs\n- Enable local caching for 10x speed",
            "narration_tpl": "在這裡跟大家分享一個關鍵技巧：在執行時善用結構化指令與快取機制，可以讓整體穩定度大幅提升，完全避免常見的卡頓問題。"
        },
        {
            "stage": "roi",
            "badge": "📊 效益對比",
            "title_suffix": "：傳統作法 vs AI 自動化",
            "subtitle": "數據說話！效率翻倍、時間成本直降 90%",
            "bullets": [
                "時間投入：從數小時壓縮至幾分鐘",
                "人力成本：單人即可搞定團隊工作量",
                "持續複利：建立一次，隨時反覆調用"
            ],
            "code_box": "[Comparison]\nManual: 4.5 hours | High effort\nAI Studio: 3 minutes | 1-Click Done",
            "narration_tpl": "算一算這筆帳：以前手動操作需要耗費大半天，現在全部自動化，你把省下來的時間拿去構思新題目或休息，效率直接翻了好幾倍！"
        },
        {
            "stage": "cta",
            "badge": "🔔 訂閱與資源",
            "title_suffix": "：立即動手實作！",
            "subtitle": "完整專案與設定檔已在說明欄開放領取",
            "bullets": [
                "歡迎在留言區分享你的實作成果與點子",
                "持續鎖定頻道，掌握最新 AI 黑科技",
                "記得按讚、訂閱、開啟小鈴鐺！"
            ],
            "code_box": "Thanks for watching!\n>>> Next Episode:\n自訂聲音與私有化模型進階實戰",
            "narration_tpl": f"以上就是今天的「{clean_topic}」完整教學！專案代碼與工具都已經整理在下方說明欄。如果覺得實用，別忘了按讚、訂閱並開啟小鈴鐺，我們下期再見！"
        }
    ]

    # 根據要求的場景數 num_scenes 進行挑選與拼接
    selected_scenes = []
    if num_scenes <= 3:
        # 短影片 (1分鐘內)：Hook -> Demo -> CTA
        chosen_stages = [stage_templates[0], stage_templates[4], stage_templates[7]]
    elif num_scenes <= 5:
        # 2分鐘：Hook -> Concept -> Step 1 -> Demo -> CTA
        chosen_stages = [stage_templates[0], stage_templates[1], stage_templates[2], stage_templates[4], stage_templates[7]]
    elif num_scenes <= 8:
        # 3分鐘：8 場景全選
        chosen_stages = stage_templates[:num_scenes]
    else:
        # 5~10分鐘：循環擴展不同專題深入探討步驟
        chosen_stages = list(stage_templates)
        extra_count = num_scenes - len(stage_templates)
        for i in range(extra_count):
            idx = i + 1
            chosen_stages.insert(4 + i, {
                "stage": f"deep_dive_{idx}",
                "badge": f"🔍 深度探討 0{idx}",
                "title_suffix": f"：模組解析與案例實操 (第{idx}部分)",
                "subtitle": "針對常見邊界狀況的實務處理解決方案",
                "bullets": [
                    f"細分模組實測：針對不同情境自動適配",
                    "數據一致性校驗與防錯邏輯",
                    "產出日誌實時追蹤與分析"
                ],
                "code_box": f"$ agent-exec --module part_{idx}\n>>> Analyzing test case #{idx}...\n>>> Status: PASS",
                "narration_tpl": f"接下來我們深入探討第 {idx} 個關鍵核心模組。在很多複雜的實務情境中，透過這樣的防錯與適配機制，能確保整個流程萬無一失。"
            })

    # 組合最終場景陣列
    scenes_output = []
    for s in chosen_stages:
        title = f"{clean_topic}{s.get('title_suffix', '')}"
        if len(title) > 28:
            title = title[:28] + "..."
        scenes_output.append({
            "badge": s["badge"],
            "title": title,
            "subtitle": s["subtitle"],
            "bullets": s["bullets"],
            "highlight_box": s["code_box"],
            "narration": s["narration_tpl"]
        })

    return {
        "title": clean_topic,
        "duration_minutes": duration_min,
        "total_scenes": len(scenes_output),
        "target_words": plan["target_words"],
        "scenes": scenes_output
    }

def _call_gemini_api(topic: str, plan: dict, style: str, api_key: str) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    prompt = f"""你是一名頂級 YouTube 科技/AI 實戰頻道腳本架構師。
請為頻道創作一部影片腳本，主題為：「{topic}」。
目標時長：{plan['duration_minutes']} 分鐘。
總共需要精確產生 {plan['num_scenes']} 個分鏡場景（Scene）。
請以繁體中文 (台灣風格，如「哈囉大家好」、「這款工具」、「搞定」) 輸出合法的 JSON，不要包含任何 markdown 標籤或其餘贅字。
JSON 結構格式：
{{
  "title": "{topic}",
  "duration_minutes": {plan['duration_minutes']},
  "scenes": [
    {{
      "badge": "短標籤 (如：🔥 實戰開場)",
      "title": "大標題 (20字內，吸引人)",
      "subtitle": "副標題 (30字內)",
      "bullets": ["重點1", "重點2", "重點3"],
      "highlight_box": "終端機代碼或架構圖 (多行純文字)",
      "narration": "主播口播旁白 (約 {plan['words_per_scene']} 字，自然流暢)"
    }}
  ]
}}"""
    data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        raw_text = res["candidates"][0]["content"]["parts"][0]["text"].strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1].rsplit("\n```", 1)[0].strip()
        return json.loads(raw_text)

def _call_openai_api(topic: str, plan: dict, style: str, api_key: str) -> dict:
    url = "https://api.openai.com/v1/chat/completions"
    prompt = f"請為主題「{topic}」製作長度為 {plan['duration_minutes']} 分鐘、共 {plan['num_scenes']} 個場景的 YouTube 繁中腳本 JSON。"
    payload = {
        "model": "gpt-4o-mini",
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "You are a professional YouTube scriptwriter. Return pure JSON with title, duration_minutes, and scenes list."},
            {"role": "user", "content": prompt}
        ]
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        return json.loads(res["choices"][0]["message"]["content"])

if __name__ == "__main__":
    test_script = generate_script_by_ai("5分鐘教你打造自動剪片機器人", duration_minutes=3.0)
    print(f"✅ 成功生成腳本：{test_script['title']}，共 {len(test_script['scenes'])} 分鏡")
