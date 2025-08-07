import asyncio
from playwright.async_api import async_playwright, TimeoutError

async def run_crawler_async(query, browser_executable_path):
    """3단계 대기(팝업->iframe->내용물)로 안정성을 극대화한 최종 크롤러"""
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
            
            try:
                await page.wait_for_load_state('networkidle', timeout=15000)
                print("5. 페이지 네트워크 안정화 완료")
            except TimeoutError:
                print("5. 페이지 네트워크 안정화 시간 초과. 계속 진행합니다.")

            await asyncio.sleep(1)

            print("6. '제안공고목록' 버튼 클릭")
            # 팝업이 뜰 수 있으므로, 클릭 후 네비게이션을 기다리지 않습니다.
            await page.get_by_role("link", name="제안공고목록").click(no_wait_after=True)
            print("   - 성공")

            # --- 3단계 대기 로직 시작 (가장 중요한 부분) ---
            
            # 1단계: 팝업창(div) 자체가 나타날 때까지 대기
            print("7. 팝업창(div)이 나타날 때까지 대기")
            popup_div_selector = 'div[id*="popPrpbList"]'
            await page.wait_for_selector(popup_div_selector, state='visible', timeout=30000)
            print("   - 팝업창(div) 발견!")

            # 2단계: 해당 팝업창 내부의 iframe을 찾음
            print("8. iframe으로 제어권 전환")
            frame_locator = page.frame_locator(f'{popup_div_selector} iframe')
            print("   - iframe 찾음!")

            # 3단계: iframe 내부의 내용물('3개월' 버튼)이 로드될 때까지 대기
            print("9. iframe 내부 콘텐츠가 로드될 때까지 대기")
            await frame_locator.locator('input[title="3개월"]').wait_for(timeout=30000)
            print("   - iframe 내용물 로드 완료!")

            # --- 이제부터 모든 선택은 frame_locator를 통해 수행합니다. ---
            
            print("10. '3개월' 라디오 버튼 클릭")
            await frame_locator.locator('input[title="3개월"]').click()
            print("   - 성공")

            print(f"11. 검색어 '{query}' 입력")
            await frame_locator.locator('td[data-title="제안공고명"] input[type="text"]').fill(query)
            print("   - 성공")

            print("12. 표시 수 '100'개 선택")
            await frame_locator.locator('select[id*="RecordCountPerPage"]').select_option("100")
            print("   - 성공")

            print("13. '적용' 버튼 클릭")
            await frame_locator.locator('input[type="button"][value="적용"]').click(no_wait_after=True)
            print("   - 클릭 동작 수행 완료. 이제 결과 로딩을 기다립니다.")

            print("14. 검색 결과 테이블 대기 (최대 60초)")
            await frame_locator.locator('table[id$="grdPrpsPbanc_body_table"]').wait_for(timeout=60000)
            print("15. 검색 결과 로딩 완료. 테이블 파싱 시작.")
            table_elem = frame_locator.locator('table[id$="grdPrpsPbanc_body_table"]')
            headers = []
            data = []
            rows = await table_elem.locator('tr').all()
            for row in rows:
                tds = await row.locator('td').all()
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
