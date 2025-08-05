#!/bin/bash
echo "Starting Playwright setup..."

# Playwright 브라우저 설치
python -m playwright install chromium
python -m playwright install-deps chromium

echo "Playwright setup completed!"
