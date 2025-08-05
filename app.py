import streamlit as st
import asyncio
import os
import subprocess
import sys

# Playwright 설치 확인 및 설치
@st.cache_resource
def install_playwright():
    try:
        # Playwright 브라우저 설치
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        return True
    except Exception as e:
        st.error(f"Playwright 설치 실패: {e}")
        return False

# streamlit_g2b_crawler에서 main 함수 import
from streamlit_g2b_crawler import main

# Streamlit 페이지 설정
st.set_page_config(page_title="나라장터 제안공고 크롤러", layout="centered")
st.title("💻 나라장터 제안공고 크롤러")
st.caption("컴퓨터 관련 제안공고를 G2B에서 크롤링하여 다운로드합니다.")

# Playwright 설치 확인
if not install_playwright():
    st.stop()

# 상태 표시 UI 요소
progress_bar = st.empty()
status = st.empty()

# 실행 버튼
if st.button("📦 크롤링 시작"):
    st.info("Playwright 크롤링을 실행 중입니다. 잠시 기다려 주세요.")
    progress_bar.progress(5)
    status.text("브라우저 시작 중...")

    try:
        # asyncio 실행 방식 수정
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
        
        progress_bar.progress(100)
        st.success("✅ 크롤링 완료")
    except Exception as e:
        st.error(f"❌ 에러 발생: {e}")
        st.error(f"상세 에러: {type(e).__name__}")
        import traceback
        st.code(traceback.format_exc())
    finally:
        progress_bar.empty()
        status.empty()

# 다운로드 버튼 (결과 파일 존재 시)
if os.path.exists("g2b_result.xlsx"):
    with open("g2b_result.xlsx", "rb") as f:
        st.download_button(
            label="📥 크롤링 결과 다운로드",
            data=f,
            file_name="g2b_result.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
