import asyncio
import streamlit as st
from playwright.async_api import async_playwright
import pandas as pd
import os
import openpyxl
from openpyxl.styles import Alignment
import base64

import subprocess
subprocess.run(["playwright", "install"], check=True)

# 팝업창 닫기 함수
async def close_notice_popups(page):
    for _ in range(5):
        popup_divs = await page.query_selector_all("div[id^='mf_wfm_container_wq_uuid_'][class*='w2popup_window']")
        for popup in popup_divs:
            try:
                for sel in ["button[class*='w2window_close']", "input[type='button'][value='닫기']"]:
                    btn = await popup.query_selector(sel)
                    if btn:
                        await btn.click()
                        await asyncio.sleep(0.2)
                        break
                checkbox = await popup.query_selector("input[type='checkbox'][title*='오늘 하루']")
                if checkbox:
                    await checkbox.check()
                    await asyncio.sleep(0.1)
                    btn = await popup.query_selector("input[type='button'][value='닫기']")
                    if btn:
                        await btn.click()
                        break
            except:
                continue
        await asyncio.sleep(0.5)

# 버튼 대기 및 클릭 함수
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

# 크롤링 함수
async def crawl_and_save(search_term):
    result_msg = ""
    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto("https://shop.g2b.go.kr/", timeout=3000)
            await page.wait_for_load_state('networkidle', timeout=5000)
            await asyncio.sleep(3)

            await close_notice_popups(page)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)

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

            await asyncio.sleep(0.3)

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
                await input_elem.fill(search_term, timeout=1000)

            await page.evaluate("""
                const selects = document.querySelectorAll('select[id*="RecordCountPerPage"]');
                selects.forEach(select => {
                    select.value = "100";
                    const event = new Event('change', { bubbles: true });
                    select.dispatchEvent(event);
                });
            """)
            await asyncio.sleep(1)

            await wait_and_click(page, 'input[type="button"][value="적용"]', "적용버튼", scroll=False)
            await wait_and_click(page, 'input[type="button"][value="검색"]', "검색버튼", scroll=False)
            await asyncio.sleep(0.8)

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
                            text = await a.inner_text() if a else await td.inner_text()
                        cols.append(text.strip())
                    if cols and any(cols):
                        data.append(cols)

                if data:
                    new_df = pd.DataFrame(data)
                    headers = ["No", "제안공고번호", "수요기관", "제안공고명", "공고게시일자", "공고마감일시", "공고상태", "사유", "기타"]
                    new_df.columns = headers[:len(new_df.columns)]
                    new_df.insert(0, "검색어", search_term)

                    file_path = 'g2b_result.xlsx'
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
                    col_widths = [15, 3.5, 17, 44, 55, 15, 17.5, 17, 17, 17]
                    for i, width in enumerate(col_widths, start=1):
                        col_letter = openpyxl.utils.get_column_letter(i)
                        ws.column_dimensions[col_letter].width = width
                    wb.save(file_path)
                    result_msg = f"✅ 크롤링 완료: `{search_term}` 검색, 파일 저장됨 → g2b_result.xlsx"
                else:
                    result_msg = "⚠️ 검색 결과가 없습니다."
    except Exception as e:
        result_msg = f"❌ 오류 발생: {e}"
    finally:
        if browser:
            await browser.close()
        return result_msg

# 다운로드 버튼 생성 함수
def file_download_button(file_path, label):
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="{os.path.basename(file_path)}">{label}</a>'
        st.markdown(href, unsafe_allow_html=True)

# ----------------------
# Streamlit UI 시작
# ----------------------
st.set_page_config(page_title="G2B 제안공고 크롤러", layout="centered")
st.title("💻 G2B 제안공고 크롤러")

search_term = st.text_input("🔎 검색어를 입력하세요", value="컴퓨터", help="예: 컴퓨터, 데스크톱, 모니터, 노트북 등")

if st.button("크롤링 시작"):
    st.info(f"⏳ '{search_term}'로 검색 중입니다. 잠시만 기다려주세요...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    result = loop.run_until_complete(crawl_and_save(search_term))
    st.success(result)

    if os.path.exists("g2b_result.xlsx"):
        st.markdown("---")
        st.subheader("📥 결과 다운로드")
        file_download_button("g2b_result.xlsx", "👉 결과 엑셀 파일 다운로드")
