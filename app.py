import streamlit as st
import pandas as pd
import io
import os
import subprocess
import sys
import glob
from contextlib import redirect_stdout

BROWSER_PATH = "/tmp/playwright-browsers"

@st.cache_resource(show_spinner="브라우저 준비 중입니다...")
def install_and_get_browser():
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
    except subprocess.CalledProcessError:
        st.error("브라우저 설치에 실패했습니다.")
        return None
    except Exception as e:
        st.error(f"알 수 없는 오류 발생: {e}")
        return None

# ---------- Streamlit Custom CSS (고급 스타일) ----------
st.set_page_config(
    page_title="나라장터 제안공고 크롤러",
    page_icon="🏛️",
    layout="wide"
)

st.markdown(
    """
    <style>
    /* 헤더 & 전체 레이아웃 */
    .main-title {font-size:2.7rem; font-weight:800; color:#233059; letter-spacing:-0.03em;}
    .subtitle {font-size:1.18rem; color:#4A5662; margin-bottom:18px;}
    .search-card {background:#f3f7fc; border-radius:18px; padding:26px 30px 20px 30px; margin-bottom:34px; box-shadow: 0 4px 20px #d6e5f3;}
    .result-card {background:#ffffff; border-radius:22px; padding:36px 36px 30px 36px; box-shadow:0 6px 38px #e3e7ee; margin-bottom:40px;}
    .result-title {font-size:1.34rem; font-weight:700; color:#203356; margin-bottom:18px;}
    .stDataFrame {background: #f9fbfd; border-radius: 15px; box-shadow: 0 3px 24px #e8ecf5; font-size:1.07rem;}
    .stDownloadButton>button {font-size:1.1rem !important; font-weight:600; border-radius:14px; padding:14px 24px; background:linear-gradient(90deg,#377efb 0%,#65c3ff 100%);}
    .alert-card {background:#fff6e2; border-radius:15px; padding:18px 28px; border:1px solid #ffecb2; color:#9f7303; font-size:1.05rem;}
    .success-card {background:#eaf6ed; border-radius:15px; padding:18px 28px; border:1px solid #9fd6a4; color:#217541; font-size:1.05rem;}
    .footer {font-size:1.02rem; color:#a5afbb; text-align:right; margin-top:40px;}
    .stTextInput>div>input {font-size:1.13rem;}
    </style>
    """,
    unsafe_allow_html=True
)

# ---------- 브라우저 준비 ----------
browser_executable_path = install_and_get_browser()
if not browser_executable_path:
    st.error("브라우저를 준비할 수 없어 앱을 실행할 수 없습니다.\n페이지를 새로고침해 주세요.")
    st.stop()

from g2b_crawler import run_g2b_crawler

# ---------- 헤더 영역 ----------
st.markdown('<div class="main-title">🏛️ 나라장터 제안공고 크롤러</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">나라장터 제안공고 데이터를 <b>한 번의 검색</b>으로 빠르게 수집하고, <b>엑셀(또는 CSV)</b>로 바로 저장하세요.<br>검색 후 상세 테이블·다운로드 지원!</div>',
    unsafe_allow_html=True,
)
st.markdown("---")

# ---------- 검색 카드 ----------
st.markdown('<div class="search-card">', unsafe_allow_html=True)
with st.form(key="search_form", clear_on_submit=False):
    search_query = st.text_input("🔎 검색어", value="컴퓨터", help="공고명, 품목명 등 주요 키워드 입력")
    submitted = st.form_submit_button("크롤링 시작")
st.markdown('</div>', unsafe_allow_html=True)

# ---------- 결과 출력 ----------
if submitted:
    status_area = st.empty()
    log_capture = io.StringIO()
    try:
        status_area.markdown(
            f"<span style='color:#377efb;font-weight:600;'>⏳ <b>{search_query}</b> 검색 중입니다... 잠시만 기다려주세요.</span>",
            unsafe_allow_html=True
        )
        with redirect_stdout(log_capture):
            result = run_g2b_crawler(search_query, browser_executable_path)

        if result and result[1]:
            header, table_data = result
            df = pd.DataFrame(table_data, columns=header)

            st.markdown('<div class="result-card">', unsafe_allow_html=True)
            st.markdown(
                f'<div class="result-title">📑 <b>{len(df)}</b>건의 제안공고가 검색되었습니다.</div>',
                unsafe_allow_html=True
            )
            st.dataframe(
                df,
                use_container_width=True,
                height=650 if len(df) > 13 else 380
            )
            st.download_button(
                label="📥 결과 CSV 다운로드",
                data=df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"g2b_{search_query}.csv",
                mime="text/csv",
                help="엑셀에서 바로 열 수 있는 UTF-8 CSV입니다."
            )
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('<div class="success-card">✅ 검색이 성공적으로 완료되었습니다.</div>', unsafe_allow_html=True)

        else:
            st.markdown('<div class="alert-card">❌ 검색 결과가 없거나 크롤링에 실패했습니다.<br>검색어를 바꿔 시도해보세요.</div>', unsafe_allow_html=True)

    except Exception as e:
        st.markdown(f'<div class="alert-card">❌ 오류 발생: {str(e)}</div>', unsafe_allow_html=True)
        with st.expander("오류 상세 보기"):
            st.code(str(e))

else:
    st.markdown(
        '<div class="alert-card">1. 검색어 입력 후 <b>크롤링 시작</b>을 클릭하세요.<br>'
        '2. 약 1분 내외로 결과가 표로 출력됩니다.<br>'
        '3. <b>CSV 다운로드</b>로 엑셀 연동도 가능합니다.</div>',
        unsafe_allow_html=True
    )

st.markdown("---")
st.markdown('<div class="footer">© 2025 <b>위더스컴퓨터</b> · Powered by Playwright · 나라장터 제안공고 자동수집</div>', unsafe_allow_html=True)
