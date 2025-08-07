#!/bin/bash
# 이 스크립트는 Playwright 브라우저 설치의 성공 여부를 결정하는 가장 중요한 파일입니다.
# set -e: 어떤 명령어라도 실패하면 즉시 스크립트를 중단하고 오류를 보고합니다.
set -e

echo "--- [setup.sh] 스크립트 실행 시작 ---"

# Playwright의 Chromium 브라우저를 설치합니다.
echo "--- [setup.sh] 'playwright install chromium' 명령어 실행 ---"
python3 -m playwright install chromium
echo "--- [setup.sh] 'playwright install chromium' 명령어 실행 완료 ---"

# 설치가 정말로 완료되었는지 확인하기 위해, 설치된 디렉토리 내용을 로그에 출력합니다.
echo "--- [setup.sh] 브라우저 설치 경로 확인 ---"
ls -l /home/appuser/.cache/ms-playwright/
echo "--- [setup.sh] 스크립트 성공적으로 종료 ---"
