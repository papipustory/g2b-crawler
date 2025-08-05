#!/bin/bash
echo "===== Streamlit Cloud Setup Start ====="

# 1. 패키지 목록 업데이트
echo "[INFO] Updating package list..."
apt-get update -qq

# 2. Playwright 및 Chromium 실행에 필요한 시스템 라이브러리 설치
echo "[INFO] Installing system dependencies..."
apt-get install -y -qq \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgdk-pixbuf2.0-0 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    libxshmfence1 \
    xdg-utils

# 3. APT 캐시 정리
echo "[INFO] Cleaning APT cache..."
apt-get clean
rm -rf /var/lib/apt/lists/*

# 4. Playwright 캐시 디렉토리 생성
echo "[INFO] Creating Playwright cache directory..."
mkdir -p ~/.cache/ms-playwright

# 5. Playwright 브라우저 실행에 필요한 의존성 설치
echo "[INFO] Installing Playwright dependencies..."
python -m playwright install-deps chromium || {
    echo "[ERROR] playwright install-deps failed"
    exit 1
}

# 6. Chromium 브라우저 설치
echo "[INFO] Installing Chromium browser..."
python -m playwright install chromium || {
    echo "[ERROR] playwright install chromium failed"
    exit 1
}

echo "===== Streamlit Cloud Setup Completed Successfully ====="
