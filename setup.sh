#!/bin/bash

# 디버깅을 위한 로그
echo "Starting setup script..."

# Streamlit Cloud 환경 변수 설정
export PLAYWRIGHT_BROWSERS_PATH=/home/appuser/.cache/ms-playwright
export DEBIAN_FRONTEND=noninteractive

# 필수 패키지 설치
echo "Installing system packages..."
apt-get update -qq
apt-get install -y -qq wget gnupg ca-certificates

# Playwright 설치 전 필수 의존성
echo "Installing Playwright dependencies..."
apt-get install -y -qq \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libatspi2.0-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libxcb1 \
    libxkbcommon0 \
    libgtk-3-0 \
    libpango-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libasound2

# 디렉토리 생성 및 권한 설정
echo "Setting up directories..."
mkdir -p /home/appuser/.cache/ms-playwright
chmod -R 777 /home/appuser/.cache

# Playwright 브라우저 설치
echo "Installing Playwright browsers..."
python -m playwright install chromium --with-deps

# 설치 확인
echo "Verifying installation..."
python -m playwright install --help

echo "Setup completed successfully!"
