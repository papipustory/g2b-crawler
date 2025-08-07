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

@st.cache_resource(show_spinner="브라우저를 설정하고 있습니다...")
def install_and_get_browser():
    """앱 실행 환경 내에서 브라우저를 설치하고, 설치된 실행 파일 경로를 반환합니다."""
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = BROWSER_PATH
    
    # 1. 브라우저가 이미 설치되었는지 확인 (가장 가능성 높은 시나리오)
    # glob를 사용해 버전 번호를 하드코딩하지 않고 동적으로 경로를 찾습니다.
    executable_path_glob = os.path.join(BROWSER_PATH, "chromium-*", "chrome-linux", "chrome")
    found_paths = glob.glob(executable_path_glob)
    if found_paths:
        st.toast(f"이미 설치된 브라우저를 사용합니다: {found_paths[0]}")
        return found_paths[0]

    # 2. 설치되지 않았다면, subprocess를 이용해 설치합니다.
    st.info(f"브라우저를 {BROWSER_PATH}에 설치합니다. (최초 1회)")
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True, # 오류 발생 시 예외를 발생시킴
            capture_output=True, # 표준 출력/오류를 캡처
            text=True
        )
        st.success("브라우저 설치 완료!")
        
        # 3. 설치 후 다시 경로를 찾아서 반환합니다.
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

# --- 앱 로직 시작 ---
browser_executable_path = install_and_get_browser()

if browser_executable_path:
    from g2b_crawler import run_g2b_crawler
else:
    st.error("브라우저를 준비할 수 없어 앱을 실행할 수 없습니다. 페이지를 새로고침하거나 로그를 확인하세요.")
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
            # 크롤러에 동적으로 찾은 브라우저 경로를 전달합니다.
            result = run_g2b_crawler(search_query, browser_executable_path)

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
