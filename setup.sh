#!/bin/bash
# 빌드/실행 환경 분리 문제를 해결하기 위한 최종 스크립트
set -ex

# 1. 브라우저를 프로젝트 폴더 내의 'pw-browsers'에 설치하도록 환경 변수를 설정합니다.
# 이렇게 하면 브라우저가 앱 코드와 함께 실행 환경으로 복사됩니다.
export PLAYWRIGHT_BROWSERS_PATH=$(pwd)/pw-browsers

# 2. 시스템 의존성 라이브러리를 설치합니다.
python3 -m playwright install-deps chromium

# 3. 실제 브라우저를 위에서 지정한 로컬 경로에 설치합니다.
python3 -m playwright install chromium

# 4. 로컬 경로에 설치가 성공했는지 모든 파일 목록을 출력하여 확인합니다.
echo "--- Verifying local browser installation ---"
ls -lR ./pw-browsers
echo "--- setup.sh finished successfully ---"
