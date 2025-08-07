import asyncio
from playwright.async_api import async_playwright, TimeoutError

async def run_crawler_async(query, browser_executable_path):
    """Playwright를 사용해 비동기적으로 크롤링을 수행하는 내부 함수 (최종 안정화 및 상세 로깅)"""
    browser = None
    print("--- 크롤러 시작 ---")
    try:
        async with async_playwright() as p:
            print("1. Playwright 컨텍스트 시작")
            browser = await p.chromium.launch(headless=True, executable_path=browser_executable_path, args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--single-process', '--no-zygote'])
            print("2. 브라우저 실행 완료")
            context = await browser.new_context()
            page = await context.new_page()
            print("3. 새 페이지 생성 완료")

            await page.goto("https://shop.g2b.go.kr/", timeout=60000)
            print("4. 초기 페이지 접속 성공")
            print(f"   - 현재 URL: {page.url}")
            print(f"   - 현재 페이지 제목: '{await page.title()}'")

            try:
                await page.wait_for_load_state('networkidle', timeout=15000)
                print("5. 페이지 네트워크 안정화 완료")
            except TimeoutError:
                print("5. 페이지 네트워크 안정화 시간 초과. 계속 진행합니다.")
            except Exception as e:
                print(f"5. 페이지 로딩 중 예외 발생: {e}. 계속 진행합니다.")

            await asyncio.sleep(3)

            print("6. 팝업 닫기 시도")
            for _ in range(5):
                popups = await page.query_selector_all("div[id^='mf_wfm_container_wq_uuid_'][class*='w2popup_window']")
                if not popups: break
                for popup in popups:
                    try:
                        button = await popup.query_selector("button[class*='w2window_close']")
                        if button and await button.is_visible(): await button.click(); print("   - 팝업 닫기 버튼 클릭")
                    except Exception: pass
            print("7. 팝업 닫기 완료")

            print("8. '제안공고목록' 버튼 클릭 시도")
            await page.get_by_role("link", name="제안공고목록").click()
            print("   - 성공")

            await page.wait_for_load_state('networkidle', timeout=15000)
            print("9. '제안공고목록' 페이지 로딩 완료")

            print("10. '3개월' 라디오 버튼 클릭 시도")
            await page.get_by_label("3개월").check()
            print("   - 성공")

            print(f"11. 검색어 '{query}' 입력 시도")
            await page.get_by_placeholder("제안공고명을 입력하세요").fill(query)
            print("   - 성공")

            print("12. 표시 수 '100'개 선택 시도")
            await page.locator('select[id*="RecordCountPerPage"]').select_option("100")
            print("   - 성공")

            print("13. '적용' 버튼 클릭 시도")
            await page.get_by_role("button", name="적용").click(no_wait_after=True)
            print("   - 클릭 동작 수행 완료. 이제 결과 로딩을 기다립니다.")

            print("14. 검색 결과 테이블이 나타날 때까지 대기 (최대 60초)")
            await page.wait_for_selector('table[id$="grdPrpsPbanc_body_table"]', timeout=60000)
            print("15. 검색 결과 로딩 완료. 테이블 파싱 시작.")
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

                headers = ["No", "제안공고번호", "수요기관", "제안공고명", "공고게시일자", "공고마감일시", "공고상태", "사유", "기타"]
                if data and len(data[0]) < len(headers): headers = headers[:len(data[0])]
                print(f"   - 성공: {len(data)}개의 행을 찾음")
            
            return headers, data

    except Exception as e:
        print(f"[CRITICAL ERROR] 크롤링 중 예외 발생: {e}")
        return None, None
    finally:
        if browser: await browser.close(); print("--- 브라우저 종료, 크롤러 끝 ---")

def run_g2b_crawler(query="컴퓨터", browser_executable_path=None):
    """어디서든 일관되게 동작하는 크롤러 실행 함수"""
    if not browser_executable_path: raise ValueError("Browser executable path was not provided.")
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
