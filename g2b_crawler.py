import asyncio
from playwright.async_api import async_playwright

async def run_crawler_async(query, browser_executable_path):
    """Playwright를 사용해 비동기적으로 크롤링을 수행하는 내부 함수 (상세 로깅 추가)"""
    browser = None
    print("--- 크롤러 시작 ---")
    try:
        async with async_playwright() as p:
            print("1. Playwright 컨텍스트 시작")
            browser = await p.chromium.launch(
                headless=True,
                executable_path=browser_executable_path,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--single-process',
                    '--no-zygote'
                ]
            )
            print("2. 브라우저 실행 완료")
            context = await browser.new_context()
            page = await context.new_page()
            print("3. 새 페이지 생성 완료")

            await page.goto("https://shop.g2b.go.kr/", timeout=60000)
            print("4. 초기 페이지 접속 성공")
            await page.wait_for_load_state('networkidle', timeout=20000)
            print("5. 페이지 네트워크 안정화 완료")
            await asyncio.sleep(3)

            # --- 이하 크롤링 상세 로직 ---
            print("6. 팝업 닫기 시도")
            for i in range(5):
                popup_divs = await page.query_selector_all("div[id^='mf_wfm_container_wq_uuid_'][class*='w2popup_window']")
                if not popup_divs:
                    print(f"   - 팝업 없음 (시도 {i+1})")
                    break
                
                closed = False
                for popup in popup_divs:
                    try:
                        close_button = await popup.query_selector("button[class*='w2window_close']")
                        if close_button and await close_button.is_visible():
                            await close_button.click()
                            print("   - 일반 팝업 닫기 버튼 클릭")
                            await asyncio.sleep(0.3)
                            closed = True
                    except Exception:
                        pass # 오류 무시
                if not closed:
                    break # 닫을 팝업이 더 이상 없음
            print("7. 팝업 닫기 완료")
            await page.keyboard.press('End')
            await asyncio.sleep(1)

            print("8. '제안공고목록' 버튼 클릭 시도")
            btn_selectors = [
                'a[id^="mf_wfm_container_wq_uuid_"][id$="_btnPrpblist"]',
                'a[title*="제안공고목록"]',
                'a:has-text("제안공고목록")',
            ]
            clicked = False
            for sel in btn_selectors:
                try:
                    elem = await page.query_selector(sel)
                    if elem and await elem.is_visible():
                        await elem.scroll_into_view_if_needed()
                        await elem.click()
                        clicked = True
                        print(f"   - 성공: 선택자 '{sel}'")
                        break
                except Exception:
                    continue
            
            if not clicked:
                print("   - 실패: '제안공고목록' 버튼을 찾지 못함")

            await page.wait_for_load_state('networkidle', timeout=10000)
            print("9. '제안공고목록' 페이지 로딩 완료")

            print("10. '3개월' 라디오 버튼 클릭 시도")
            radio_3month = await page.query_selector('input[title="3개월"]')
            if radio_3month:
                await radio_3month.click()
                print("   - 성공")
                await asyncio.sleep(1)

            print(f"11. 검색어 '{query}' 입력 시도")
            input_elem = await page.query_selector('td[data-title="제안공고명"] input[type="text"]')
            if input_elem:
                await input_elem.fill(query)
                print("   - 성공")
                await asyncio.sleep(0.5)

            print("12. 표시 수 '100'개 선택 시도")
            select_elem = await page.query_selector('select[id*="RecordCountPerPage"]')
            if select_elem:
                await select_elem.select_option("100")
                print("   - 성공")
                await asyncio.sleep(1)

            print("13. '적용/검색' 버튼 클릭 시도")
            search_button = await page.query_selector('input[type="button"][value="적용"], input[type="button"][value="검색"]')
            if search_button:
                await search_button.click()
                print("   - 성공")

            await page.wait_for_load_state('networkidle', timeout=10000)
            print("14. 검색 결과 로딩 완료")

            print("15. 테이블 파싱 시도")
            await page.wait_for_selector('table[id$="grdPrpsPbanc_body_table"]', timeout=10000)
            table_elem = await page.query_selector('table[id$="grdPrpsPbanc_body_table"]')
            headers = []
            data = []
            if table_elem:
                rows = await table_elem.query_selector_all('tr')
                for row in rows:
                    tds = await row.query_selector_all('td')
                    cols = [await td.inner_text() for td in tds]
                    if cols and any(c.strip() for c in cols):
                        data.append([c.strip() for c in cols])

                headers = ["No", "제안공고번호", "수요기관", "제안공고명",
                           "공고게시일자", "공고마감일시", "공고상태", "사유", "기타"]
                if data and len(data[0]) < len(headers):
                    headers = headers[:len(data[0])]
                print(f"   - 성공: {len(data)}개의 행을 찾음")
            
            return headers, data

    except Exception as e:
        print(f"[CRITICAL ERROR] 크롤링 중 예외 발생: {e}")
        return None, None
    finally:
        if browser:
            await browser.close()
            print("--- 브라우저 종료, 크롤러 끝 ---")

def run_g2b_crawler(query="컴퓨터", browser_executable_path=None):
    """어디서든 일관되게 동작하는 크롤러 실행 함수""" 
    if not browser_executable_path:
        raise ValueError("Browser executable path was not provided.")

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import nest_asyncio
        nest_asyncio.apply()
        return loop.run_until_complete(run_crawler_async(query, browser_executable_path))
    else:
        return asyncio.run(run_crawler_async(query, browser_executable_path))
