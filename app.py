import streamlit as st
import pandas as pd
import io
import os
import sys
from contextlib import redirect_stdout
from playwright.sync_api import sync_playwright, Error

# --- Playwright 브라우저 설치 로직 (Streamlit Cloud 최종 버전) ---
@st.cache_resource(show_spinner="브라우저 설정 확인 중...")
def install_playwright_browser():
    """
    Streamlit Cloud 환경에서 Playwright 브라우저가 존재하는지 확인하고,
    없으면 설치합니다. subprocess 대신 동기 API를 사용합니다.
    """
    # Playwright의 캐시 디렉토리 경로를 확인합니다.
    pw_path = os.path.join(os.path.expanduser("~"), ".cache", "ms-playwright")
    browser_path = os.path.join(pw_path, "chromium-1091", "chrome-linux", "chrome") # 정확한 버전을 명시

    # 브라우저 실행 파일이 있는지 직접 확인합니다.
    if not os.path.exists(browser_path):
        st.info("Chromium 브라우저가 설치되어 있지 않습니다. 설치를 시작합니다.")
        st.warning("설치에는 1-2분 정도 소요될 수 있습니다. 잠시만 기다려주세요.")
        
        # 동기 API를 사용하여 브라우저를 설치합니다.
        try:
            with sync_playwright() as p:
                # p.chromium.launch()를 시도하면 자동으로 브라우저를 다운로드합니다.
                # 이것이 subprocess를 호출하는 것보다 훨씬 안정적입니다.
                browser = p.chromium.launch(headless=True)
                browser.close()
            
            # 설치가 완료되었는지 다시 확인
            if os.path.exists(browser_path):
                st.success("브라우저 설치가 완료되었습니다!")
                st.balloons()
                return True
            else:
                # 이 경우는 거의 없지만, 만약을 대비한 방어 코드
                st.error("설치를 시도했지만 브라우저를 찾을 수 없습니다. 앱을 재부팅해주세요.")
                return False
        except Error as e:
            st.error(f"Playwright 브라우저 설치 중 오류 발생: {e}")
            st.info("자세한 내용은 아래 오류 메시지를 확인하세요.")
            st.code(str(e.message))
            return False
    else:
        # 이미 설치된 경우
        return True

# --- 앱 시작 ---
playwright_installed = install_playwright_browser()

if playwright_installed:
    from g2b_crawler import run_g2b_crawler
else:
    st.error("Playwright 브라우저가 준비되지 않았습니다. 페이지를 새로고침하여 다시 시도해주세요.")
    st.stop()

st.title("🏛️ 나라장터 제안공고 크롤러")
st.markdown("---")

with st.sidebar:
    st.header("🔍 디버그 로그")
    debug_container = st.container()

search_query = st.text_input("검색어를 입력하세요", value="컴퓨터")

if st.button("🔍 크롤링 시작"):
    status_placeholder = st.empty()
    log_capture = io.StringIO()
    try:
        status_placeholder.info(f"'{search_query}' 검색 중... (최대 1분 소요)")

        with redirect_stdout(log_capture):
            result = run_g2b_crawler(search_query)

        log_output = log_capture.getvalue()
        with debug_container:
            st.code(log_output, language='text')

        if result and result[1]:  # (headers, data)
            header, table_data = result
            df = pd.DataFrame(table_data, columns=header)
            status_placeholder.success(f"✅ {len(df)}개의 공고를 찾았습니다!")
            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "📥 CSV 다운로드",
                csv,
                file_name=f"g2b_{search_query}.csv",
                mime="text/csv"
            )
        else:
            status_placeholder.error("❌ 검색 결과가 없거나 크롤링 실패")
            st.info("💡 왼쪽 사이드바의 디버그 로그를 확인하세요")

    except Exception as e:
        status_placeholder.error(f"❌ 오류 발생: {str(e)}")
        log_output = log_capture.getvalue()
        with debug_container:
            st.code(log_output, language='text')
        with st.expander("오류 상세"):
            st.code(str(e))
