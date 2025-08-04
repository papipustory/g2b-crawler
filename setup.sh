#!/bin/bash

# Streamlit Cloud 환경 설정
export PLAYWRIGHT_BROWSERS_PATH=/home/appuser/.cache/ms-playwright
export DEBIAN_FRONTEND=noninteractive

# 시스템 업데이트 및 필수 패키지 설치
apt-get update
apt-get install -y wget gnupg

# Playwright 브라우저 설치
echo "Installing Playwright browsers..."
python -m playwright install chromium
python -m playwright install-deps chromium

# 권한 설정
chmod -R 755 /home/appuser/.cache/ms-playwright

echo "Setup completed successfully!"
