# =========================
# Iprime-Bot Dockerfile
# Discord Bot + yt-dlp + ffmpeg
# =========================

FROM python:3.11-slim

# ---- SYSTEM DEPENDENCIES ----
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ---- WORKDIR ----
WORKDIR /app

# ---- COPY FILES ----
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ---- ENV ----
ENV PYTHONUNBUFFERED=1

# ---- EXPOSE (Koyeb health check) ----
EXPOSE 8000

# ---- RUN BOT ----
CMD ["python", "bot.py"]
