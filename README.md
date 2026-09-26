# 🎬 AI YouTube 影片全自動生成工作台

專為你的頻道風格（**雙AI協同開發 / 三大AI / 不寫程式搞定實戰**）打造的 **100% 免費、免 API Key、全自動 YouTube 影片生成系統**！

---

## 📁 統一存放目錄
所有產出的成品影片，均統一存放在：
```
d:\ethan\自動做yt\output_videos\
```

---

## ⚡ 三種使用方式

### 方式 1：雙擊執行網頁操作介面 (推薦 ⭐⭐⭐⭐⭐)
在資料夾中雙擊 **`啟動工作台.bat`**（或執行 `python web_ui.py`）：
1. 瀏覽器會自動開啟 `http://127.0.0.1:8501`。
2. 可以在介面上挑選模板、選擇比例（16:9 長片 或 9:16 Shorts 短影音）、選擇男聲或女聲。
3. 點擊「開始全自動生成影片」，生成後直接在網頁上 **線上播放預覽、下載** 或 **一鍵開啟檔案資料夾**！

---

### 方式 2：Google NotebookLM 轉 1080p Podcast 影片
Google NotebookLM 可免費生成超擬真的雙主持 AI 對談語音（Audio Overview）。本系統能自動將其轉為高質感影片：
1. 到 [Google NotebookLM](https://notebooklm.google.com) 產生音訊並下載（`.m4a` 或 `.mp3`）。
2. 將音訊檔案放進 `inputs_notebooklm/` 資料夾。
3. 執行指令：
   ```bash
   python notebooklm_to_video.py --title "你的專題標題" --subtitle "副標題"
   ```
4. 系統會自動繪製科技對談背景、雙 AI 主持人狀態卡、並加入**跟隨聲音跳動的即時動態音波（Waveform）**，輸出 1080p MP4 影片至 `output_videos/`！

---

### 方式 3：命令列一鍵快速生成
- **生成 16:9 長影片（預設模板 1）：**
  ```bash
  python create_video.py --template 1
  ```
- **生成 9:16 Shorts 短影音（預設模板 2）：**
  ```bash
  python create_video.py --template 2 --shorts
  ```
- **更換配音角色為台灣自然女聲：**
  ```bash
  python create_video.py --template 1 --voice zh-TW-HsiaoChenNeural
  ```

---

## 🛠️ 系統特色與核心技術
1. **100% 完全免費**：不需要購買任何昂貴的影片生成會員或 OpenAI API Key。
2. **微軟高音質神經語音 (Edge-TTS)**：自動生成自然流暢的台灣繁體中文發音（男聲 YunJhe / 女聲 HsiaoChen）。
3. **精準字幕自動對齊與燒錄**：毫秒級時間戳，自動燒錄高對比微軟正黑體黃白字幕，手機電腦皆清晰。
4. **高質感科技感視覺卡片**：深色賽博龐克風格、格線、代碼視窗與亮點數字卡片，完美契合頻道受眾喜好。
