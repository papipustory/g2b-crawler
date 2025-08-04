#!/bin/bash

# Streamlit Cloud가 빌드 단계에서 이 스크립트를 실행합니다.
# Playwright가 사용하는 브라우저 바이너리를 설치합니다.
# 여기서는 크롤러에 필요한 Chromium만 설치합니다.

playwright install chromium
