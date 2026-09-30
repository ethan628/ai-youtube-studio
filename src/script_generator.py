import os
import sys
import json
import math
import time
import re
import urllib.request
import urllib.parse

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def estimate_scenes_and_words(duration_minutes: float):
    """
    計算指定分鐘數所需的場景數與總字數（支援 0.5 ~ 60 分鐘）
    標準語音速率：每分鐘約 225 中文字
    依據時長智能調節單幕節奏 (25 ~ 35 秒/幕)
    """
    duration_minutes = max(0.5, min(60.0, float(duration_minutes)))
    total_seconds = duration_minutes * 60
    target_words = int(duration_minutes * 225)
    
    # 短片節奏較快 (25s)，長片每幕深入闡述 (30~35s)
    if duration_minutes <= 5:
        pace_sec = 25
    elif duration_minutes <= 15:
        pace_sec = 30
    else:
        pace_sec = 35

    num_scenes = max(2, round(total_seconds / pace_sec))
    words_per_scene = max(80, int(target_words / num_scenes))
    
    return {
        "duration_minutes": duration_minutes,
        "total_seconds": total_seconds,
        "target_words": target_words,
        "num_scenes": num_scenes,
        "words_per_scene": words_per_scene
    }

def is_programming_topic(topic: str) -> bool:
    """
    判斷主題是否為程式/代碼/技術開發範疇。
    若不是程式主題，嚴禁在腳本、說明欄、卡片中出現終端機指令、Python 程式碼或 pip 等程式元素。
    """
    if not topic:
        return False
    from src.rubiks_cube_engine import is_rubiks_cube_topic
    if is_rubiks_cube_topic(topic):
        return False
    t = topic.lower()

    # 明確宣告不寫程式的排除詞
    for neg in ["不寫程式", "不用寫程式", "不用寫代碼", "零代碼", "免代碼", "nocode", "no-code", "不寫python", "不用寫code", "不需寫代碼"]:
        if neg in t:
            return False

    # 程式/代碼關鍵詞
    code_keywords = [
        "python", "javascript", "typescript", "golang", "rust", "c++", "c#", "java", "php",
        "寫程式", "寫代碼", "寫code", "編程", "程式碼", "源代碼", "原始碼", "原始代碼",
        "函數", "函式庫", "算法", "演算法", "bug", "debug", "api開發", "sdk", "sql", "資料庫",
        "terminal", "終端機", "linux", "bash", "shell", "docker", "k8s", "pip install", "npm install",
        "flask", "django", "fastapi", "vue", "react", "前端開發", "後端開發", "全端開發",
        "git clone"
    ]
    return any(k in t for k in code_keywords)

