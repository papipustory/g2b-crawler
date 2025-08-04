
#!/bin/bash
apt-get update
apt-get install -y wget unzip curl

# 필요한 시스템 패키지 설치
xargs -r -a packages.txt apt-get install -y

# Python 패키지 설치
pip install --upgrade pip
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install chromium
