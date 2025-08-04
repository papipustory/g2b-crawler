import streamlit as st
import asyncio
from playwright.async_api import async_playwright
import pandas as pd
import openpyxl
from openpyxl.styles import Alignment
import os
import sys

st.set_page_config(page_title="나라장터 제안공고 크롤러", layout="centered")

st.title("💻 나라장터 제안공고 크롤링")

# Streamlit Cloud에서 asyncio 이벤트 루프 처리
def run_async_code():
    try:
        # 기존 이벤트 루프가 있는지 확인
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 이미 실행 중인 루프가 있다면 새 스레드에서 실행
            import threading
            import concurrent.futures
            
            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(main())
                finally:
                    new_loop.close()
            
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result()
        else:
            return asyncio.run(main())
    except RuntimeError:
        # 새로운 이벤트 루프 생성
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(main())
        finally:
            loop.close()

if st.button("크롤링 시작"):
    st.info("크롤링을 시작합니다. 잠시만 기다려 주세요...")

    async def wait_and_click(page, selector, name, timeout=3000, scroll=True):
        try:
            if scroll:
                await page.evaluate(f'''
                    var el = document.querySelector('{selector}');
                    if (el) el.scrollIntoView();
                ''')
            await page.wait_for_selector(selector, timeout=timeout)
            await page.click(selector)
            return True
        except Exception:
            print(f"[실패] {name} 클릭 실패: selector {selector}")
            return False

    async def close_notice_popups(page):
        try:
            popup_buttons = await page.query_selector_all("div.popup a")
            for btn in popup_buttons:
                text = await btn.inner_text()
                if "닫기" in text:
                    await btn.click()
        except:
            pass

    async def main():
        browser = None
        try:
            async with async_playwright() as p:
                # Streamlit Cloud에서 브라우저 실행 옵션 추가
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-accelerated-2d-canvas',
                        '--no-first-run',
                        '--no-zygote',
                        '--single-process',
                        '--disable-gpu'
                    ]
                )
                context = await browser.new_context()
                page = await context.new_page()
                
                # 타임아웃 증가
                await page.goto("https://shop.g2b.go.kr/", timeout=30000)
                await page.wait_for_load_state('networkidle', timeout=30000)
                await asyncio.sleep(2)

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
                else:
                    all_a = await page.query_selector_all("a")
                    for a in all_a:
                        try:
                            title = await a.get_attribute("title")
                            href = await a.get_attribute("href")
                            inner = await a.inner_text()
                            if (title and "제안공고" in title) or (inner and "제안공고" in inner):
                                if href and href.strip() != "javascript:void(null)":
                                    await a.scroll_into_view_if_needed()
                                    await asyncio.sleep(0.2)
                                    await a.click()
                                    break
                        except:
                            continue

                await asyncio.sleep(1)

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

                await wait_and_click(page, 'input[type="button"][value="적용"]', "적용버튼", scroll=False)
                await wait_and_click(page, 'input[type="button"][value="검색"]', "검색버튼", scroll=False)
                await asyncio.sleep(1)

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
                        new_df = pd.DataFrame(data)
                        headers = ["No", "제안공고번호", "수요기관", "제안공고명", "공고게시일자", "공고마감일시", "공고상태", "사유", "기타"]
                        if len(new_df.columns) < len(headers):
                            headers = headers[:len(new_df.columns)]
                        elif len(new_df.columns) > len(headers):
                            new_df = new_df.iloc[:, :len(headers)]
                        new_df.columns = headers

                        # Streamlit Cloud에서는 임시 디렉토리 사용
                        file_path = '/tmp/g2b_result.xlsx'
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

                        # 다운로드 버튼 제공
                        with open(file_path, 'rb') as f:
                            st.download_button(
                                label="📥 결과 파일 다운로드",
                                data=f.read(),
                                file_name="g2b_result.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                        
                        st.success("✅ 크롤링 완료!")
                        st.dataframe(combined_df.head(10))  # 미리보기 제공
                    else:
                        st.warning("📭 공고 목록을 찾을 수 없습니다.")

        except Exception as e:
            st.error(f"❌ 오류 발생: {str(e)}")
            import traceback
            st.error(f"상세 오류: {traceback.format_exc()}")

        finally:
            if browser:
                await browser.close()

    # asyncio 실행
    run_async_code()
