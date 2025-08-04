
import streamlit as st
import asyncio
import pandas as pd
import openpyxl
from openpyxl.styles import Alignment
import os
import sys
import traceback
import logging
import nest_asyncio
from playwright.async_api import async_playwright

nest_asyncio.apply()

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="💻 나라장터 제안공고 크롤러", layout="centered", page_icon="📄")

st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .block-container {
        padding-top: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📄 나라장터 제안공고 크롤러")
st.markdown("**국가종합전자조달(G2B)** 사이트에서 '컴퓨터' 키워드의 제안공고 목록을 자동 수집합니다.")

status = st.empty()
progress_bar = st.empty()

def debug_log(message):
    st.write(f"🔍 {message}")
    print(f"DEBUG: {message}")

async def close_notice_popups(page):
    for _ in range(5):
        popup_divs = await page.query_selector_all("div[id^='mf_wfm_container_wq_uuid_'][class*='w2popup_window']")
        closed = False
        for popup in popup_divs:
            try:
                for sel in ["button[class*='w2window_close']", "input[type='button'][value='닫기']"]:
                    btn = await popup.query_selector(sel)
                    if btn:
                        await btn.click()
                        await asyncio.sleep(0.2)
                        closed = True
                        break
                checkbox = await popup.query_selector("input[type='checkbox'][title*='오늘 하루']")
                if checkbox:
                    await checkbox.check()
                    await asyncio.sleep(0.1)
                    btn = await popup.query_selector("input[type='button'][value='닫기']")
                    if btn:
                        await btn.click()
                        closed = True
                        break
            except:
                continue
        if not closed:
            break
        await asyncio.sleep(0.5)

async def wait_and_click(page, selector, desc, timeout=3000, scroll=True):
    try:
        await page.wait_for_selector(selector, timeout=timeout, state="visible")
        elem = await page.query_selector(selector)
        if elem and await elem.is_visible():
            if scroll:
                await elem.scroll_into_view_if_needed()
                await asyncio.sleep(0.02)
            await elem.click()
            return True
        return False
    except:
        return False

async def main():
    file_path = 'g2b_result.xlsx'
    browser = None
    try:
        status.text("🌐 G2B 사이트 접속 중...")
        debug_log("사이트 접속 시작")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto("https://shop.g2b.go.kr/", timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=30000)
            await asyncio.sleep(3)
            debug_log("사이트 접속 완료")

            status.text("🧼 팝업 닫는 중...")
            await close_notice_popups(page)
            debug_log("팝업 닫기 완료")

            status.text("📥 제안공고목록 클릭 중...")
            btn_selectors = [
                'a[id^="mf_wfm_container_wq_uuid_"][id$="_btnPrpblist"]',
                'a[title*="제안공고목록"]',
                'a:has-text("제안공고목록")',
                '//a[contains(text(), "제안공고목록")]',
                'div.w2textbox:text("제안공고목록")',
            ]
            for sel in btn_selectors:
                if await wait_and_click(page, sel, "제안공고목록 버튼"):
                    break
            await asyncio.sleep(1)

            status.text("📅 3개월 옵션 선택 중...")
            await page.evaluate("""
                const radio = document.querySelector('input[title="3개월"]');
                if (radio) {
                    radio.checked = true;
                    const event = new Event('click', { bubbles: true });
                    radio.dispatchEvent(event);
                }
            """)
            await asyncio.sleep(1)

            status.text("🔍 검색어 '컴퓨터' 입력 중...")
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

            status.text("🔎 검색 버튼 클릭 중...")
            await wait_and_click(page, 'input[type="button"][value="적용"]', "적용버튼", scroll=False)
            await wait_and_click(page, 'input[type="button"][value="검색"]', "검색버튼", scroll=False)
            await asyncio.sleep(1)

            status.text("📊 테이블 수집 중...")
            table_elem = await page.query_selector('table[id$="grdPrpsPbanc_body_table"]')
            if table_elem:
                rows = await table_elem.query_selector_all('tr')
                data = []
                for row in rows:
                    tds = await row.query_selector_all('td')
                    cols = []
                    for td in tds:
                        nobr = await td.query_selector('nobr')
                        if nobr:
                            text = await nobr.inner_text()
                        else:
                            a = await td.query_selector('a')
                            if a:
                                text = await a.inner_text()
                            else:
                                text = await td.inner_text()
                        cols.append(text.strip())
                    if cols and any(cols):
                        data.append(cols)

                debug_log(f"수집된 행 수: {len(data)}")
                if data:
                    new_df = pd.DataFrame(data)
                    headers = ["No", "제안공고번호", "수요기관", "제안공고명", "공고게시일자", "공고마감일시", "공고상태", "사유", "기타"]
                    if len(new_df.columns) < len(headers):
                        headers = headers[:len(new_df.columns)]
                    elif len(new_df.columns) > len(headers):
                        new_df = new_df.iloc[:, :len(headers)]
                    new_df.columns = headers

                    if os.path.exists(file_path):
                        old_df = pd.read_excel(file_path)
                        combined_df = pd.concat([old_df, new_df])
                        combined_df.drop_duplicates(subset="제안공고번호", keep='last', inplace=True)
                        combined_df.reset_index(drop=True, inplace=True)
                    else:
                        combined_df = new_df

                    combined_df.to_excel(file_path, index=False)

                    wb = openpyxl.load_workbook(file_path)
                    ws = wb.active
                    align = Alignment(horizontal='center', vertical='center')
                    for row in ws.iter_rows():
                        for cell in row:
                            cell.alignment = align
                    col_widths = [3.5, 17, 44, 55, 15, 17.5, 17, 17, 17]
                    for i, width in enumerate(col_widths, start=1):
                        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = width
                    wb.save(file_path)
                    debug_log("📁 엑셀 저장 완료")

    except Exception as e:
        status.text("❌ 크롤링 중 오류 발생")
        st.error(f"오류 발생: {str(e)}")
        traceback.print_exc()
    finally:
        if browser:
            await browser.close()

if st.button("🚀 제안공고 크롤링 시작"):
    status.text("🟡 준비 중...")
    progress_bar.progress(5)
    try:
        asyncio.get_event_loop().run_until_complete(main())
        status.text("✅ 완료되었습니다.")
        progress_bar.progress(100)
        with open("g2b_result.xlsx", "rb") as file:
            st.download_button("📥 결과 다운로드 (Excel)", data=file, file_name="g2b_result.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        st.error(f"❌ 실행 중 오류: {str(e)}")
        traceback.print_exc()
