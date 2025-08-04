#!/bin/bash
apt-get update && apt-get install -y libnss3 libnspr4 libatk-bridge2.0-0 \
libdrm2 libgtk-3-0 libgbm1 libasound2 libxss1 libxrandr2 libu2f-udev \
libvulkan1 xvfb fonts-liberation libappindicator3-1 libgconf-2-4 \
libatk1.0-0 libcups2 libpango-1.0-0 libcairo2 libdbus-1-3

# playwright 브라우저 설치
playwright install chromium
