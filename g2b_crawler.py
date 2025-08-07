import asyncio
from playwright.async_api import async_playwright, TimeoutError

async def run_crawler_async(query, browser_executable_path):
    """지능형 대기 루프를 사용하여 안정성을 극대화한 최종 크롤러"""
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

            # --- 지능형 대기 루프 시작 ---
            print("6. 팝업을 닫고 '제안공고목록' 버튼이 나타날 때까지 대기합니다.")
            proposal_button = page.get_by_role("link", name="제안공고목록")
            
            for i in range(15): # 최대 30초간 시도
                try:
                    # 버튼이 보이면 루프를 탈출하고 성공 처리
                    if await proposal_button.is_visible():
                        print(f"   - '제안공고목록' 버튼 발견! (시도 {i+1})")
                        break
                    
                    # 버튼이 안 보이면, 팝업을 닫으려고 시도
                    popups = await page.locator("div[id*='w2popup_window']").all()
                    if popups:
                        print(f"   - 팝업 발견. 닫기를 시도합니다.")
                        for popup in popups:
                            close_btn = popup.locator("button[class*='w2window_close']")
                            if await close_btn.is_visible():
                                await close_btn.click(timeout=5000)
                                print("     - 팝업 닫기 버튼 클릭 성공.")
                    else:
                        print(f"   - 팝업 없음. 버튼을 기다립니다. (시도 {i+1})")

                    await page.wait_for_timeout(1000) # 1초 대기 후 재시도

                except Exception as e:
                    print(f"   - 대기 중 오류 발생: {e}")
                    await page.wait_for_timeout(1000)
            
            if not await proposal_button.is_visible():
                raise Exception("'제안공고목록' 버튼을 최종적으로 찾지 못했습니다.")

            print("7. '제안공고목록' 버튼 클릭")
            await proposal_button.click()
            print("   - 성공")

            # --- iframe 처리 시작 ---
            print("8. 제안공고목록 iframe 대기 및 진입")
            frame_locator = page.frame_locator('div[id*="popPrpbList"] iframe')
            await frame_locator.locator('input[title="3개월"]').wait_for(timeout=30000)
            print("   - iframe 진입 성공!")

            print("9. '3개월' 라디오 버튼 클릭")
            await frame_locator.locator('input[title="3개월"]').click()
            print("   - 성공")

            print(f"10. 검색어 '{query}' 입력")
            await frame_locator.locator('td[data-title="제안공고명"] input[type="text"]').fill(query)
            print("   - 성공")

            print("11. 표시 수 '100'개 선택")
            await frame_locator.locator('select[id*="RecordCountPerPage"]').select_option("100")
            print("   - 성공")

            print("12. '적용' 버튼 클릭")
            await frame_locator.locator('input[type="button"][value="적용"]').click(no_wait_after=True)
            print("   - 클릭 동작 수행 완료. 이제 결과 로딩을 기다립니다.")

            print("13. 검색 결과 테이블 대기 (최대 60초)")
            await frame_locator.locator('table[id$="grdPrpsPbanc_body_table"]').wait_for(timeout=60000)
            print("14. 검색 결과 로딩 완료. 테이블 파싱 시작.")
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
