#!/bin/bash
set -ex

# Playwright 브라우저 실행에 필요한 시스템 라이브러리를 설치합니다.
# 이것이 브라우저 실행 파일 자체를 다운로드하는 것보다 선행되어야 할 수 있습니다.
python3 -m playwright install-deps chromium
