import streamlit as st
import pandas as pd
import subprocess
import sys
import os

# Playwright 브라우저 설치 확인
@st.cache_resource
def install_playwright():
    """Playwright 브라우저 자동 설치"""
    try:
        # Playwright 브라우저 설치
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], 
                      check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        st.error(f"Playwright 설치 실패: {e}")
        return False

# 앱 시작 시 Playwright 설치
if 'playwright_installed' not in st.session_state:
    with st.spinner("Playwright 브라우저 설치 중... (첫 실행 시에만 필요)"):
        st.session_state.playwright_installed = install_playwright()

# 크롤러 import는 Playwright 설치 후에
if st.session_state.get('playwright_installed', False):
    from g2b_crawler_with_status import run_g2b_crawler
else:
    st.error("Playwright가 설치되지 않았습니다. 페이지를 새로고침해주세요.")
    st.stop()

# 앱 UI
st.title("🏛️ 나라장터 제안공고 크롤러")

# 검색어 입력
search_query = st.text_input("검색어를 입력하세요", value="컴퓨터")

# 크롤링 실행 버튼
if st.button("🔍 크롤링 시작"):
    # 진행 상황 표시 컨테이너
    progress_container = st.container()
    status_placeholder = st.empty()
    
    # 진행 상황 업데이트 함수
    def update_status(step, message):
        status_placeholder.info(f"**단계 {step}**: {message}")
    
    try:
        # 크롤링 실행 (상태 업데이트 함수 전달)
        result = run_g2b_crawler(search_query, update_status)
        
        if result:
            header, table_data = result
            df = pd.DataFrame(table_data, columns=header)
            
            status_placeholder.success(f"✅ 크롤링 완료! {len(df)}개의 공고를 찾았습니다!")
            st.dataframe(df, use_container_width=True)
            
            # CSV 다운로드
            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "📥 CSV 다운로드",
                csv,
                file_name=f"g2b_{search_query}.csv",
                mime="text/csv"
            )
        else:
            status_placeholder.warning("⚠️ 검색 결과가 없습니다.")
            
    except Exception as e:
        status_placeholder.error(f"❌ 크롤링 오류: {str(e)}")
        with st.expander("오류 상세"):
            st.code(str(e))
