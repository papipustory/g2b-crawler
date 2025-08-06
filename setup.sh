#!/bin/bash
set -e

echo "========================================="
echo "Starting Streamlit Cloud Setup"
echo "========================================="

# 환경 변수 설정
export PLAYWRIGHT_BROWSERS_PATH=/tmp/playwright-browsers
export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0

# Playwright 브라우저 설치
echo "Installing Playwright browsers..."
python -m playwright install chromium --with-deps

# 권한 설정
echo "Setting permissions..."
chmod -R 755 /tmp/playwright-browsers 2>/dev/null || true

echo "========================================="
echo "Setup completed successfully!"
echo "========================================="
