
import streamlit as st
import asyncio
import pandas as pd
import openpyxl
from openpyxl.styles import Alignment
import os
import sys
import subprocess
import traceback
import logging
import nest_asyncio
from playwright.async_api import async_playwright

nest_asyncio.apply()

st.set_page_config(page_title="나라장터 제안공고 크롤러", layout="centered")

st.markdown("## 💻 나라장터 제안공고 크롤러")
st.caption("컴퓨터 관련 제안공고를 G2B에서 크롤링하여 다운로드합니다.")

progress_bar = st.progress(0)
status_text = st.empty()

def update_status(message, progress):
    status_text.info(message)
    progress_bar.progress(progress)

async def run_crawler():
    update_status("1️⃣ Playwright 브라우저 실행 중...", 5)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        update_status("2️⃣ G2B 홈페이지 접속 중...", 10)
        await page.goto("https://shop.g2b.go.kr/", timeout=30000)
        await asyncio.sleep(3)

        update_status("3️⃣ 팝업 닫는 중...", 20)
        try:
            popups = await page.query_selector_all("div[id^='mf_wfm_container_wq_uuid_']")
            for popup in popups:
                close_btn = await popup.query_selector("button[class*='w2window_close']")
                if close_btn:
                    await close_btn.click()
                    await asyncio.sleep(0.5)
        except:
            pass

        update_status("4️⃣ 브라우저 하단으로 스크롤 중...", 30)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)

        update_status("5️⃣ 제안공고 목록 버튼 클릭 중...", 40)
        clicked = False
        selectors = [
            'a[id$="_btnPrpblist"]',
            'a:has-text("제안공고목록")',
            '//a[contains(text(), "제안공고목록")]'
        ]
        for sel in selectors:
            try:
                btn = await page.query_selector(sel)
                if btn:
                    await btn.click()
                    clicked = True
                    break
            except:
                continue
        if not clicked:
            raise Exception("제안공고 목록 버튼 클릭 실패")

        await asyncio.sleep(2)
        update_status("6️⃣ 검색 조건 설정 중...", 55)

        await page.evaluate("""
            const radio = document.querySelector('input[title="3개월"]');
            if (radio) {
                radio.checked = true;
                const event = new Event('click', { bubbles: true });
                radio.dispatchEvent(event);
            }
        """)
        await asyncio.sleep(1)

        input_elem = await page.query_selector('td[data-title="제안공고명"] input[type="text"]')
        if input_elem:
            await input_elem.fill('컴퓨터')

        await page.evaluate("""
            const selects = document.querySelectorAll('select[id*="RecordCountPerPage"]');
            selects.forEach(select => {
                select.value = "100";
                const event = new Event('change', { bubbles: true });
                select.dispatchEvent(event);
            });
        """)
        await asyncio.sleep(1)

        await page.click('input[type="button"][value="적용"]')
        await page.click('input[type="button"][value="검색"]')

        update_status("7️⃣ 테이블 데이터 추출 중...", 75)
        await asyncio.sleep(2)
        table_elem = await page.query_selector('table[id$="grdPrpsPbanc_body_table"]')
        data = []
        if table_elem:
            rows = await table_elem.query_selector_all('tr')
            for row in rows:
                tds = await row.query_selector_all('td')
                cols = []
                for td in tds:
                    text = await td.inner_text()
                    cols.append(text.strip())
                if any(cols):
                    data.append(cols)

        if data:
            df = pd.DataFrame(data)
            df.to_excel("g2b_result.xlsx", index=False)

            wb = openpyxl.load_workbook("g2b_result.xlsx")
            ws = wb.active
            align = Alignment(horizontal='center', vertical='center')
            for row in ws.iter_rows():
                for cell in row:
                    cell.alignment = align
            wb.save("g2b_result.xlsx")

        update_status("✅ 완료! 파일 저장됨", 100)
        await browser.close()

if st.button("🚀 크롤링 시작"):
    try:
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        asyncio.run(run_crawler())
        with open("g2b_result.xlsx", "rb") as f:
            st.download_button("📥 다운로드", f, file_name="g2b_result.xlsx")
    except Exception as e:
        st.error(f"❌ 실행 중 오류: {e}")
