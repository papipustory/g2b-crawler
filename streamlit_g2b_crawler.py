import streamlit as st
import asyncio
import pandas as pd
import openpyxl
from openpyxl.styles import Alignment
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
import traceback
import logging

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="나라장터 제안공고 크롤러", layout="centered")

st.title("💻 나라장터 제안공고 크롤링")

# 디버그 정보 표시
if st.checkbox("🔍 디버그 모드 활성화"):
    st.session_state.debug_mode = True
else:
    st.session_state.debug_mode = False

def debug_log(message):
    """디버그 로그 출력"""
    if st.session_state.get('debug_mode', False):
        st.write(f"🔍 DEBUG: {message}")
    print(f"DEBUG: {message}")

# Playwright 브라우저 설치 확인 및 설치
@st.cache_resource
def ensure_playwright_installed():
    try:
        import subprocess
        debug_log("Playwright 설치 확인 시작...")
        result = subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], 
                              capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            st.error(f"Playwright 설치 실패: {result.stderr}")
            debug_log(f"Playwright 설치 실패: {result.stderr}")
            return False
        debug_log("Playwright 설치 완료")
        return True
    except Exception as e:
        st.error(f"Playwright 설치 중 오류: {e}")
        debug_log(f"Playwright 설치 오류: {e}")
        return False

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

async def find_and_click_by_text(page, text, element_type="a"):
    """텍스트로 요소를 찾아서 클릭"""
    try:
        debug_log(f"텍스트 검색 시작: '{text}' ({element_type})")
        # 다양한 방법으로 텍스트 검색
        selectors = [
            f'{element_type}:has-text("{text}")',
            f'{element_type}[title*="{text}"]',
            f'{element_type}[alt*="{text}"]',
            f'//{element_type}[contains(text(), "{text}")]',
            f'//{element_type}[contains(@title, "{text}")]'
        ]
        
        for selector in selectors:
            try:
                debug_log(f"셀렉터 시도: {selector}")
                if selector.startswith('//'):
                    # XPath 사용
                    elements = await page.query_selector_all(f'xpath={selector}')
                else:
                    elements = await page.query_selector_all(selector)
                
                debug_log(f"찾은 요소 수: {len(elements)}")
                
                for i, element in enumerate(elements):
                    try:
                        await element.scroll_into_view_if_needed()
                        await asyncio.sleep(0.5)
                        await element.click()
                        debug_log(f"성공: '{text}' 텍스트로 클릭 (요소 {i+1})")
                        return True
                    except Exception as e:
                        debug_log(f"요소 {i+1} 클릭 실패: {e}")
                        continue
            except Exception as e:
                debug_log(f"셀렉터 실패 {selector}: {e}")
                continue
        
        debug_log(f"텍스트 검색 실패: '{text}'")
        return False
    except Exception as e:
        debug_log(f"텍스트 검색 오류: {e}")
        return False

async def main():
    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            # 사이트 접속 및 충분한 대기
            await page.goto("https://shop.g2b.go.kr/", timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=30000)
            await asyncio.sleep(3)

            # 팝업 닫기
            await close_notice_popups(page)
            await asyncio.sleep(1)

            # 스크롤 하단
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
            await asyncio.sleep(0.3)

            # 3개월 라디오 버튼 선택
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
                await input_elem.fill('컴퓨터', timeout=1000)

            # 표시수 드롭다운 강제 설정
            await page.evaluate("""
                const selects = document.querySelectorAll('select[id*="RecordCountPerPage"]');
                selects.forEach(select => {
                    select.value = "100";
                    const event = new Event('change', { bubbles: true });
                    select.dispatchEvent(event);
                });
            """)
            await asyncio.sleep(1)

            # 적용/검색 버튼 클릭
            await wait_and_click(page, 'input[type="button"][value="적용"]', "적용버튼", scroll=False)
            await wait_and_click(page, 'input[type="button"][value="검색"]', "검색버튼", scroll=False)
            await asyncio.sleep(0.8)

            # 테이블 데이터 추출
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
                    col_widths = [3.5, 17, 44, 55, 15, 17.5, 17, 17, 17]
                    for i, width in enumerate(col_widths, start=1):
                        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = width
                    wb.save(file_path)
                    print("Excel saved and formatting applied.")

            await asyncio.sleep(2)

    except Exception as e:
        print(f"Error occurred: {e}")

    finally:
        if browser:
            await browser.close()

if st.button("크롤링 시작"):
    # Playwright 설치 확인
    if not ensure_playwright_installed():
        st.stop()
    st.info("크롤링을 시작합니다. 잠시만 기다려 주세요... (1-2분 소요)")
    progress_bar = st.progress(0)
    status_text = st.empty()

    # 별도 스레드에서 크롤링 실행
    with ThreadPoolExecutor(max_workers=1) as executor:
        try:
            status_text.text("브라우저 시작 중...")
            progress_bar.progress(10)
            future = executor.submit(lambda: asyncio.run(main()))
            # ... (진행상황 표시 등)
            result = future.result(timeout=180)
            # ... (결과 표시)
        except Exception as e:
            st.error(f"❌ 실행 중 오류: {str(e)}")
        finally:
            progress_bar.empty()
            status_text.empty()
