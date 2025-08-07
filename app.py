import streamlit as st
import pandas as pd
import io
import os
import subprocess
import sys
import glob
import traceback

# ----- 브라우저 설치 및 경로 추출 -----
BROWSER_PATH = "/tmp/playwright-browsers"

@st.cache_resource(show_spinner="브라우저를 설정하고 있습니다...")
def install_and_get_browser():
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = BROWSER_PATH
    executable_path_glob = os.path.join(BROWSER_PATH, "chromium-*", "chrome-linux", "chrome")
    found_paths = glob.glob(executable_path_glob)
    if found_paths:
        return found_paths[0]
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True, capture_output=True, text=True
        )
        found_paths = glob.glob(executable_path_glob)
        if found_paths:
            return found_paths[0]
        else:
            st.error("브라우저를 설치했지만 실행 파일을 찾을 수 없습니다.")
            return None
    except subprocess.CalledProcessError as e:
        st.error("브라우저 설치에 실패했습니다.")
        st.code(f"Return code: {e.returncode}\nStdout: {e.stdout}\nStderr: {e.stderr}")
        return None
    except Exception as e:
        st.error(f"알 수 없는 오류 발생: {e}")
        return None

# --- G2B 크롤러 임포트 ---
browser_executable_path = install_and_get_browser()
if browser_executable_path:
    from g2b_crawler import run_g2b_crawler
else:
    st.error("브라우저를 준비할 수 없어 앱을 실행할 수 없습니다. 페이지를 새로고침하거나 로그를 확인하세요.")
    st.stop()

# ====== UI 시작 ======
st.markdown("""
    <style>
    .stDownloadButton button {
        height: 2.6em !important;
        font-size: 1.1em !important;
    }
    .stDataFrame { border-radius: 18px; }
    </style>
""", unsafe_allow_html=True)

st.markdown("## 🏛️ 나라장터 제안공고 크롤러")
st.markdown(
    '<div style="color:#888;font-size:15px;margin-bottom:16px;">검색어를 입력하면 나라장터(조달청) 제안공고를 신속하게 수집합니다.</div>',
    unsafe_allow_html=True
)

# ───── 검색 영역 ─────
with st.form("search_form", clear_on_submit=False):
    st.markdown("#### 🔍 검색어")
    col1, col2 = st.columns([6,1])
    with col1:
        search_query = st.text_input("", value="컴퓨터", label_visibility="collapsed")
    with col2:
        submit = st.form_submit_button("크롤링 시작", use_container_width=True)

status_placeholder = st.empty()
result_placeholder = st.empty()
error_placeholder = st.empty()

if submit:
    status_placeholder.info("⏳ <b>검색 중입니다... 잠시만 기다려주세요.</b>", icon="🔎", unsafe_allow_html=True)
    error_placeholder.empty()
    result_placeholder.empty()
    try:
        # --- 크롤러 실행 (원본 그대로) ---
        result = run_g2b_crawler(search_query, browser_executable_path)
        if result and result[1]:
            header, table_data = result
            df = pd.DataFrame(table_data, columns=header)
            status_placeholder.empty()
            error_placeholder.empty()
            with result_placeholder:
                st.success(f"✅ <b>{len(df):,}개</b>의 공고를 찾았습니다!", icon="✅", unsafe_allow_html=True)
                st.dataframe(
                    df, 
                    use_container_width=True, 
                    height=min(820, 70 + 34*min(len(df), 20))
                )
                csv = df.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "📥 CSV 다운로드", csv,
                    file_name=f"g2b_{search_query}.csv", mime="text/csv"
                )
        else:
            status_placeholder.empty()
            result_placeholder.empty()
            error_placeholder.error(
                "❌ <b>검색 결과가 없거나 크롤링에 실패했습니다.</b><br>검색어를 바꿔 시도해보세요.",
                icon="❌", unsafe_allow_html=True
            )
    except Exception as e:
        status_placeholder.empty()
        result_placeholder.empty()
        error_placeholder.error(
            "🚨 <b>예기치 않은 오류가 발생했습니다!</b>", icon="🚨", unsafe_allow_html=True
        )
        with error_placeholder.expander("오류 상세 보기", expanded=False):
            st.code(traceback.format_exc())