def predict_next_episode(current_topic: str, duration_minutes: float = 3.0, style: str = "科技實戰", api_key: str = None) -> dict:
    """
    智慧連載推薦引擎：
    根據當前影片主題、領域與集數，自動推導最具吸引力與連貫性的【下一集】主題、預告旁白與亮點。
    若為非程式主題，嚴禁推薦程式類題材。
    """
    clean_topic = current_topic.strip() if current_topic and current_topic.strip() else "2026 最新實戰工作流"
    is_code = is_programming_topic(clean_topic)

    # 內建啟發式連載規則庫 (Heuristic Curriculum & Series Engine)
    ep_match = re.search(r'(?:EP|ep|第)\s*(\d+)\s*(?:集|講|期)?', clean_topic)
    ep_num = 1
    if ep_match:
        try:
            ep_num = int(ep_match.group(1))
            next_ep_num = ep_num + 1
            prefix = ep_match.group(0)
            base_title = clean_topic.replace(prefix, "").strip("：:- ")
        except Exception:
            next_ep_num = ep_num + 1
    else:
        next_ep_num = 2

    from src.rubiks_cube_engine import is_rubiks_cube_topic
    if is_rubiks_cube_topic(clean_topic):
        candidates = [
            "【速解進階】魔術方塊進階指法與 30 秒盲擰/速解技巧全拆解",
            "【花式秘笈】魔術方塊六面彩虹與對稱花樣圖案秘笈",
            "【二階魔方】二階魔術方塊極速復原：只需兩條公式！",
            "【異形魔方】金字塔魔方零門檻極速入門教學"
        ]
        chosen = candidates[0]
        return {
            "current_topic": clean_topic,
            "next_episode_number": next_ep_num,
            "next_topic": chosen,
            "next_teaser_narration": f"在下一集影片中，我們將帶來【{chosen}】！帶你解鎖更快的手法與高階進階技巧，記得訂閱開啟小鈴鐺！",
            "highlights": ["30 秒速解進階指法", "OLL/PLL 極速指法優化", "無痛提速訓練心法"],
            "is_programming": False
        }

    # 若有 API Key 優先嘗試調用大模型
    gemini_key = api_key or os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            return _call_gemini_predict_next(clean_topic, duration_minutes, style, gemini_key)
        except Exception:
            pass

    # 依據主題領域與是否為程式進行分流推薦
    if is_code:
        # 程式開發類續集
        if any(k in clean_topic for k in ["三大", "工具", "入門", "基礎", "新手", "零門檻", "推薦"]):
            candidates = [
                f"打造專屬本地私有化 AI 智能體：從零串接與全自動無人維運實戰",
                f"多智能體 (Multi-Agent Swarm) 協同作戰：一行指令自動完成複雜專案",
                f"突破 Token 限制！超長文本向量檢索與私有知識庫防幻覺優化"
            ]
        elif any(k in clean_topic for k in ["爬蟲", "抓取", "數據", "網頁", "excel"]):
            candidates = [
                f"AI 深度數據清洗與全自動 BI 視覺化儀表板：從零打造即時戰情報告",
                f"全自動動態網頁監控與異常告警推播：LINE/Telegram 零延遲通報",
                f"多來源數據融合與大模型預測決策：個人量化分析實戰"
            ]
        else:
            candidates = [
                f"【進階實戰】{clean_topic}之全自動無人值守落地指南",
                f"【極限優化】{clean_topic}常見避坑指南與性能翻倍秘訣",
                f"【商業落地】將{clean_topic}轉化為被動自動化服務全流程"
            ]
    else:
        # 非程式類題材（生活、自媒體、時間、思維、職場、理財等）
        if any(k in clean_topic for k in ["自媒體", "影音", "剪輯", "流量", "頻道", "youtube", "tiktok", "短片"]):
            candidates = [
                "【爆款選題】建立源源不絕的靈感庫：用一套模板持續產生高觀看主題",
                "【完播率秘訣】黃金前 3 秒留存法則：讓觀眾一秒停下來看完整部影片",
                "【內容矩陣】從單支長片到全平台裂變：打造個人可持續內容飛輪"
            ]
        elif any(k in clean_topic for k in ["時間", "效率", "專注", "拖延", "工作法", "習慣"]):
            candidates = [
                "【精力管理】擺脫持續疲勞感：高效人士都在用的充沛活力作息法",
                "【深度工作】消除分心誘惑：打造每天 3 小時的高產出心流狀態",
                "【習慣複利】每天進步 1%：如何用微習慣徹底戰勝拖延症"
            ]
        elif any(k in clean_topic for k in ["理財", "投資", "金錢", "資產", "收入"]):
            candidates = [
                "【穩健增長】普通人也能輕鬆上手的資產配置心法：告別追高殺跌",
                "【副業變現】將個人專業轉化為持續被動收入的實戰路徑",
                "【財富思維】從勞力賺錢到槓桿獲利：普通人破局的底層邏輯"
            ]
        elif any(k in clean_topic for k in ["心理", "情緒", "壓力", "焦慮", "溝通", "人際"]):
            candidates = [
                "【情緒穩定】告別精神內耗：建立強大心理韌性的 3 個科學習慣",
                "【高情商表達】如何把話說到對方心坎裡：職場與人際溝通關鍵術",
                "【自我確立】找到個人核心熱情：在充滿不確定的世界中確立確定感"
            ]
        elif any(k in clean_topic for k in ["三大", "工具", "推薦", "盤點"]):
            candidates = [
                f"【進階指南】{clean_topic}之高階落地技巧與少走彎路指南",
                f"【實戰複利】將方法融入日常：實現效率倍增的實踐手冊",
                f"【成果放大】從新手到精通：關鍵細節與核心要點全拆解"
            ]
        else:
            candidates = [
                f"【進階實戰】{clean_topic}之深度實踐與落地指南",
                f"【避坑指南】{clean_topic}常見盲區與少走彎路的核心原則",
                f"【成果放大】把{clean_topic}轉化為長期持續優勢的方法論"
            ]

    if ep_match:
        candidates = [f"第{next_ep_num}集：{c}" for c in candidates]

    chosen_next_topic = candidates[0]
    teaser_narration = f"在下一集影片中，我們將帶來【{chosen_next_topic}】深度分享，完整拆解核心關鍵！千萬不要錯過，記得按讚、訂閱並開啟小鈴鐺！"
    teaser_box = f">>> Next Episode (下集預告):\n【{chosen_next_topic}】\n精彩亮點: 核心方法深度拆解 | 立即實踐"

    highlights = [
        f"接續本集核心架構，深入【{chosen_next_topic}】",
        "解鎖進階避坑技巧，讓實踐效益再翻倍",
        "完整提供精華筆記與具體行動清單"
    ]

    return {
        "current_topic": clean_topic,
        "next_topic": chosen_next_topic,
        "next_episode_num": next_ep_num,
        "alternative_topics": candidates,
        "teaser_narration": teaser_narration,
        "teaser_box": teaser_box,
        "highlights": highlights,
        "duration_minutes": duration_minutes,
        "is_programming": is_code
    }

def _call_gemini_predict_next(current_topic: str, duration_minutes: float, style: str, api_key: str) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    prompt = f"""你是一名頂級 YouTube 科技/AI 實戰頻道爆款策劃師。
當前影片主題為：「{current_topic}」。
請為此頻道設計最具點擊率與追劇感的【下一集】主題與亮點規劃。
請以繁體中文 (台灣用語風格) 輸出合法的 JSON，不要 markdown 格式。
結構：
{{
  "next_topic": "下一集吸睛標題 (25字內)",
  "alternative_topics": ["候選主題1", "候選主題2", "候選主題3"],
  "teaser_narration": "在當前影片結尾的下集預告旁白 (約50字)",
  "teaser_box": "下集預告文字卡片內容 (多行代碼或標語)",
  "highlights": ["亮點1", "亮點2", "亮點3"]
}}"""
    data = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        raw = res["candidates"][0]["content"]["parts"][0]["text"].strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("\n```", 1)[0].strip()
        data_json = json.loads(raw)
        data_json["current_topic"] = current_topic
        data_json["duration_minutes"] = duration_minutes
        return data_json

