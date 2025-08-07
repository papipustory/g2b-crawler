import streamlit as st
import pandas as pd
import io
import os
import subprocess
import sys
import glob
from contextlib import redirect_stdout

# Streamlit Cloud에서 쓰기 가능한 임시 브라우저 경로
BROWSER_PATH = "/tmp/playwright-browsers"

@st.cache_resource(show_spinner="브라우저 준비 중입니다...")
def install_and_get_browser():
    """Cloud 환경 내에서 Playwright 크롬 설치 및 경로 반환"""
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = BROWSER_PATH
    executable_path_glob = os.path.join(BROWSER_PATH, "chromium-*", "chrome-linux", "chrome")
    found_paths = glob.glob(executable_path_glob)
    if found_paths:
        return found_paths[0]
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            capture_output=True,
            text=True
        )
        found_paths = glob.glob(executable_path_glob)
        if found_paths:
            return found_paths[0]
        else:
            st.error("브라우저 설치는 완료되었으나 실행 파일이 없습니다.")
            return None
    except subprocess.CalledProcessError as e:
        st.error("브라우저 설치에 실패했습니다.")
        return None
    except Exception as e:
        st.error(f"알 수 없는 오류 발생: {e}")
        return None

# --- 앱 시작 ---
st.set_page_config(
    page_title="나라장터 제안공고 크롤러",
    page_icon="🏛️",
    layout="centered"
)

st.markdown(
    """
    <style>
    .main-title {font-size:2.2rem; font-weight:600;}
    .subtitle {font-size:1.1rem; color:#555;}
    .result-table .stDataFrame {margin-top:1rem;}
    .stButton>button {font-size:1.1rem;}
    </style>
    """,
    unsafe_allow_html=True
)

# --- 브라우저 준비 ---
browser_executable_path = install_and_get_browser()
if not browser_executable_path:
    st.error("브라우저를 준비할 수 없어 앱을 실행할 수 없습니다.\n페이지를 새로고침해 주세요.")
    st.stop()

from g2b_crawler import run_g2b_crawler

# --- 헤더 영역 ---
st.markdown('<div class="main-title">🏛️ 나라장터 제안공고 크롤러</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">나라장터 조달청 제안공고 데이터를 쉽고 빠르게 수집·분석할 수 있습니다.<br>검색어 입력 → 크롤링 시작 → 표/다운로드 지원!</div>',
    unsafe_allow_html=True,
)
st.markdown("---")

# --- 사이드바: 디버그 토글 ---
with st.sidebar:
    st.header("⚙️ 고급 설정 & 로그")
    show_debug = st.toggle("디버그 로그 보기", value=False, help="개발자/운영자용. 일반 사용자는 끌 것!")
    st.info("공고 데이터는 검색어 기준으로 1분 이내 빠르게 수집됩니다.")

# --- 메인 검색 영역 ---
with st.form(key="search_form", clear_on_submit=False):
    search_query = st.text_input("🔎 검색어", value="컴퓨터", help="공고명, 품목명 등 키워드")
    submitted = st.form_submit_button("크롤링 시작")

if submitted:
    status_area = st.empty()
    log_capture = io.StringIO()
    try:
        status_area.info(f"🔄 <b>'{search_query}'</b> 검색 중입니다... 잠시만 기다려주세요.", unsafe_allow_html=True)

        with redirect_stdout(log_capture):
            # 동적으로 찾은 브라우저 경로를 전달
            result = run_g2b_crawler(search_query, browser_executable_path)

        log_output = log_capture.getvalue()

        if result and result[1]:
            header, table_data = result
            df = pd.DataFrame(table_data, columns=header)
            status_area.success(f"✅ {len(df)}개의 제안공고를 찾았습니다!")
            st.markdown("**검색 결과**")
            st.dataframe(df, use_container_width=True, height=min(520, 50+len(df)*34))

            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="📥 결과 CSV 다운로드",
                data=csv,
                file_name=f"g2b_{search_query}.csv",
                mime="text/csv"
            )

            # 디버그 로그(선택적 표시)
            if show_debug:
                with st.expander("🪛 디버그 로그(운영자용)"):
                    st.code(log_output or "(로그 없음)", language="text")
        else:
            status_area.error("❌ 검색 결과가 없거나 크롤링 실패")
            if show_debug:
                with st.expander("🪛 디버그 로그(운영자용)"):
                    st.code(log_output or "(로그 없음)", language="text")
            else:
                st.info("💡 <b>상세 로그를 보려면 사이드바에서 '디버그 로그 보기'를 켜주세요.</b>", unsafe_allow_html=True)

    except Exception as e:
        status_area.error(f"❌ 오류 발생: {str(e)}")
        if show_debug:
            with st.expander("🪛 디버그 로그(운영자용)"):
                st.code(log_capture.getvalue() or "(로그 없음)", language="text")
        with st.expander("오류 상세"):
            st.code(str(e))

else:
    st.info(
        "1. 검색어를 입력하고 [크롤링 시작]을 클릭하세요.<br>"
        "2. 1분 내외로 공고 데이터가 표로 출력됩니다.<br>"
        "3. CSV 다운로드로 엑셀 연동도 OK!",
        icon="📝"
    )

st.markdown("---")
st.caption("© 2025 위더스컴퓨터 · powered by Playwright · for 나라장터 제안공고 수집 자동화")

