import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import openpyxl
from openpyxl.styles import Alignment
import os
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

async def wait_and_click(page, selector, desc, timeout=3000, scroll=True):
    """특정 요소 대기 후 클릭"""
    try:
        await page.wait_for_selector(selector, timeout=timeout)
        if scroll:
            await page.evaluate(f"document.querySelector('{selector}').scrollIntoView()")
        await page.click(selector)
        print(f"[DEBUG] 클릭 완료: {desc}")
    except Exception as e:
        print(f"[DEBUG] {desc} 클릭 실패: {e}")

async def main():
    print("[DEBUG] main() 시작")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            print("[DEBUG] G2B 접속 시도")
            await page.goto("https://shop.g2b.go.kr/")

            # 팝업 닫기
            await close_notice_popups(page)

            # 여기서 실제 크롤링 로직 수행 (샘플)
            print("[DEBUG] 샘플 데이터 생성")
            df = pd.DataFrame({
                "공고명": ["테스트 공고 1", "테스트 공고 2"],
                "URL": ["https://example.com/1", "https://example.com/2"]
            })
            df.to_excel("g2b_result.xlsx", index=False)

            await browser.close()
            print("[DEBUG] main() 종료 - 정상 완료")

    except Exception as e:
        print(f"[DEBUG] main() 오류 발생: {repr(e)}")
        traceback.print_exc()
        st.error(f"❌ 크롤링 중 오류 발생: {e}")

