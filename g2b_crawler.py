import asyncio
from playwright.async_api import async_playwright

async def run_crawler_async(query, browser_executable_path):
    """Playwright를 사용해 비동기적으로 크롤링을 수행하는 내부 함수"""
    browser = None
    try:
        async with async_playwright() as p:
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
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto("https://shop.g2b.go.kr/", timeout=60000)
            await page.wait_for_load_state('networkidle', timeout=20000)
            await asyncio.sleep(3)

            # --- 이하 크롤링 상세 로직 ---
            # 팝업 닫기
            for _ in range(5):
                popup_divs = await page.query_selector_all("div[id^='mf_wfm_container_wq_uuid_'][class*='w2popup_window']")
                closed = False
                for popup in popup_divs:
                    try:
                        for sel in ["button[class*='w2window_close']", "input[type='button'][value='닫기']"]:
                            btn = await popup.query_selector(sel)
                            if btn and await btn.is_visible():
                                await btn.click()
                                await asyncio.sleep(0.2)
                                closed = True
                                break
                        checkbox = await popup.query_selector("input[type='checkbox'][title*='오늘 하루']")
                        if checkbox and await checkbox.is_visible():
                            await checkbox.check()
                            await asyncio.sleep(0.1)
                            btn = await popup.query_selector("input[type='button'][value='닫기']")
                            if btn and await btn.is_visible():
                                await btn.click()
                                closed = True
                                break
                    except Exception:
                        continue
                if not closed:
                    break
                await asyncio.sleep(0.5)
            await page.keyboard.press('End')
            await asyncio.sleep(1)

            # 제안공고목록 진입
            btn_selectors = [
                'a[id^="mf_wfm_container_wq_uuid_"][id$="_btnPrpblist"]',
                'a[title*="제안공고목록"]',
                'a:has-text("제안공고목록")',
                'div.w2textbox:text("제안공고목록")',
            ]
            clicked = False
            for sel in btn_selectors:
                try:
                    await page.wait_for_selector(sel, timeout=5000, state="visible")
                    elem = await page.query_selector(sel)
                    if elem and await elem.is_visible():
                        await elem.scroll_into_view_if_needed()
                        await asyncio.sleep(0.1)
                        await elem.click()
                        clicked = True
                        break
                except Exception:
                    continue
            
            if not clicked:
                print("Could not find '제안공고목록' button.")

            await asyncio.sleep(1)

            # 3개월 라디오 버튼 클릭
            radio_3month = await page.query_selector('input[title="3개월"]')
            if radio_3month:
                await radio_3month.click()
                await asyncio.sleep(1)

            # 검색어 입력
            input_elem = await page.query_selector('td[data-title="제안공고명"] input[type="text"]')
            if input_elem:
                await input_elem.fill(query)
                await asyncio.sleep(0.5)

            # 표시수 100개 선택
            select_elem = await page.query_selector('select[id*="RecordCountPerPage"]')
            if select_elem:
                await select_elem.select_option("100")
                await asyncio.sleep(1)

            # 적용/검색 버튼 클릭
            for sel in ['input[type="button"][value="적용"]', 'input[type="button"][value="검색"]']:
                try:
                    await page.wait_for_selector(sel, timeout=3000, state="visible")
                    elem = await page.query_selector(sel)
                    if elem:
                        await elem.click()
                        await asyncio.sleep(1)
                except Exception:
                    continue

            # 테이블 파싱
            await page.wait_for_selector('table[id$="grdPrpsPbanc_body_table"]', timeout=10000)
            table_elem = await page.query_selector('table[id$="grdPrpsPbanc_body_table"]')
            headers = []
            data = []
            if table_elem:
                rows = await table_elem.query_selector_all('tr')
                for row in rows:
                    tds = await row.query_selector_all('td')
                    cols = []
                    for td in tds:
                        text = await td.inner_text()
                        cols.append(text.strip())
                    if cols and any(cols):
                        data.append(cols)

                headers = ["No", "제안공고번호", "수요기관", "제안공고명",
                           "공고게시일자", "공고마감일시", "공고상태", "사유", "기타"]
                if data and len(data[0]) < len(headers):
                    headers = headers[:len(data[0])]
            
            return headers, data

    except Exception as e:
        print(f"[ERROR] An error occurred during crawling: {e}")
        return None, None
    finally:
        if browser:
            await browser.close()

def run_g2b_crawler(query="컴퓨터", browser_executable_path=None):
    """
    어디서든 일관되게 동작하는 크롤러 실행 함수.
    app.py로부터 브라우저 경로를 전달받습니다.
    """
    if not browser_executable_path:
        raise ValueError("Browser executable path was not provided.")

    try:
        # 현재 실행 중인 이벤트 루프를 확인합니다.
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    # Streamlit/Jupyter와 같이 이미 이벤트 루프가 실행 중인 환경
    if loop and loop.is_running():
        import nest_asyncio
        nest_asyncio.apply()
        # 비동기 함수를 현재 루프에서 실행합니다.
        return loop.run_until_complete(run_crawler_async(query, browser_executable_path))
    # 일반 Python 스크립트 환경
    else:
        # 새로운 이벤트 루프를 만들어 비동기 함수를 실행합니다.
        return asyncio.run(run_crawler_async(query, browser_executable_path))
