#!/bin/bash
# 최종 단순화 버전: 이 스크립트는 오직 시스템 의존성 설치만 책임집니다.
set -ex
echo "--- [setup.sh] Installing system dependencies for Chromium ---"
python3 -m playwright install-deps chromium
echo "--- [setup.sh] Finished installing system dependencies ---"
