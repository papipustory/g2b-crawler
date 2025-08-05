import streamlit as st
import asyncio
import nest_asyncio
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import os
import traceback
import openpyxl
from openpyxl.styles import Alignment
from playwright.async_api import async_playwright

# 이벤트 루프 충돌 방지
nest_asyncio.apply()

# 상태 표시용 글로벌 변수
ui_status = None
progress_bar = None

# ===============================
# [함수] 상태 업데이트
# ===============================
def update_status(message, progress=None):
    """UI 상태와 진행률 갱신"""
    global ui_status, progress_bar
    if ui_status:
        ui_status.text(message)
    if progress_bar and progress is not None:
        progress_bar.progress(progress)

# ===============================
# [함수] 공지팝업 닫기
# ===============================
async def close_notice_popups(page):
    try:
        for _ in range(5):
            closed_any = False
            # 메인 페이지 팝업
            popups = await page.query_selector_all("div[id*='_header'][title='공지팝업']")
            for popup in popups:
                close_btn = await popup.query_selector("button.w2window_close")
                if close_btn:
                    await close_btn.click()
                    closed_any = True
                    await asyncio.sleep(0.2)
            # iframe 내부 팝업
            for frame in page.frames:
                popups_iframe = await frame.query_selector_all("div[id*='_header'][title='공지팝업']")
                for popup in popups_iframe:
                    close_btn = await popup.query_selector("button.w2window_close")
                    if close_btn:
                        await close_btn.click()
                        closed_any = True
                        await asyncio.sleep(0.2)
            if not closed_any:
                break
    except Exception as e:
        print(f"[close_notice_popups] 오류: {e}")

# ===============================
# [함수] 요소 대기 후 클릭
# ===============================
async def wait_and_click(page, selector, desc, timeout=10000, scroll=True):
    try:
        await page.wait_for_selector(selector, timeout=timeout, state="visible")
        elem = await page.query_selector(selector)
        if elem:
            if scroll:
                await elem.scroll_into_view_if_needed()
                await asyncio.sleep(0.02)
            await elem.click()
            return True
        return False
    except:
        return False

# ===============================
# 메인 크롤러
# ===============================
async def main():
    browser = None
    try:
        async with async_playwright() as p:
            update_status("브라우저 시작 중...", 10)
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-software-rasterizer"]
            )
            context = await browser.new_context()
            page = await context.new_page()

            update_status("나라장터 접속 중...", 20)
            await page.goto("https://shop.g2b.go.kr/", timeout=10000)
            await page.wait_for_load_state('networkidle', timeout=10000)
            await asyncio.sleep(3)

            update_status("공지팝업 닫는 중...", 30)
            await close_notice_popups(page)

            update_status("페이지 스크롤 중...", 40)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)

            update_status("'제안공고목록' 클릭 중...", 50)
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

            update_status("조회 기간 설정 중...", 55)
            await page.evaluate("""
                const radio = document.querySelector('input[title="3개월"]');
                if (radio) {
                    radio.checked = true;
                    const event = new Event('click', { bubbles: true });
                    radio.dispatchEvent(event);
                }
            """)
            await asyncio.sleep(1)

            update_status("검색어 입력 중...", 60)
            input_elem = await page.query_selector('td[data-title="제안공고명"] input[type="text"]')
            if input_elem:
                await input_elem.fill('컴퓨터', timeout=1000)

            update_status("표시 건수 변경 중...", 65)
            await page.evaluate("""
                const selects = document.querySelectorAll('select[id*="RecordCountPerPage"]');
                selects.forEach(select => {
                    select.value = "100";
                    const event = new Event('change', { bubbles: true });
                    select.dispatchEvent(event);
                });
            """)
            await asyncio.sleep(1)

            update_status("검색 실행 중...", 70)
            await wait_and_click(page, 'input[type="button"][value="적용"]', "적용버튼", scroll=False)
            await wait_and_click(page, 'input[type="button"][value="검색"]', "검색버튼", scroll=False)
            await asyncio.sleep(0.8)

            update_status("결과 수집 중...", 80)
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

            update_status("완료!", 100)
            await asyncio.sleep(1)

    except Exception as e:
        print(f"Error occurred: {e}")
    finally:
        if browser:
            await browser.close()

# ===============================
# Streamlit UI
# ===============================
st.set_page_config(page_title="나라장터 제안공고 크롤러", layout="centered")
st.title("💻 나라장터 제안공고 크롤러")
st.caption("단계별 진행 상황을 표시합니다.")

progress_bar = st.empty()
ui_status = st.empty()

def run_crawler_async():
    try:
        asyncio.run(main())
    except Exception:
        traceback.print_exc()
        raise

if st.button("📦 크롤링 시작"):
    progress_bar.progress(0)
    ui_status.text("대기 중...")

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run_crawler_async)
        while not future.done():
            pass
        try:
            future.result()
            st.success("✅ 크롤링 완료")
        except Exception as e:
            st.error(f"❌ 에러 발생: {e}")

excel_file = "g2b_result.xlsx"
if os.path.exists(excel_file):
    with open(excel_file, "rb") as f:
        st.download_button(
            label="📥 크롤링 결과 다운로드",
            data=f,
            file_name="g2b_result.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
