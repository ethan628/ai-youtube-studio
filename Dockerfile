FROM python:3.11-slim

# 安裝 FFmpeg 與中文字型 (思源黑體)，確保影片與字型正常渲染
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-noto-cjk \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安裝 Python 相依套件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案代碼
COPY . .

# 建立所需目錄
RUN mkdir -p output_videos voice_samples inputs_notebooklm

EXPOSE 8501

CMD ["python", "web_ui.py"]
