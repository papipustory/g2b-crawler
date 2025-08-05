import streamlit as st
import pandas as pd
import asyncio
import nest_asyncio
from playwright.async_api import async_playwright
from playwright.__main__ import main as playwright_main

nest_asyncio.apply()

st.title("나라장터 제안공고 크롤러 (Streamlit Cloud 최적화)")

search_query = st.text_input("검색어를 입력하세요", "컴퓨터")

if st.button("크롤링 실행"):
    st.write("크롤링을 시작합니다...")

    try:
        # (1) Playwright 바이너리 설치 (필수, 누락시 에러 발생)
        try:
            playwright_main(['install', 'chromium'])
        except Exception as e:
            st.info("Chromium 설치 생략 또는 이미 설치됨")

        async def crawl_g2b(search_query):
            data = []
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True, 
                    args=["--no-sandbox", "--disable-setuid-sandbox"]
                )
                page = await browser.new_page()
                await page.goto("https://shop.g2b.go.kr/")
                await asyncio.sleep(2)
                # 실제 크롤링 로직(아래 예시)
                # 예: 메인 타이틀 추출
                title = await page.title()
                data.append({"타이틀": title})
                await browser.close()
            return pd.DataFrame(data)

        result_df = asyncio.run(crawl_g2b(search_query))
        st.dataframe(result_df)
        st.success("크롤링이 완료되었습니다!")

    except Exception as e:
        st.error(f"크롤링 중 오류 발생: {e}")
