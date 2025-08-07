#!/bin/bash
# Streamlit Cloud의 빌드 환경에서 Playwright를 안정적으로 설치하기 위한 최종 스크립트

# -e: 명령 실패 시 즉시 중단
# -x: 실행되는 명령어를 로그에 출력
set -ex

# 1. 캐시 디렉토리를 직접 생성하고 모든 권한을 부여합니다.
# 이것이 권한 문제로 인한 설치 실패를 방지하는 가장 중요한 단계입니다.
mkdir -p /home/appuser/.cache/ms-playwright
chmod -R 777 /home/appuser/.cache

# 2. 브라우저 실행에 필요한 시스템 의존성 라이브러리를 먼저 설치합니다.
python3 -m playwright install-deps chromium

# 3. 라이브러리가 준비된 상태에서, 실제 브라우저 실행 파일을 다운로드합니다.
python3 -m playwright install chromium

# 4. 설치가 성공했는지 확인하기 위해, 설치된 모든 파일 목록을 로그에 상세히 출력합니다.
echo "--- Playwright browser installation verification ---"
ls -lR /home/appuser/.cache/ms-playwright/
echo "--- setup.sh finished successfully ---"
