import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import traceback
import nest_asyncio
import streamlit as st

# 중첩 이벤트 루프 허용
nest_asyncio.apply()

async def close_notice_popups(page):
    """공지팝업 닫기 - 최대 5개까지 반복"""
    try:
        for i in range(5):
            popup_selectors = await page.query_selector_all("h2.w2window_header_title_h2")
            if not popup_selectors:
                break
            for popup in popup_selectors:
                title_text = await popup.inner_text()
                if "공지팝업" in title_text:
                    close_button = await popup.evaluate_handle("""
                        (element) => {
                            const popupDiv = element.closest('.w2popup_window');
                            return popupDiv.querySelector('button.w2window_close');
                        }
                    """)
                    if close_button:
                        await close_button.click()
                        await asyncio.sleep(0.3)
    except Exception as e:
        print(f"[DEBUG] 팝업 닫기 오류: {e}")

async def crawl_g2b():
    """G2B 사이트 접속 후 검색 및 데이터 수집"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://shop.g2b.go.kr/")

        # 팝업 닫기
        await close_notice_popups(page)

        # TODO: 여기서 검색어 입력 / 검색 버튼 클릭 / 결과 수집
        # 샘플 데이터
        data = [
            {"공고명": "샘플 공고 1", "URL": "https://example.com/1"},
            {"공고명": "샘플 공고 2", "URL": "https://example.com/2"}
        ]
        df = pd.DataFrame(data)
        df.to_excel("g2b_result.xlsx", index=False)

        await browser.close()

async def main():
    try:
        await crawl_g2b()
    except Exception as e:
        st.error(f"❌ 크롤링 중 오류 발생: {e}")
        traceback.print_exc()
