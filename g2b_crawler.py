import asyncio
from playwright.async_api import async_playwright, TimeoutError

async def run_crawler_async(query, browser_executable_path):
    """iframe의 주소를 찾기 위한 디버깅용 크롤러"""
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

            # 잠시 기다려 iframe이 로드될 시간을 줍니다.
            await asyncio.sleep(5)
            print("9. iframe 로드 대기 완료")

            # --- iframe의 주소를 찾기 위해 현재 페이지의 전체 HTML을 출력합니다. ---
            print("\n--- 페이지의 모든 iframe을 찾기 위해 현재 HTML 구조를 출력합니다. ---")
            html_content = await page.content()
            print(html_content)
            print("--- HTML 구조 출력 완료 ---")

            # 여기서 일단 실행을 멈추고 로그를 확인합니다.
            return None, None

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
