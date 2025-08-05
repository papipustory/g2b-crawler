#!/bin/bash
echo "Starting setup..."

apt-get update -qq && \
apt-get install -y -qq wget gnupg ca-certificates fonts-liberation libasound2 \
libatk-bridge2.0-0 libatk1.0-0 libatspi2.0-0 libcairo2 libcups2 libdbus-1-3 \
libdrm2 libgbm1 libgdk-pixbuf2.0-0 libglib2.0-0 libgtk-3-0 libnspr4 libnss3 \
libpango-1.0-0 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxdamage1 libxext6 \
libxfixes3 libxkbcommon0 libxrandr2 libxshmfence1 xdg-utils

# Clean APT cache
apt-get clean && rm -rf /var/lib/apt/lists/*

# Ensure playwright cache dir exists
mkdir -p ~/.cache/ms-playwright

# Install Playwright dependencies
python -m playwright install-deps chromium

# Install Chromium browser
python -m playwright install chromium
