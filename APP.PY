import streamlit as st
import asyncio
import traceback
from concurrent.futures import ThreadPoolExecutor
import os

# streamlit_g2b_crawler.py 의 main() 불러오기
from streamlit_g2b_crawler import main as crawler_main

# ===============================
# Streamlit 페이지 설정
# ===============================
st.set_page_config(page_title="나라장터 제안공고 크롤러", layout="centered")
st.title("💻 나라장터 제안공고 크롤러")
st.caption("컴퓨터 관련 제안공고를 G2B에서 크롤링하여 다운로드합니다.")

# 진행 표시 영역
progress_bar = st.empty()
status_text = st.empty()

# ===============================
# 크롤러 실행 함수
# ===============================
def run_crawler_async():
    try:
        asyncio.run(crawler_main())  # streamlit_g2b_crawler.py 의 main 실행
    except Exception:
        traceback.print_exc()
        raise

# ===============================
# 버튼 클릭 시 크롤링 시작
# ===============================
if st.button("📦 크롤링 시작"):
    st.info("Playwright 크롤링을 실행 중입니다. 잠시 기다려 주세요.")
    progress_bar.progress(5)
    status_text.text("브라우저 시작 중...")

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run_crawler_async)
        while not future.done():
            progress_bar.progress(50)
            status_text.text("공고 수집 중...")

        try:
            future.result()
            progress_bar.progress(100)
            st.success("✅ 크롤링 완료")
        except Exception as e:
            st.error(f"❌ 에러 발생: {e}")
        finally:
            progress_bar.empty()
            status_text.empty()

# ===============================
# 다운로드 버튼
# ===============================
excel_file = "g2b_result.xlsx"
if os.path.exists(excel_file):
    with open(excel_file, "rb") as f:
        st.download_button(
            label="📥 크롤링 결과 다운로드",
            data=f,
            file_name="g2b_result.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
