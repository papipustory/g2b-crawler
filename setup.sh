#!/bin/bash
# Streamlit Cloud 환경을 위한 Playwright 설정
export PLAYWRIGHT_BROWSERS_PATH=/tmp
playwright install chromium --with-deps
