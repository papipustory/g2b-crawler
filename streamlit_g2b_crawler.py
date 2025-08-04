import streamlit as st
import asyncio
import pandas as pd
import openpyxl
from openpyxl.styles import Alignment
import os
import sys
import time
from playwright.async_api import async_playwright
import nest_asyncio

nest_asyncio.apply()

st.set_page_config(page_title="💻 나라장터 제안공고 크롤러", layout="centered")
st.title("💻 나라장터 제안공고 크롤러")
st.markdown("컴퓨터 관련 제안공고를 G2B에서 크롤링하여 다운로드합니다.")

progress_text = st.empty()
progress_bar = st.progress(0)

def update_progress(step: int, total_steps: int, message: str):
    ratio = step / total_steps
    progress_bar.progress(ratio)
    progress_text.info(f"{message} ({step}/{total_steps})")

async def close_notice_popups(page):
    await asyncio.sleep(1)
    for _ in range(3):
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(1.5)
        popups = await page.query_selector_all("div[id^='mf_wfm_container_wq_uuid_'][class*='w2popup_window']")
        for popup in popups:
            try:
                title = await popup.query_selector("h2")
                if title:
                    text = await title.inner_text()
                    if "팝업" in text:
                        close_btn = await popup.query_selector("button[class*='w2window_close']")
                        if close_btn:
                            await close_btn.click()
                            await asyncio.sleep(1.5)
            except:
                pass

async def run_crawler():
    step = 0
    total_steps = 10
    update_progress(step, total_steps, "Playwright 브라우저 실행 중...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        step += 1
        update_progress(step, total_steps, "1️⃣ 사이트 접속 중...")

        await page.goto("https://shop.g2b.go.kr/")
        await asyncio.sleep(3)

        step += 1
        update_progress(step, total_steps, "2️⃣ 팝업창 닫는 중...")
        await close_notice_popups(page)
        await asyncio.sleep(1.5)

        step += 1
        update_progress(step, total_steps, "3️⃣ 페이지 하단으로 스크롤...")
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)

        step += 1
        update_progress(step, total_steps, "4️⃣ Clicking proposal list button...")
        await asyncio.sleep(1)
        await page.evaluate("""
            const buttons = document.querySelectorAll("a, input");
            buttons.forEach(btn => {
                if (btn.innerText && btn.innerText.includes("제안공고목록")) {
                    btn.click();
                }
            });
        """)
        await asyncio.sleep(2)

        step += 1
        update_progress(step, total_steps, "5️⃣ 3개월 라디오 선택 중...")
        await page.evaluate("""
            const radio = document.querySelector('input[title="3개월"]');
            if (radio) {
                radio.checked = true;
                radio.dispatchEvent(new Event('click', { bubbles: true }));
            }
        """)
        await asyncio.sleep(1.5)

        step += 1
        update_progress(step, total_steps, "6️⃣ Typing search keyword...")
        search_input = await page.query_selector('td[data-title="제안공고명"] input[type="text"]')
        if search_input:
            await search_input.fill('컴퓨터')
        await asyncio.sleep(1)

        step += 1
        update_progress(step, total_steps, "7️⃣ 표시수 변경 중...")
        await page.evaluate("""
            const selects = document.querySelectorAll('select[id*="RecordCountPerPage"]');
            selects.forEach(select => {
                select.value = "100";
                select.dispatchEvent(new Event('change', { bubbles: true }));
            });
        """)
        await asyncio.sleep(1)

        step += 1
        update_progress(step, total_steps, "8️⃣ 검색 버튼 클릭 중...")
        await page.click('input[type="button"][value="적용"]')
        await page.click('input[type="button"][value="검색"]')
        await asyncio.sleep(2)

        step += 1
        update_progress(step, total_steps, "9️⃣ Collecting table data...")
        table = await page.query_selector('table[id$="grdPrpsPbanc_body_table"]')
        data = []
        if table:
            rows = await table.query_selector_all("tr")
            for row in rows:
                cols = await row.query_selector_all("td")
                row_data = []
                for col in cols:
                    text = await col.inner_text()
                    row_data.append(text.strip())
                if row_data:
                    data.append(row_data)

        df = pd.DataFrame(data)
        if not df.empty:
            df.columns = ["No", "제안공고번호", "수요기관", "제안공고명", "공고게시일자", "공고마감일시", "공고상태", "사유", "기타"]
            df.to_excel("g2b_result.xlsx", index=False)

            wb = openpyxl.load_workbook("g2b_result.xlsx")
            ws = wb.active
            align = Alignment(horizontal="center", vertical="center")
            for row in ws.iter_rows():
                for cell in row:
                    cell.alignment = align
            wb.save("g2b_result.xlsx")

        step += 1
        update_progress(step, total_steps, "✅ 크롤링 완료!")

        await browser.close()

if st.button("🧲 크롤링 시작"):
    st.toast("크롤링을 시작합니다. 약 1~2분 정도 소요됩니다.", icon="🕒")
    try:
        asyncio.run(run_crawler())
        with open("g2b_result.xlsx", "rb") as file:
            st.download_button(
                label="📥 결과 파일 다운로드",
                data=file,
                file_name="g2b_result.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    except Exception as e:
        st.error(f"❌ 실행 중 오류: {str(e)}")