def generate_next_episode_script(current_topic: str, duration_minutes: float = 3.0, style: str = "科技實戰", api_key: str = None, chosen_topic: str = None) -> dict:
    """
    自己出下一集腳本：
    1. 智慧推導或使用指定的下一集主題
    2. 自動產出完整的下一集多幕分鏡結構腳本
    3. 注入上一集關聯與下一集連載預告（實現無限連載模式）
    """
    next_info = predict_next_episode(current_topic, duration_minutes, style, api_key)
    target_topic = chosen_topic or next_info["next_topic"]

    next_script = generate_script_by_ai(topic=target_topic, duration_minutes=duration_minutes, style=style, api_key=api_key)
    next_script["previous_topic"] = current_topic
    next_script["is_next_episode"] = True
    next_script["next_episode_meta"] = next_info

    # 儲存持久化規劃至 next_episode_plan.json
    try:
        plan_path = os.path.join(PROJECT_ROOT, "next_episode_plan.json")
        with open(plan_path, "w", encoding="utf-8") as f:
            json.dump({
                "source_topic": current_topic,
                "current_episode_topic": target_topic,
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "script": next_script,
                "next_info": next_info
            }, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return next_script

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

    res = None
    if gemini_key:
        try:
            res = _call_gemini_api(topic, plan, style, gemini_key)
        except Exception as e:
            print(f"⚠️ Gemini API 調用異常 ({e})，自動切換至內建智能腳本引擎！")
    elif openai_key:
        try:
            res = _call_openai_api(topic, plan, style, openai_key)
        except Exception as e:
            print(f"⚠️ OpenAI API 調用異常 ({e})，自動切換至內建智能腳本引擎！")

    if not res:
        # 內建免 Key 智能腳本生成引擎
        res = _generate_smart_built_in_script(topic, plan, style)

    # 確保具備下一集規劃資訊
    if "next_episode" not in res or not res["next_episode"]:
        res["next_episode"] = predict_next_episode(topic, duration_minutes, style, api_key)

    return res

def _generate_smart_built_in_script(topic: str, plan: dict, style: str) -> dict:
    """
    內建智能生成演算法：根據影片分鐘數與主題，自動擴展對應長度的專業分鏡。
    依據主題是否為程式，嚴格分流：
    - 非程式主題：全面去除任何代碼、終端機命令、pip 等，改為核心精華筆記、思考模型與行動清單。
    - 程式主題：保留標準代碼與終端機工作流原型。
    """
    duration_min = plan["duration_minutes"]
    num_scenes = plan["num_scenes"]
    clean_topic = topic.strip() if topic.strip() else "2026 最新實戰工作流"
    from src.rubiks_cube_engine import is_rubiks_cube_topic
    is_rubik = is_rubiks_cube_topic(clean_topic)
    is_code = False if is_rubik else is_programming_topic(clean_topic)

    # 先預測下一集主題，以便在結尾 (Outro / CTA) 自動置入下集預告
    next_info = predict_next_episode(clean_topic, duration_min, style)
    next_topic_clean = next_info.get("next_topic", "打造專屬個人高效成長系統")

    if is_rubik:
        # 🎲 魔術方塊專屬七步解法分鏡原型池 (配合 3D 解法旋轉動畫，嚴禁任何代碼/終端機)
        stage_templates = [
            {
                "stage": "intro",
                "badge": "🎉 六面全解成果搶先看",
                "title_suffix": "：零廢話！手把手全解震撼效果",
                "subtitle": "開頭直接看成果！原本打亂的魔方，一套口訣輕鬆搞定",
                "bullets": [
                    "六面全解成果：照著步驟走，任何人都能100%全解",
                    "摒棄冗長鋪陳：告別死記硬背，直觀口訣秒上手",
                    "前 15 秒建立信心：只要掌握層先法，復原超有成就感"
                ],
                "code_box": "【🎉 六面全解震撼成果搶先看】\n打亂狀態 ➔ 7步層先法 ➔ 六面完美全解！\n核心理念: 零廢話鋪陳，跟著口訣直接通關",
                "narration_tpl": f"大家先看畫面上這個成果！原本徹底打亂的魔術方塊，現在六面已經全部完美復原！今天這部影片完全不講冗長的前置概念，直接帶你用最直覺的七步層先法，手把手把你手中的魔方從打亂到全解，我們馬上進入第一步！"
            },
            {
                "stage": "cross",
                "badge": "⭐ 步驟一",
                "title_suffix": "：白色小花與底層十字",
                "subtitle": "復原白色中心十字，並對齊四個側面中心顏色",
                "bullets": [
                    "小花定位：先在頂層黃色中心周圍聚集四個白稜塊",
                    "側面顏色對齊：轉動頂層讓側面顏色與中心塊同色",
                    "順轉 180 度翻下：四個白稜轉入底層，底十字完美成形"
                ],
                "code_box": "【步驟一口訣】\n白稜聚黃心 -> 側面顏色對齊 -> 旋轉180度翻至底面",
                "narration_tpl": "第一步是打下最穩固的基礎：底層十字。我們先在頂面黃色中心周圍做出四朵白花瓣，接著觀察每個白塊的另一個顏色，轉動頂層跟側面中心塊對齊後，直接往下轉 180 度，底面白色十字就大功告成了！"
            },
            {
                "stage": "first_layer",
                "badge": "🎯 步驟二",
                "title_suffix": "：底層角塊歸位 (解完第一層)",
                "subtitle": "學會萬能口訣「上左下右」，一次搞定四個底層角塊",
                "bullets": [
                    "鎖定目標角塊：找出含有白色的角塊，轉到目標槽位正上方",
                    "黃金口訣公式：上左下右 (R U R' U')",
                    "重複 1 至 5 次：角塊自動翻轉並精確嵌入底層位置"
                ],
                "code_box": "【黃金核心口訣】\nR U R' U' (右手：上左下右)\n目標角塊置於右上，重複直至白色朝下歸位",
                "narration_tpl": "第二步我們要復原整個底層的第一層！這裡只需要記住魔方最核心的黃金口訣：上、左、下、右，也就是 R、U、R撇、U撇。把目標角塊放在右上角，重複這個動作一到五次，底層四個角塊就會全部歸位！"
            },
            {
                "stage": "second_layer",
                "badge": "🚀 步驟三",
                "title_suffix": "：中層稜塊歸位 (F2L 前兩層)",
                "subtitle": "用對稱公式將頂層無黃稜塊推入中層兩側",
                "bullets": [
                    "尋找非黃稜塊：在頂層找到不含黃色的稜塊",
                    "對齊中心形成倒 T 字：轉動頂層對齊前方中心顏色",
                    "右手公式推入：U R U' R' U' F' U F (向左則鏡像操作)"
                ],
                "code_box": "【中層右側公式】\nU R U' R' U' F' U F\n(向右推入中層，前兩層全解完成)",
                "narration_tpl": "第三步我們要復原中層的四個稜塊，達到前兩層完全復原！在頂層找出一塊不含黃色顏色的稜塊，對齊顏色後，運用右側推入公式：U R U撇 R撇 U撇 F撇 U F，輕鬆將稜塊推進中層！"
            },
            {
                "stage": "top_cross",
                "badge": "⚡ 步驟四",
                "title_suffix": "：頂面黃色十字",
                "subtitle": "點、折線、一字、十字，一條順時針公式串聯",
                "bullets": [
                    "觀察頂面黃色圖案：點 ➔ 直角折線 ➔ 水平一字 ➔ 黃色十字",
                    "核心公式：壓前上左下右翻回 (F R U R' U' F')",
                    "橫向擺放一字：確保一字水平擺放後再做公式"
                ],
                "code_box": "【頂面十字公式】\nF R U R' U' F'\n(順序：點 -> 折線置左上 -> 一字水平 -> 十字)",
                "narration_tpl": "第四步開始進攻頂層！我們的目標是讓頂面拼出黃色十字。不管現在頂面是點、小直角還是一字，只要做出 F、R、U、R撇、U撇、F撇，頂面的黃色十字就會立刻浮現！"
            },
            {
                "stage": "oll",
                "badge": "✨ 步驟五",
                "title_suffix": "：小魚公式翻頂面 (頂面全黃)",
                "subtitle": "辨識小魚頭方向，小魚公式讓頂面九格全黃",
                "bullets": [
                    "小魚圖案辨識：十字加上一個角塊黃色朝上，形狀如同小魚",
                    "魚頭朝向左下：魚頭對準左下角開始做公式",
                    "小魚口訣：上左下左 上左左下 (R U R' U R U2 R')"
                ],
                "code_box": "【小魚翻頂公式 (OLL)】\nR U R' U R U2 R'\n(口訣：上左下左 上左左下，魚頭朝左下)",
                "narration_tpl": "第五步就是大家最喜歡的小魚公式！把頂面小魚的魚頭朝向左下角，念著口訣：上、左、下、左、上、左左、下，也就是 R U R撇 U R U2 R撇，整個頂面就會瞬間翻成滿滿的黃色！"
            },
            {
                "stage": "pll_solved",
                "badge": "🎉 步驟六",
                "title_suffix": "：頂層角塊與稜塊全解 (六面復原！)",
                "subtitle": "最後換角與換稜，迎接六面完全復原的感動時刻",
                "bullets": [
                    "尋找雙同色車燈角塊：將車燈置於後方，執行換角公式",
                    "最後三稜逆轉：換角完成後，順時針或逆時針將稜塊歸位",
                    "轉動頂層對齊：六面完全復原，大功告成！"
                ],
                "code_box": "【頂層全解公式 (PLL)】\nR U R' F' R U R' U' R' F R2 U' R'\n(六面完全復原，恭喜通關！)",
                "narration_tpl": "最後一步，我們來做頂層的角塊與稜塊換位！找到同一側兩個相同顏色的車燈角塊放在後面，執行最終公式，最後轉動頂層輕輕對齊，恭喜你，六面完全復原！你已經成功學會解魔術方塊了！"
            },
            {
                "stage": "outro",
                "badge": "🔔 總結與下集",
                "title_suffix": "：熟練心法與進階預告",
                "subtitle": "每天練習十分鐘，手速自然突飛猛進",
                "bullets": [
                    f"下集精彩預告：{next_topic_clean[:22]}",
                    "肌肉記憶心法：不看公式卡，靠手感盲轉",
                    "記得按讚、訂閱、開啟小鈴鐺！"
                ],
                "code_box": f"🎉 恭喜完全學會魔術方塊！\n>>> Next Episode (下集預告):\n{next_topic_clean}",
                "narration_tpl": f"以上就是今天的魔術方塊完整新手教學！在下一集影片中，我們將帶來【{next_topic_clean}】，帶你挑戰更驚人的速解手速。完整公式口訣都整理在下方說明欄，別忘了按讚訂閱開啟小鈴鐺，我們下期見！"
            }
        ]
        curriculum_pool = [
            {"title": "指法加速秘訣與手法練習", "sub": "練習食指撥動 U 層與右手大拇指固定手法", "bullets": ["指法撥動 (Flick) 取代全手腕轉動", "掌握右手 R U R' U' 盲轉肌肉記憶", "轉動過程保持視線觀察下一個色塊"], "code": "【手法加速要點】\n食指快速推 U 層 | 手腕小幅度放鬆\n盲轉黃金公式 R U R' U' 練到 1 秒 4 步"},
            {"title": "十字底面盲做心法（8步以內）", "sub": "觀察打亂後 15 秒內規劃完整十字路徑", "bullets": ["白色十字在底面直接組裝，不翻上頂面", "最多 8 步必定可以完成任何隨機打亂十字", "對位技巧：紅藍橘綠相對方位銘記在心"], "code": "【底十字盲做規範】\n15秒觀察 (Inspection) -> 預判4稜走向\n嚴格控制在 8 步之內直接復原底十字"},
            {"title": "F2L 前兩層直覺化理解與配對", "sub": "角塊與稜塊在頂層合體後整組推進槽位", "bullets": ["同色向頂與異色向頂的快速拆分心法", "利用空槽位進行無痛旋轉躲避", "徹底告別七步法的重複轉動，速度提升3倍"], "code": "【F2L 核心心法】\n頂層尋找角稜對 -> 同步調整朝向 ->\n整組插入槽位 (Slotting)"},
            {"title": "頂層 OLL 與 PLL 極速辨識技巧", "sub": "一眼看清車燈、純色塊與稜塊走向", "bullets": ["二步 OLL 與兩步 PLL 記憶路徑", "觀察相鄰色與對稱色，零秒切換公式", "頂層 AUF (Adjust U Face) 一轉即鎖定"], "code": "【極速辨識原則】\n只需看兩面側面特徵，不必轉動整個方塊\n鎖定特徵色直接起手相應公式"},
            {"title": "魔方保養與磁力手感調校", "sub": "軸距彈力、磁力強度與潤滑油搭配指南", "bullets": ["魔術方塊軸心螺絲垂直對稱調校", "高黏度軸心油 vs 低黏度跑道油搭配", "防止卡角與防爆塊 (Anti-POP) 最佳平衡點"], "code": "【魔方調試指南】\n彈力調校: 兼顧容錯性與穩定度\n潤滑保養: 軸心減噪，滑道順滑零阻力"}
        ]
    elif is_code:
        # 💻 程式開發類專屬分鏡原型池
        stage_templates = [
            {
                "stage": "hook",
                "badge": "⚡ 實機成果搶先看",
                "title_suffix": "：全自動工作流震撼成果！",
                "subtitle": "告別手動操作！一行指令自動完成所有複雜任務",
                "bullets": [
                    "實機成果即刻呈現：全自動閉環秒級輸出",
                    "效率極限對比：傳統 4.5 小時 ➔ 自動化 30 秒",
                    "跳過冗長鋪陳：直接拆解可立即落地的實戰管線"
                ],
                "code_box": f"[⚡ LIVE DEMO 實機成果搶先看]\n>>> Task: \"{clean_topic[:18]}\"\n>>> Pipeline: Running Multi-Agent Workflow...\n[✔] Status: 100% Completed (0.42s)\n[✔] Result: output_final.mp4 [Success!]",
                "narration_tpl": f"大家直接看畫面上這個震撼成果！原本需要手動花費好幾個小時的繁瑣流程，現在只要一行指令，短短幾秒鐘之內，全自動工作流就已經把所有成果精準輸出！今天我們跳過所有廢話鋪陳，直接帶你拆解並複製這套立即可用的全自動系統！"
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
                "narration_tpl": f"要徹底搞定「{clean_topic}」，核心關鍵就在於架構分工與多模型協同。由系統自動負責資料收集、邏輯分析與繁瑣處理，創作者只需要專注在決策與靈感輸出，就能將生產力推升至極致！"
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
                "narration_tpl": "第一步非常簡單，我們完全不需要配置昂貴的伺服器或安裝繁雜的環境依賴，只要透過今天展示的這套自動化工作台，點擊一鍵就能把整個系統無縫啟動，快速進入創作狀態！"
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
                "narration_tpl": "接下來就是最精彩的核心環節：我們把設定好的規格與工作流程交給系統自動運轉，你會發現原本需要耗費好幾天反覆調整的繁瑣步驟，現在只需要短短幾秒鐘就能全部精準跑完！"
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
                "narration_tpl": "大家可以仔細看畫面上展示的實際成果！從輸入最初的一句話指令，到整部影片與圖文資料完整產出，不僅速度極快而且細節滿滿，這就是最新 AI 自動化協同帶來的震撼生產力！"
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
                "narration_tpl": "在這裡跟大家分享一個老手才知道的關鍵技巧：在執行時善用結構化指令規範與本地快取機制，可以讓整體運算穩定度大幅提升，還能節省算力開銷，完全避免常見的格式錯誤與延遲！"
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
                "narration_tpl": "我們來認真算一算這筆時間成本：過去手動剪輯與腳本撰寫往往需要耗費一整天，現在全面導入自動化，你把省下來的大量寶貴時間拿去構思更多優質題目，長期的複利效益絕對超過數倍！"
            },
            {
                "stage": "cta",
                "badge": "🔔 訂閱與資源",
                "title_suffix": "：立即動手實作！",
                "subtitle": "完整專案與設定檔已在說明欄開放領取",
                "bullets": [
                    f"下集精彩預告：{next_topic_clean[:22]}",
                    "持續鎖定頻道，掌握最新 AI 黑科技",
                    "記得按讚、訂閱、開啟小鈴鐺！"
                ],
                "code_box": f"Thanks for watching!\n>>> Next Episode (下集預告):\n{next_topic_clean}",
                "narration_tpl": f"以上就是今天的「{clean_topic}」完整教學！在下一集影片中，我們將帶來【{next_topic_clean}】深度實戰教學。完整代碼與工具都已經整理在下方說明欄。如果覺得實用，別忘了按讚、訂閱並開啟小鈴鐺，我們下期再見！"
            }
        ]
        curriculum_pool = [
            {"title": "資料流架構設計與強型別合約", "sub": "建立端到端強型別資料檢驗標準", "bullets": ["Pydantic 結構化欄位驗證", "異常格式自動修復補齊", "邊界資料雜訊即時過濾"], "code": "$ schema-validate --strict\nStatus: 100% Validated"},
            {"title": "超長文本自動分塊與語義摘要", "sub": "保留核心邏輯並精確控制 Token", "bullets": ["層級化摘要遞迴演算法", "關鍵論點加權排序保留", "動態滑動窗口 (Sliding Window)"], "code": "$ summarizer --mode chunked\nTokens: 18,500 -> 920"},
            {"title": "動態視訊字幕毫秒級同步對齊", "sub": "波形頻譜與時間軸自動精準吻合", "bullets": ["VAD 語音活動檢測精確到毫秒", "音高與音量波形動態反饋", "智慧斷句與螢幕邊緣防遮擋"], "code": "$ align-subtitles --precision ms\nOffset: 0.00ms [Sync OK]"},
            {"title": "高對比科技視覺排版與渲染", "sub": "霓虹賽博龐克風格，大螢幕清晰吸睛", "bullets": ["粗體描邊與立體陰影特效", "背景電路網格動態融合", "支援 1080p 橫片與 9:16 Shorts"], "code": "$ render-canvas --res 1080p\nStyle: Cyberpunk Neon Blue"},
            {"title": "神經擬真聲音情感與語調調校", "sub": "突破機械感！讓 AI 配音充滿感染力", "bullets": ["語速微調 (+0% ~ +8%) 匹配節奏", "標點符號換氣與停頓深度控制", "雙聲道立體聲母帶級響度標準化"], "code": "$ tts-engine --tune expressiveness\nPitch: +2Hz | Rate: +5% [Natural]"},
            {"title": "本地私有大模型無網絡離線部署", "sub": "完全不依賴雲端，數據 100% 留在電腦", "bullets": ["Ollama 與 vLLM 高速推論引擎", "4-bit / 8-bit 量化顯存極限壓榨", "離線環境毫秒級極速回應"], "code": "$ ollama run deepseek-r1:8b\nLoaded to GPU VRAM: 4.8 GB"},
            {"title": "自動化防當機與常駐服務守護", "sub": "Systemd 與 Supervisor 背景無人維運", "bullets": ["進程異常重啟與自動心跳檢測", "崩潰日誌自動快照與告警推播", "平滑重啟 (Zero-Downtime Reload)"], "code": "$ systemctl status ai-studio-daemon\nActive: active (running) [24/7 OK]"},
            {"title": "多智能體協同 (Multi-Agent Swarm)", "sub": "專職專責！打造頂級 AI 虛擬專家團隊", "bullets": ["規劃者 (Planner) 制定整體策略", "執行者 (Coder) 專注產出高品質結果", "審查者 (Reviewer) 雙重驗證驗收"], "code": "[Agent Swarm]\nPlanner -> Coder -> Reviewer\nFinal Consensus: Approved (100%)"},
            {"title": "大規模批次生片排程系統", "sub": "一次生成數十部影片的高速管線", "bullets": ["佇列管理 (Queue System) 依序排程", "多核心 CPU 與硬體 GPU 加速編碼", "完成後自動重命名並分類歸檔"], "code": "$ batch-producer --queue video_jobs/\nProcessed: 12/12 Completed (100%)"},
            {"title": "高續播率與點閱率 (CTR) 實戰秘訣", "sub": "抓住眼球！讓 YouTube 演算法主動推薦", "bullets": ["前 3 秒黃金留存法則精準落實", "縮圖與標題的對比張力營造", "觀眾互動觸發點的策略性埋入"], "code": "[Audience Retention]\nTarget: > 65% at 30s\nAlgorithm Boost Factor: High"}
        ]
    else:
        # 💡 非程式主題專屬分鏡原型池 (生活、自媒體、思維、理財、時間管理等，嚴禁出現代碼與終端指令)
        stage_templates = [
            {
                "stage": "hook",
                "badge": "🎯 最終成效搶先看",
                "title_suffix": "：立竿見影的落地成效！",
                "subtitle": "開頭直接看成果！告別盲目摸索，建立高效實踐閉環",
                "bullets": [
                    "實戰成果搶先看：看見具體落地後的驚人改變",
                    "前後對比立竿見影：節省 80% 時間，產出翻倍",
                    "拒絕抽象空談：直接提供拿來就用的行動範本"
                ],
                "code_box": "【🎯 最終成效震撼對比】\n傳統摸索: 心力交瘁、進度卡關、成效零碎\n落地成果: 建立行動閉環，產出翻倍、掌握主動權！\n核心承諾: 前15秒直擊重點，學會立即可用",
                "narration_tpl": f"大家先看畫面上這個最終成果！透過這套方法落地後的具體成效，直接把過去幾個月的摸索成本徹底省下來！今天我們不講抽象的大道理，直接切入核心操作，帶你第一時間掌握這套立竿見影的實戰系統！"
            },
            {
                "stage": "concept",
                "badge": "⚡ 核心模型",
                "title_suffix": "：三大底層運作機制拆解",
                "subtitle": "從底層認知到行動閉環，建立清晰的實踐地圖",
                "bullets": [
                    "認知層：看清底層本質，不再被表象迷惑",
                    "策略層：設定優先順序，聚焦最高價值關鍵",
                    "行動層：建立最小可行習慣，每天持續推進"
                ],
                "code_box": "[實踐三要素]\n清晰認知 -> 聚焦槓桿點 -> 最小可行行動",
                "narration_tpl": f"要徹底做好「{clean_topic}」，關鍵不在於做更多事，而是做對最重要的核心環節。透過這套三大思維框架，釐清認知盲區、找出關鍵槓桿點，你就能用最少精力換取最大的成長！"
            },
            {
                "stage": "step1",
                "badge": "🌱 實戰第一步",
                "title_suffix": "：建立清晰起步基石",
                "subtitle": "從現狀盤點開始，設定具體可衡量的起點",
                "bullets": [
                    "自我盤點：找出目前卡關的核心瓶頸",
                    "降維門檻：設計 5 分鐘就能開始的微行動",
                    "正向反饋：即時看見進步，維持長期動力"
                ],
                "code_box": "💡 起步檢核清單 (Checklist):\n[✔] 明確當前最大瓶頸\n[✔] 設計最小啟動動作\n[✔] 排除環境干擾因素",
                "narration_tpl": "第一步非常關鍵，我們不需要一開始就給自己設定太龐大的目標，而是先進行現狀盤點，找出目前阻礙前進的最大瓶頸，並設計一個五分鐘內就能立即執行的微行動，輕鬆踏出第一步！"
            },
            {
                "stage": "step2",
                "badge": "🚀 實戰第二步",
                "title_suffix": "：建立持續運作的行動系統",
                "subtitle": "不靠短暫意志力，用機制驅動穩定產出",
                "bullets": [
                    "機制化設計：把行為綁定到日常生活節奏中",
                    "降低摩擦阻力：讓對的選擇變得最容易發生",
                    "定期覆盤調整：每週檢視並迭代行動策略"
                ],
                "code_box": "📌 系統運轉機制:\n日常觸發 -> 順暢執行 -> 即時反饋 -> 週覆盤迭代",
                "narration_tpl": "接下來是第二個核心環節：優秀的結果不是靠短暫的意志力，而是靠穩固的系統機制。我們把行動融入日常生活節奏，降低每一次執行的阻力，讓好習慣自然而然地持續發生！"
            },
            {
                "stage": "demo",
                "badge": "🎯 實例解析",
                "title_suffix": "：前後對比與真實成效",
                "subtitle": "前後差異一目了然，用對方法成效立竿見影",
                "bullets": [
                    "前後對比：從混亂摸索到井然有序",
                    "關鍵轉折點：做對了哪一項關鍵決定",
                    "長期複利：時間拉長後的指數級成長"
                ],
                "code_box": "【前後對比實錄】\n改善前: 精力分散、焦慮拖延、成效不彰\n改善後: 目標明確、節奏穩定、產出翻倍",
                "narration_tpl": "大家可以仔細看畫面上展示的前後對比！在還沒建立這套清晰架構前，往往容易感到疲憊且成效有限；而一旦掌握核心原則後，不僅做事更有餘裕，整體產出與成就感更迎來質的飛躍！"
            },
            {
                "stage": "tips",
                "badge": "💡 避坑指南",
                "title_suffix": "：新手最常踩的 3 個思維盲區",
                "subtitle": "避開這些隱形陷阱，讓前進速度再翻倍",
                "bullets": [
                    "盲區一：過度追求完美而遲遲不敢開始",
                    "盲區二：忽視微小進步導致中途放棄",
                    "盲區三：孤軍奮戰，缺少反饋與覆盤"
                ],
                "code_box": "⚠️ 避坑提醒 (Pitfalls to Avoid):\n- 完成比完美更重要 (Done is better than perfect)\n- 重視過程複利，不過度焦慮短期結果",
                "narration_tpl": "在這裡跟大家分享幾個最常見的盲區與誤區：很多人在實踐時，往往因為過度追求完美而不敢跨出第一步，或是因為短期內看不到巨大變化而過早放棄。記住，完成比完美更重要，持續微小進步才是王道！"
            },
            {
                "stage": "roi",
                "badge": "📊 成長複利",
                "title_suffix": "：長期堅持帶來的巨大質變",
                "subtitle": "每天進步 1%，一年後將成長 37 倍",
                "bullets": [
                    "時間複利：越早建立習慣，回報越大",
                    "認知提升：看待問題的維度徹底改變",
                    "生活掌控感：告別焦慮，重掌生活主動權"
                ],
                "code_box": "[複利成長公式]\n(1 + 0.01)^365 = 37.78 倍巨大提升！\n專注長期價值，享受時間的紅利",
                "narration_tpl": "我們來認真算一算這筆長期帳：每天只投入一點點心力落實核心原則，一年後產生的複利效應將是原本的 37 倍！當你掌握了這種底層邏輯，你不僅能搞定眼前挑戰，更獲得了重掌生活與工作主動權的底氣！"
            },
            {
                "stage": "cta",
                "badge": "🔔 精華總結",
                "title_suffix": "：本集複習與下集預告",
                "subtitle": "精華筆記與行動清單已整理在說明欄",
                "bullets": [
                    f"下集精彩預告：{next_topic_clean[:22]}",
                    "持續鎖定頻道，掌握更多實戰乾貨",
                    "記得按讚、訂閱、開啟小鈴鐺！"
                ],
                "code_box": f"感謝觀看！\n>>> Next Episode (下集預告):\n【{next_topic_clean}】\n精彩亮點: 核心方法深度拆解 | 立即實踐",
                "narration_tpl": f"以上就是今天的「{clean_topic}」完整精華分享！在下一集影片中，我們將帶來【{next_topic_clean}】的深度解析。本集的重點筆記與實踐清單都已經整理在下方說明欄。如果覺得有收穫，別忘了按讚、訂閱並開啟小鈴鐺，我們下期再見！"
            }
        ]
        curriculum_pool = [
            {"title": "核心痛點精準定位與根源分析", "sub": "跳脫表面現象，直接直擊底層關鍵", "bullets": ["運用五問法 (5 Whys) 挖掘真問題", "辨識假性需求與無效焦慮", "建立清晰的優先級篩選矩陣"], "code": "【根源分析矩陣】\n現象 -> 誘發因素 -> 底層核心因 -> 解決對策"},
            {"title": "能量與專注力的高效分配機制", "sub": "保護大腦黃金時段，告別疲勞耗損", "bullets": ["將高難度任務安排在精力巔峰期", "運用番茄鐘或時間塊杜絕干擾", "建立工作與休息的明確分界線"], "code": "💡 能量管理守則:\n上午: 核心攻堅 (90分鐘高專注)\n下午: 常規溝通與碎片處理"},
            {"title": "建立即時正向反饋與激勵系統", "sub": "告別三分鐘熱度，讓動力源源不絕", "bullets": ["可視化進度追蹤 (視覺化打卡)", "設定微小里程碑獎勵機制", "記錄每日微成就，累積自我效能感"], "code": "🎯 動力回饋機制:\n微小行動 -> 即時記錄 -> 成就反饋 -> 強化動力"},
            {"title": "環境阻力最小化與微習慣養成", "sub": "塑造助推環境，讓好習慣水到渠成", "bullets": ["減少目標行為的啟動阻力", "增加誘惑與干擾的摩擦成本", "兩分鐘定律：隨時隨地無負擔啟動"], "code": "📌 環境設計原則:\n- 想要做的事: 放在顯眼且伸手可得處\n- 想戒除的事: 增加阻力拉開物理距離"},
            {"title": "深度覆盤與迭代優化方法論", "sub": "做完不是結束，覆盤才能轉化為能力", "bullets": ["PDCA 循環：計畫-執行-檢視-調整", "每週 15 分鐘精煉覆盤三問", "保留成功經驗，汰除無效動作"], "code": "【精煉覆盤三問】\n1. 本週做對了什麼？\n2. 哪裡可以做得更好？\n3. 下週只改進哪一件事？"},
            {"title": "高價值輸出與認知內化飛輪", "sub": "以教為學 (費曼學習法)，徹底吸收", "bullets": ["用自己的話將核心概念說給別人聽", "產出結構化圖文或實踐筆記", "在實戰應用中檢視理解深度"], "code": "💡 費曼學習飛輪:\n吸收概念 -> 通俗輸出 -> 發現盲點 -> 簡化內化"},
            {"title": "長線思維與抗脆弱心理建設", "sub": "在不確定性中建立穩健的內心秩序", "bullets": ["接受波動：成長是非線性的", "建立心理安全邊際與備援方案", "將挫折重新定義為有價值的數據反饋"], "code": "🛡️ 抗脆弱心態:\n將意外與挑戰視為系統升級的養分\n保持靈活性，專注於自己能控制的事"},
            {"title": "建立個人知識庫與專屬資源庫", "sub": "把靈感與素材資產化，隨時調用", "bullets": ["模組化筆記：按標籤與主題分類", "快速檢索系統：30 秒內找到所需", "定期整理與連結新舊知識"], "code": "📚 知識資產化:\n收集素材 -> 提煉卡片 -> 網狀連結 -> 一鍵調用"},
            {"title": "高效溝通與協同共贏心法", "sub": "連結優質夥伴，放大個人成果與影響力", "bullets": ["結構化表達：結論先行，論據充分", "同理心傾聽：理解他人背後的真實訴求", "建立信任資產，實現長期雙贏"], "code": "🤝 共贏溝通原則:\n先聽懂對方 -> 站在對方利益思考 -> 創造增量價值"},
            {"title": "從執行者到策略者的思維躍遷", "sub": "用系統思考取代單點努力，放大槓桿", "bullets": ["識別系統中的正負反饋回路", "尋找阻力最小的關鍵槓桿解", "讓時間成為你的盟友而非敵人"], "code": "🚀 思維躍遷模型:\n單點努力 (算術級) -> 系統槓桿 (指數級)"}
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
        # 3分鐘：選取前序場景並確保最後一幕為 CTA (訂閱與下集預告)
        chosen_stages = stage_templates[:num_scenes - 1] + [stage_templates[7]]
    else:
        # 5~60分鐘：循環擴展不同專題深入探討步驟
        chosen_stages = list(stage_templates[:4])
        extra_count = num_scenes - 6  # 保留 2 個給成果與總結

        for i in range(extra_count):
            mod = curriculum_pool[i % len(curriculum_pool)]
            cycle = (i // len(curriculum_pool)) + 1
            idx = i + 5
            suffix = f"：{mod['title']}" + (f" (第{cycle}講)" if cycle > 1 else "")
            narration_text = (
                f"現在我們深入探討【{clean_topic}】的第 {idx} 個關鍵核心模組：{mod['title']}。在實際落地中，手動處理容易遭遇效能瓶頸或格式錯誤。透過我們設計的自動化檢驗機制，能確保所有環節穩定運作。大家跟著畫面設定，就能輕鬆掌握這套高效率工作流！"
                if is_code else
                f"現在我們深入探討【{clean_topic}】的第 {idx} 個關鍵核心模組：{mod['title']}。在許多人的日常實踐中，往往容易因為忽略了這個底層細節而遇到瓶頸。透過今天拆解的具體方法，能幫助你穩健落地，持續產出優質成果！"
            )
            chosen_stages.append({
                "stage": f"deep_dive_{idx}",
                "badge": f"🔍 深入探討 {idx:02d}",
                "title_suffix": suffix,
                "subtitle": mod["sub"],
                "bullets": mod["bullets"],
                "code_box": mod["code"],
                "narration_tpl": narration_text
            })

        chosen_stages.append(stage_templates[4])  # 成果示範
        chosen_stages.append(stage_templates[7])  # 總結與訂閱領取

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
        "scenes": scenes_output,
        "next_episode": next_info,
        "is_programming": is_code
    }

def _call_gemini_api(topic: str, plan: dict, style: str, api_key: str) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    from src.rubiks_cube_engine import is_rubiks_cube_topic
    is_rubik = is_rubiks_cube_topic(topic)
    is_code = False if is_rubik else is_programming_topic(topic)
    
    if is_rubik:
        constraint_note = (
            "【極其重要 - 魔術方塊專屬解法教學】：本片為魔術方塊解法教學，嚴禁任何 python/pip/終端機命令！"
            "請規劃完整的魔方七步還原法（底十字、第一層角塊、中層F2L、頂面十字、小魚OLL、頂層PLL六面全解）。"
            "highlight_box 請務必填寫該步驟對應的轉動口訣與公式（例如 R U R' U'、F R U R' U' F'、小魚公式等）。"
        )
    elif not is_code:
        constraint_note = (
            "【極其重要】：本片為【非程式主題】，嚴禁在腳本、highlight_box、旁白或任何欄位出現任何程式碼、終端機命令（如 $、pip、python、bash 等）。highlight_box 請填寫結構化精華筆記、清單、思考模型或前後對比圖。"
        )
    else:
        constraint_note = (
            "【程式實戰主題】：highlight_box 請填寫清晰簡潔的終端機指令、代碼原型或系統架構圖。"
        )

    retention_hook_rule = (
        "\n【黃金前 15~30 秒留存率法則（成果先行）】：\n"
        "第 1 個分鏡（開場 Hook）必須「成果先行」！嚴禁冗長的前置概念鋪陳或問候廢話。\n"
        "直接在第 1 幕展示「全自動工作流完成後的震撼成果」或「實際操作的即時畫面/前後對比」，讓觀眾在 15~30 秒內第一時間看見最高實用價值與期待感，極限拉高觀眾續看率！"
    )

    prompt = f"""你是一名頂級 YouTube 頻道爆款腳本架構師。
當前主題為：「{topic}」。
目標時長：{plan['duration_minutes']} 分鐘。
總共需要精確產生 {plan['num_scenes']} 個分鏡場景（Scene）。
{constraint_note}
{retention_hook_rule}
請以繁體中文 (台灣風格，如「哈囉大家好」、「這套方法」、「搞定」) 輸出合法的 JSON，不要包含任何 markdown 標籤或其餘贅字。
JSON 結構格式：
{{
  "title": "{topic}",
  "duration_minutes": {plan['duration_minutes']},
  "scenes": [
    {{
      "badge": "短標籤 (如：🔥 實機成果搶先看 / 🎯 最終成效展示)",
      "title": "大標題 (20字內，吸引人)",
      "subtitle": "副標題 (30字內)",
      "bullets": ["重點1", "重點2", "重點3"],
      "highlight_box": "畫面重點筆記框或架構圖 (多行純文字)",
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
    from src.rubiks_cube_engine import is_rubiks_cube_topic
    is_rubik = is_rubiks_cube_topic(topic)
    is_code = False if is_rubik else is_programming_topic(topic)
    if is_rubik:
        constraint = "注意：魔術方塊教學，嚴禁輸出任何程式碼或終端機指令，highlight_box 請填寫該步驟的魔方轉動公式與口訣（如 R U R' U'、小魚公式等）。"
    elif not is_code:
        constraint = "注意：非程式主題，嚴禁輸出任何程式碼、pip 或終端機指令，highlight_box 請填寫精華重點筆記與清單。"
    else:
        constraint = "提供技術實戰與終端機指令。"
    retention_rule = "【黃金前 15~30 秒成果先行】：第 1 幕嚴禁概念鋪陳，直接展示全自動完成後的震撼成果或前後對比，快速拉高續播率。"
    prompt = f"請為主題「{topic}」製作長度為 {plan['duration_minutes']} 分鐘、共 {plan['num_scenes']} 個場景的 YouTube 繁中腳本 JSON。{constraint} {retention_rule}"
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
