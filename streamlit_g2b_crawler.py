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

# ===============================
# asyncio 이벤트 루프 충돌 방지
# (Streamlit 환경에서 필수)
# ===============================
nest_asyncio.apply()

# ===============================
# [함수] 모든 '공지팝업' 닫기
#  - 메인 DOM과 iframe 내부를 모두 탐색
#  - 최대 5번 반복 (팝업 여러 개 연속 처리)
# ===============================
async def close_notice_popups(page):
    """모든 '공지팝업' 닫기 (iframe 포함)"""
    try:
        for _ in range(5):  # 최대 5회 반복 시도
            closed_any = False

            # 1) 메인 페이지 팝업 탐색
            popups = await page.query_selector_all("div[id*='_header'][title='공지팝업']")
            for popup in popups:
                try:
                    close_btn = await popup.query_selector("button.w2window_close")
                    if close_btn:
                        await close_btn.click()
                        closed_any = True
                        await asyncio.sleep(0.2)  # 닫기 후 대기
                except:
                    continue

            # 2) iframe 내부 팝업 탐색
            frames = page.frames
            for frame in frames:
                try:
                    popups_iframe = await frame.query_selector_all("div[id*='_header'][title='공지팝업']")
                    for popup in popups_iframe:
                        try:
                            close_btn = await popup.query_selector("button.w2window_close")
                            if close_btn:
                                await close_btn.click()
                                closed_any = True
                                await asyncio.sleep(0.2)
                        except:
                            continue
                except:
                    continue

            # 닫은 팝업이 하나도 없으면 종료
            if not closed_any:
                break

    except Exception as e:
        print(f"[close_notice_popups] 팝업 닫기 오류: {e}")

# ===============================
# [함수] 요소 대기 후 클릭
#  - selector와 설명(desc) 지정
#  - scroll=True 시 스크롤 후 클릭
# ===============================
async def wait_and_click(page, selector, desc, timeout=10000, scroll=True):
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

# ===============================
# 메인 크롤러 함수
# ===============================
async def main():
    browser = None
    try:
        async with async_playwright() as p:
            # 1️⃣ 브라우저 실행 (Cloud 최적화 옵션 적용)
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-software-rasterizer"]
            )
            context = await browser.new_context()
            page = await context.new_page()

            # 2️⃣ 나라장터 메인 페이지 접속
            await page.goto("https://shop.g2b.go.kr/", timeout=10000)
            await page.wait_for_load_state('networkidle', timeout=10000)
            await asyncio.sleep(3)  # 초기 로딩 대기

            # 3️⃣ 공지팝업 닫기
            await close_notice_popups(page)

            # 4️⃣ 페이지 하단 스크롤 (추가 로딩 유도)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)

            # 5️⃣ '제안공고목록' 버튼 클릭 시도
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

            # 6️⃣ 조회 기간을 '3개월'로 설정
            await page.evaluate("""
                const radio = document.querySelector('input[title="3개월"]');
                if (radio) {
                    radio.checked = true;
                    const event = new Event('click', { bubbles: true });
                    radio.dispatchEvent(event);
                }
            """)
            await asyncio.sleep(1)

            # 7️⃣ 검색어 입력 ('컴퓨터')
            input_elem = await page.query_selector('td[data-title="제안공고명"] input[type="text"]')
            if input_elem:
                await input_elem.fill('컴퓨터', timeout=1000)

            # 8️⃣ 표시 건수를 100건으로 변경
            await page.evaluate("""
                const selects = document.querySelectorAll('select[id*="RecordCountPerPage"]');
                selects.forEach(select => {
                    select.value = "100";
                    const event = new Event('change', { bubbles: true });
                    select.dispatchEvent(event);
                });
            """)
            await asyncio.sleep(1)

            # 9️⃣ '적용' 버튼 클릭 → '검색' 버튼 클릭
            await wait_and_click(page, 'input[type="button"][value="적용"]', "적용버튼", scroll=False)
            await wait_and_click(page, 'input[type="button"][value="검색"]', "검색버튼", scroll=False)
            await asyncio.sleep(0.8)

            # 🔟 검색 결과 테이블 수집
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

                # 1️⃣1️⃣ DataFrame 변환 + 기존 엑셀과 병합
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

                    # 1️⃣2️⃣ 엑셀 서식 적용
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

            await asyncio.sleep(2)

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
st.caption("컴퓨터 관련 제안공고를 G2B에서 크롤링하여 다운로드합니다.")

progress_bar = st.empty()
status = st.empty()

# 크롤러 실행 함수
def run_crawler_async():
    try:
        asyncio.run(main())
    except Exception:
        traceback.print_exc()
        raise

# '크롤링 시작' 버튼 UI
if st.button("📦 크롤링 시작"):
    st.info("Playwright 크롤링을 실행 중입니다. 잠시 기다려 주세요.")
    progress_bar.progress(5)
    status.text("브라우저 시작 중...")

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run_crawler_async)
        while not future.done():
            progress_bar.progress(50)
            status.text("공고 수집 중...")

        try:
            future.result()
            progress_bar.progress(100)
            st.success("✅ 크롤링 완료")
        except Exception as e:
            st.error(f"❌ 에러 발생: {e}")
        finally:
            progress_bar.empty()
            status.empty()

# 다운로드 버튼
excel_file = "g2b_result.xlsx"
if os.path.exists(excel_file):
    with open(excel_file, "rb") as f:
        st.download_button(
            label="📥 크롤링 결과 다운로드",
            data=f,
            file_name="g2b_result.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
