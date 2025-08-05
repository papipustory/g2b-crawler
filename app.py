import streamlit as st
import asyncio
from streamlit_g2b_crawler import main  # 정식 파일명으로 변경

# Streamlit 페이지 설정
st.set_page_config(page_title="나라장터 제안공고 크롤러", layout="centered")
st.title("💻 나라장터 제안공고 크롤러")
st.caption("컴퓨터 관련 제안공고를 G2B에서 크롤링하여 다운로드합니다.")

# 상태 표시 UI 요소
progress_bar = st.empty()
status = st.empty()

# 크롤러 실행 함수
def run_crawler_async():
    asyncio.run(main())

# 실행 버튼
if st.button("📦 크롤링 시작"):
    st.info("Playwright 크롤링을 실행 중입니다. 잠시 기다려 주세요.")
    progress_bar.progress(5)
    status.text("브라우저 시작 중...")

    try:
        run_crawler_async()
        progress_bar.progress(100)
        st.success("✅ 크롤링 완료")
    except Exception as e:
        st.error(f"❌ 에러 발생: {e}")
    finally:
        progress_bar.empty()
        status.empty()

# 다운로드 버튼 (결과 파일 존재 시)
if "g2b_result.xlsx" in __import__('os').listdir():
    with open("g2b_result.xlsx", "rb") as f:
        st.download_button(
            label="📥 크롤링 결과 다운로드",
            data=f,
            file_name="g2b_result.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
