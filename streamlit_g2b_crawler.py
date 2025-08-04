import asyncio
import os
import streamlit as st
import pandas as pd
import openpyxl
from openpyxl.styles import Alignment
from playwright.async_api import async_playwright

st.set_page_config(page_title="G2B 제안공고 크롤러", layout="wide")
st.title("💻 나라장터 제안공고 크롤링")
start = st.button("크롤링 시작")

def save_to_excel(data):
    file_path = 'g2b_result.xlsx'
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
    st.success("Excel 저장 완료 (g2b_result.xlsx)")

async def crawl():
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            await page.goto("https://shop.g2b.go.kr/", timeout=10000)
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(3)

            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)

            # 제안공고목록 버튼 클릭
            selectors = [
                'a[id^="mf_wfm_container_wq_uuid_"][id$="_btnPrpblist"]',
                'a[title*="제안공고목록"]',
                'a:has-text("제안공고목록")',
                '//a[contains(text(), "제안공고목록")]',
            ]
            for sel in selectors:
                try:
                    await page.locator(sel).click(timeout=3000)
                    break
                except:
                    continue
            await asyncio.sleep(1)

            # 3개월 체크
            await page.evaluate("""
                const radio = document.querySelector('input[title="3개월"]');
                if (radio) {
                    radio.checked = true;
                    const event = new Event('click', { bubbles: true });
                    radio.dispatchEvent(event);
                }
            """)
            await asyncio.sleep(1)

            # 검색어 입력
            input_elem = await page.query_selector('td[data-title="제안공고명"] input[type="text"]')
            if input_elem:
                await input_elem.fill('컴퓨터')

            # 표시수 100 설정
            await page.evaluate("""
                const selects = document.querySelectorAll('select[id*="RecordCountPerPage"]');
                selects.forEach(select => {
                    select.value = "100";
                    const event = new Event('change', { bubbles: true });
                    select.dispatchEvent(event);
                });
            """)
            await asyncio.sleep(1)

            await page.click('input[type="button"][value="적용"]', timeout=5000)
            await page.click('input[type="button"][value="검색"]', timeout=5000)
            await asyncio.sleep(2)

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

                if data:
                    save_to_excel(data)
            await browser.close()
    except Exception as e:
        st.error(f"❌ 오류 발생: {e}")

if start:
    st.info("크롤링을 시작합니다. 잠시만 기다려 주세요...")
    asyncio.run(crawl())
