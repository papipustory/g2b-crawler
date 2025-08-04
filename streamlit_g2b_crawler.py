import streamlit as st
import asyncio
import pandas as pd
import openpyxl
from openpyxl.styles import Alignment
import os
import sys
from concurrent.futures import ThreadPoolExecutor
import traceback
import logging
from playwright.async_api import async_playwright

# ------------------------ 설정 및 초기화 ------------------------
st.set_page_config(page_title="나라장터 제안공고 크롤러", layout="centered")
st.title("💻 나라장터 제안공고 크롤링")

# 디버그 모드
if st.checkbox("🔍 디버그 모드 활성화"):
    st.session_state.debug_mode = True
else:
    st.session_state.debug_mode = False

def debug_log(message):
    if st.session_state.get('debug_mode', False):
        st.write(f"🔍 DEBUG: {message}")
    print(f"DEBUG: {message}")

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ------------------------ 브라우저 설치 확인 ------------------------
@st.cache_resource
def ensure_playwright_installed():
    try:
        import subprocess
        debug_log("Playwright 설치 확인 중...")
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True, text=True, timeout=300
        )
        if result.returncode != 0:
            st.error(f"Playwright 설치 실패: {result.stderr}")
            debug_log(f"설치 실패: {result.stderr}")
            return False
        debug_log("Playwright 설치 완료")
        return True
    except Exception as e:
        st.error(f"Playwright 설치 중 오류: {e}")
        debug_log(f"설치 오류: {e}")
        return False

# ------------------------ 유틸 함수 ------------------------
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

# ------------------------ 크롤링 메인 ------------------------
async def main():
    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            await page.goto("https://shop.g2b.go.kr/", timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=30000)
            await asyncio.sleep(3)

            await close_notice_popups(page)
            await asyncio.sleep(1)

            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)

            # 제안공고목록 버튼 클릭
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
                await input_elem.fill('컴퓨터', timeout=1000)

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
                            text = await a.inner_text() if a else await td.inner_text()
                        cols.append(text.strip())
                    if cols and any(cols):
                        data.append(cols)

                if data:
                    df = pd.DataFrame(data)
                    headers = ["No", "제안공고번호", "수요기관", "제안공고명", "공고게시일자", "공고마감일시", "공고상태", "사유", "기타"]
                    df.columns = headers[:len(df.columns)]

                    file_path = 'g2b_result.xlsx'
                    if os.path.exists(file_path):
                        old_df = pd.read_excel(file_path)
                        df = pd.concat([old_df, df]).drop_duplicates(subset="제안공고번호", keep='last').reset_index(drop=True)

                    df.to_excel(file_path, index=False)

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
                    print("Excel 저장 및 서식 완료")

            await asyncio.sleep(2)

    except Exception as e:
        debug_log(f"크롤링 중 오류: {e}")
        traceback.print_exc()
    finally:
        if browser:
            await browser.close()

# ------------------------ 실행 및 UI ------------------------

def run_async_main():
    try:
        asyncio.run(main())
    except Exception as e:
        debug_log(f"asyncio.run(main) 실패: {e}")
        traceback.print_exc()
        raise

if st.button("📦 크롤링 시작"):
    if not ensure_playwright_installed():
        st.stop()

    st.info("크롤링을 시작합니다. 잠시만 기다려 주세요.")
    progress_bar = st.progress(0)
    status = st.empty()

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run_async_main)
        while not future.done():
            progress_bar.progress(50)
            status.text("공고 수집 중...")

        try:
            future.result()
            progress_bar.progress(100)
            st.success("✅ 크롤링 완료!")
        except Exception as e:
            st.error(f"❌ 실행 중 오류: {e}")
        finally:
            progress_bar.empty()
            status.empty()

# ------------------------ 다운로드 버튼 ------------------------
file_path = "g2b_result.xlsx"
if os.path.exists(file_path):
    with open(file_path, "rb") as f:
        st.download_button(
            label="📥 크롤링 결과 다운로드",
            data=f,
            file_name="g2b_result.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
