import streamlit as st
import asyncio
import os
import subprocess
import sys

# 페이지 설정을 맨 처음에
st.set_page_config(page_title="나라장터 제안공고 크롤러", layout="centered")

# Playwright 브라우저 설치 함수
@st.cache_resource
def ensure_playwright_installed():
    """Playwright 브라우저가 설치되어 있는지 확인하고 필요시 설치"""
    try:
        # Playwright 설치 상태 확인
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            st.success("✅ Playwright 브라우저 설치 완료")
            return True
        else:
            st.error(f"❌ Playwright 설치 실패: {result.stderr}")
            return False
    except Exception as e:
        st.error(f"❌ Playwright 설치 중 오류: {str(e)}")
        return False

# Playwright 설치 확인
with st.spinner("🔧 Playwright 브라우저 설정 중..."):
    if not ensure_playwright_installed():
        st.stop()

# 이제 main 함수 import
from streamlit_g2b_crawler import main

# UI 구성
st.title("💻 나라장터 제안공고 크롤러")
st.caption("컴퓨터 관련 제안공고를 G2B에서 크롤링하여 다운로드합니다.")

# 실행 버튼
if st.button("📦 크롤링 시작", type="primary"):
    # 진행 상태 표시
    progress_placeholder = st.empty()
    status_placeholder = st.empty()
    
    progress_placeholder.progress(0.1)
    status_placeholder.info("🌐 나라장터 사이트 접속 중...")
    
    try:
        # asyncio 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 크롤링 실행
        loop.run_until_complete(main())
        
        progress_placeholder.progress(1.0)
        status_placeholder.success("✅ 크롤링이 완료되었습니다!")
        
    except Exception as e:
        progress_placeholder.empty()
        status_placeholder.error(f"❌ 크롤링 중 오류 발생: {str(e)}")
        
        # 디버깅을 위한 상세 오류 표시
        with st.expander("🔍 상세 오류 정보"):
            st.code(str(e))
            import traceback
            st.code(traceback.format_exc())
    
    finally:
        # 진행 표시 정리
        progress_placeholder.empty()

# 결과 파일 다운로드
if os.path.exists("g2b_result.xlsx"):
    st.divider()
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.success("📊 크롤링 결과 파일이 준비되었습니다.")
    
    with col2:
        with open("g2b_result.xlsx", "rb") as file:
            st.download_button(
                label="📥 다운로드",
                data=file,
                file_name="g2b_result.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
