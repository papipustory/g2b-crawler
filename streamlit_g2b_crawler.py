import asyncio
import nest_asyncio
import pandas as pd
import os
import openpyxl
from openpyxl.styles import Alignment
from playwright.async_api import async_playwright

# Cloud에서 asyncio 중첩 허용
nest_asyncio.apply()

# ===============================
# 팝업 닫기 함수
# ===============================
async def close_notice_popups(page):
    print("[DEBUG] close_notice_popups() 시작")
    try:
        for _ in range(5):
            closed_any = False

            # 메인 페이지 팝업
            popups = await page.query_selector_all("div[id*='_header'][title='공지팝업']")
            for popup in popups:
                try:
                    close_btn = await popup.query_selector("button.w2window_close")
                    if close_btn:
                        await close_btn.click()
                        closed_any = True
                        await asyncio.sleep(0.2)
                except:
                    continue

            # iframe 내부 팝업
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

            if not closed_any:
                break
    except Exception as e:
        print(f"[close_notice_popups] 오류: {e}")
    print("[DEBUG] close_notice_popups() 종료")

# ===============================
# 요소 대기 후 클릭
# ===============================
async def wait_and_click(page, selector, desc, timeout=30000, scroll=True):
    try:
        await page.wait_for_selector(selector, timeout=timeout, state="visible")
        elem = await page.query_selector(selector)
        if elem and await elem.is_visible():
            if scroll:
                await elem.scroll_into_view_if_needed()
                await asyncio.sleep(0.02)
            await elem.click()
            print(f"[DEBUG] {desc} 클릭 성공")
            return True
        print(f"[DEBUG] {desc} 클릭 실패(안보임)")
        return False
    except Exception as e:
        print(f"[DEBUG] {desc} 클릭 실패(예외: {e})")
        return False

# ===============================
# 메인 크롤링 함수
# ===============================
async def main():
    print("[DEBUG] main() 시작")
    browser = None
    try:
        async with async_playwright() as p:
            print("[DEBUG] Playwright 초기화 완료")
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox", 
                    "--disable-dev-shm-usage", 
                    "--disable-software-rasterizer",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security"
                ]
            )
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()

            # 사이트 접속
            print("[DEBUG] 나라장터 접속 시도")
            await page.goto("https://shop.g2b.go.kr/", timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=30000)
            await asyncio.sleep(5)

            # 팝업 닫기
            await close_notice_popups(page)

            # 스크롤
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)

            # 제안공고목록 클릭
            btn_selectors = [
                'a[id^="mf_wfm_container_wq_uuid_"][id$="_btnPrpblist"]',
                'a[title*="제안공고목록"]',
                'a:has-text("제안공고목록")',
                '//a[contains(text(), "제안공고목록")]',
                'div.w2textbox:text("제안공고목록")',
            ]
            
            clicked = False
            for sel in btn_selectors:
                if await wait_and_click(page, sel, "제안공고목록 버튼"):
                    clicked = True
                    break
            
            if not clicked:
                print("[ERROR] 제안공고목록 버튼을 찾을 수 없습니다.")
                return

            await asyncio.sleep(3)

            # 조회 기간 3개월
            await page.evaluate("""
                const radio = document.querySelector('input[title="3개월"]');
                if (radio) {
                    radio.checked = true;
                    const event = new Event('click', { bubbles: true });
                    radio.dispatchEvent(event);
                }
            """)
            await asyncio.sleep(2)

            # 검색어 입력
            input_elem = await page.query_selector('td[data-title="제안공고명"] input[type="text"]')
            if input_elem:
                await input_elem.fill('컴퓨터')
                await asyncio.sleep(1)

            # 표시 건수 100건
            await page.evaluate("""
                const selects = document.querySelectorAll('select[id*="RecordCountPerPage"]');
                selects.forEach(select => {
                    select.value = "100";
                    const event = new Event('change', { bubbles: true });
                    select.dispatchEvent(event);
                });
            """)
            await asyncio.sleep(2)

            # 적용 & 검색
            await wait_and_click(page, 'input[type="button"][value="적용"]', "적용버튼", scroll=False)
            await asyncio.sleep(1)
            await wait_and_click(page, 'input[type="button"][value="검색"]', "검색버튼", scroll=False)
            await asyncio.sleep(5)

            # 테이블 수집
            print("[DEBUG] 테이블 수집 시작")
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

                # DataFrame 저장
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

                    # 엑셀 서식
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
                    
                    print(f"[DEBUG] 엑셀 파일 저장 완료: {file_path}")
                else:
                    print("[WARNING] 수집된 데이터가 없습니다.")
            else:
                print("[ERROR] 테이블을 찾을 수 없습니다.")

            await asyncio.sleep(2)

    except Exception as e:
        print(f"[DEBUG] main() 오류: {e}")
        import traceback
        print(traceback.format_exc())

    finally:
        if browser:
            await browser.close()
        print("[DEBUG] main() 종료")
