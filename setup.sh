#!/bin/bash
# Playwright 브라우저 설치
# install-deps는 packages.txt로 대체되므로, 브라우저만 설치합니다.
set -e
echo "--- Installing Playwright browser ---"
python -m playwright install chromium
echo "--- Playwright browser installation finished ---"
