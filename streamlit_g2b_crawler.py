
import streamlit as st
import nest_asyncio
import asyncio
import pandas as pd
import openpyxl
from openpyxl.styles import Alignment
import os
import sys
import subprocess
from playwright.async_api import async_playwright
import traceback

# 환경 변수 설정 (Streamlit Cloud용)
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/tmp/playwright"

# 이벤트 루프 중첩 허용
nest_asyncio.apply()

st.set_page_config(page_title="💻 나라장터 제안공고 크롤러", layout="centered")
st.title("💻 나라장터 제안공고 크롤러")

st.markdown("컴퓨터 관련 제안공고를 G2B에서 크롤링하여 다운로드합니다.")

status_area = st.empty()
progress_bar = st.empty()

async def close_popups(page):
    for _ in range(3):
        popups = await page.query_selector_all("div[id^='mf_wfm_container_wq_uuid_'][class*='w2popup_window']")
        for popup in popups:
            try:
                btn = await popup.query_selector("input[type='button'][value='닫기']")
                if btn:
                    await btn.click()
                    await asyncio.sleep(0.2)
            except:
                pass
        await asyncio.sleep(0.5)

async def main():
    status_area.info("🔄 Playwright 브라우저 실행 중...")
    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"])

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://shop.g2b.go.kr/", timeout=60000)
        await page.wait_for_load_state("networkidle")
        await close_popups(page)
        await asyncio.sleep(1)

        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1)

        try:
            btn = await page.query_selector("a[title*='제안공고목록']")
            if btn:
                await btn.click()
            await asyncio.sleep(2)
        except:
            pass

        await page.evaluate("""
            const radio = document.querySelector('input[title="3개월"]');
            if (radio) {
                radio.checked = true;
                const event = new Event('click', { bubbles: true });
                radio.dispatchEvent(event);
            }
        """)
        await asyncio.sleep(1)

        search_input = await page.query_selector('td[data-title="제안공고명"] input[type="text"]')
        if search_input:
            await search_input.fill("컴퓨터")

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
        await asyncio.sleep(0.5)
        await page.click('input[type="button"][value="검색"]')
        await asyncio.sleep(1)

        table = await page.query_selector('table[id$="grdPrpsPbanc_body_table"]')
        if not table:
            status_area.warning("❌ 데이터를 찾을 수 없습니다.")
            return None

        rows = await table.query_selector_all("tr")
        data = []
        for row in rows:
            tds = await row.query_selector_all("td")
            row_data = []
            for td in tds:
                txt = await td.inner_text()
                row_data.append(txt.strip())
            data.append(row_data)

        headers = ["No", "제안공고번호", "수요기관", "제안공고명", "공고게시일자", "공고마감일시", "공고상태", "사유", "기타"]
        df = pd.DataFrame(data, columns=headers[:len(data[0])])
        df.dropna(how="all", inplace=True)

        file_path = "g2b_result.xlsx"
        df.to_excel(file_path, index=False)

        wb = openpyxl.load_workbook(file_path)
        ws = wb.active
        for row in ws.iter_rows():
            for cell in row:
                cell.alignment = Alignment(horizontal="center", vertical="center")
        wb.save(file_path)

        await browser.close()
        return file_path

if st.button("🚀 크롤링 시작"):
    status_area.info("크롤링을 시작합니다. 최대 1분 정도 걸릴 수 있습니다.")
    progress_bar.progress(10)
    try:
        loop = asyncio.get_event_loop()
        result_file = loop.run_until_complete(main())
        progress_bar.progress(100)

        if result_file and os.path.exists(result_file):
            with open(result_file, "rb") as f:
                st.download_button(
                    label="📥 크롤링 결과 다운로드 (Excel)",
                    data=f,
                    file_name="g2b_result.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            status_area.success("✅ 크롤링이 완료되었습니다.")
        else:
            status_area.warning("❌ 결과 파일이 존재하지 않습니다.")
    except Exception as e:
        status_area.error(f"❌ 실행 중 오류: {e}")
        st.exception(e)
    finally:
        progress_bar.empty()
