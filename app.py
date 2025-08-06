import streamlit as st
import pandas as pd
import subprocess
import sys
import io
from contextlib import redirect_stdout

# Playwright 브라우저 설치 확인 함수
@st.cache_resource
def install_playwright():
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return True
        else:
            st.error(f"Playwright 설치 실패: {result.stderr}")
            return False
    except Exception as e:
        st.error(f"Playwright 설치 중 오류: {e}")
        return False

# 앱 시작 시 Playwright 설치
if 'playwright_installed' not in st.session_state:
    with st.spinner("Playwright 브라우저 설치 중... (첫 실행 시에만 필요)"):
        st.session_state.playwright_installed = install_playwright()

# 크롤러 import
if st.session_state.get('playwright_installed', False):
    from g2b_crawler import run_g2b_crawler, get_server_country, test_site_access
else:
    st.error("Playwright가 설치되지 않았습니다. 페이지를 새로고침해주세요.")
    st.stop()

st.title("🏛️ 나라장터 제안공고 크롤러")
st.markdown("---")

with st.sidebar:
    st.header("🔍 디버그 로그")
    debug_container = st.container()
    # 서버 위치 안내
    ip, country, org = get_server_country()
    st.write(f"서버 위치: {country or '알수없음'} | IP: {ip or '-'}")
    st.write(f"네트워크: {org or '-'}")
    # 사이트 접근 진단
    ok, access_msg = test_site_access("https://shop.g2b.go.kr/")
    if ok:
        st.success("나라장터 접근 진단: 정상")
    else:
        st.error(f"나라장터 접근 진단: 차단됨\n{access_msg}")

search_query = st.text_input("검색어를 입력하세요", value="컴퓨터")

if st.button("🔍 크롤링 시작"):
    status_placeholder = st.empty()
    log_capture = io.StringIO()
    try:
        status_placeholder.info(f"'{search_query}' 검색 중... (최대 1분 소요)")

        # stdout 캡처(크롤러 로그 표시)
        with redirect_stdout(log_capture):
            result = run_g2b_crawler(search_query)

        # 캡처된 로그를 사이드바에 표시
        log_output = log_capture.getvalue()
        with debug_container:
            st.code(log_output, language='text')

        if result and result[1]:  # (headers, data)
            header, table_data = result
            df = pd.DataFrame(table_data, columns=header)
            status_placeholder.success(f"✅ {len(df)}개의 공고를 찾았습니다!")
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
            status_placeholder.error("❌ 검색 결과가 없거나 크롤링 실패")
            st.info("💡 왼쪽 사이드바의 디버그 로그를 확인하세요")

    except Exception as e:
        status_placeholder.error(f"❌ 오류 발생: {str(e)}")
        log_output = log_capture.getvalue()
        with debug_container:
            st.code(log_output, language='text')
        with st.expander("오류 상세"):
            st.code(str(e))
