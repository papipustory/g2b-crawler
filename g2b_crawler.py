# g2b_crawler.py - Streamlit Cloud 최적화 G2B 제안공고 크롤러 (3개월/100개/검색어 입력 복구)
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import pandas as pd
import os

async def run_crawler_async(query="컴퓨터", browser_executable_path=None):
    """
    Streamlit Cloud 환경 최적화 G2B 제안공고 크롤러 (검색어입력, 3개월, 100개 표준 로직 복구)
    :param query: 검색어 (예: "컴퓨터")
    :param browser_executable_path: Chromium 실행파일 경로 (없으면 자동 감지)
    :return: (headers, table_data) or (None, None)
    """
    browser = context = page = None

    try:
        async with async_playwright() as p:
            browser_args = [
                '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage',
                '--disable-gpu', '--single-process', '--no-zygote',
                '--disable-blink-features=AutomationControlled', '--window-size=1920,1080',
                '--start-maximized', '--disable-extensions', '--disable-images',
                '--disable-javascript-harmony-shipping', '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding', '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection'
            ]
            # 브라우저 실행
            if browser_executable_path:
                browser = await p.chromium.launch(
                    headless=True, executable_path=browser_executable_path,
                    args=browser_args, timeout=30000
                )
            else:
                browser = await p.chromium.launch(
                    headless=True, args=browser_args, timeout=30000
                )
            # 컨텍스트 및 페이지 생성
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='ko-KR', timezone_id='Asia/Seoul', ignore_https_errors=True,
                extra_http_headers={
                    'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Cache-Control': 'no-cache', 'Pragma': 'no-cache'
                }
            )
            # 자동화 탐지 우회
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = {runtime: {}, loadTimes: function(){}, csi: function(){}, app: {}};
                Object.defineProperty(navigator, 'plugins', {get: () => [
                    {name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer'},
                    {name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai'},
                    {name: 'Native Client', filename: 'internal-nacl-plugin'}
                ],});
                Object.defineProperty(navigator, 'languages', {get: () => ['ko-KR', 'ko', 'en-US', 'en'],});
                Object.defineProperty(navigator, 'platform', {get: () => 'Linux x86_64'});
                Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 4});
                Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
            """)
            page = await context.new_page()
            page.set_default_timeout(20000)
            page.set_default_navigation_timeout(40000)

            # 접속 시도 (복수 URL)
            urls_to_try = [
                "https://shop.g2b.go.kr/index.do",
                "https://shop.g2b.go.kr/",
                "https://www.g2b.go.kr/"
            ]
            page_loaded = False
            for url in urls_to_try:
                try:
                    response = await page.goto(url, wait_until='domcontentloaded', timeout=20000)
                    if response and response.status == 200:
                        try:
                            await page.wait_for_function(
                                """() => document.title.includes("나라장터") || document.title.includes("조달청") || document.title.toUpperCase().includes("G2B")""",
                                timeout=6000)
                        except PlaywrightTimeout:
                            pass
                        page_loaded = True
                        break
                except Exception:
                    continue
            if not page_loaded:
                await context.add_cookies([
                    {"name": "WMONID", "value": "streamlit_session", "domain": ".g2b.go.kr", "path": "/"},
                    {"name": "JSESSIONID", "value": "abcdef123456", "domain": ".g2b.go.kr", "path": "/"}
                ])
                await page.goto("https://shop.g2b.go.kr/index.do", wait_until='domcontentloaded')
                try:
                    await page.wait_for_function(
                        """() => document.title.includes("나라장터")""", timeout=6000)
                except PlaywrightTimeout:
                    pass

            # 팝업 닫기 (wait_for_selector로 감지)
            try:
                for _ in range(5):
                    btns = await page.query_selector_all('button.w2window_close, input[type="button"][value="닫기"]')
                    for btn in btns:
                        try:
                            if await btn.is_visible():
                                await btn.click()
                        except Exception:
                            continue
                    try:
                        await page.wait_for_selector('button.w2window_close, input[type="button"][value="닫기"]', timeout=500)
                    except PlaywrightTimeout:
                        break
            except Exception:
                pass

            # '제안공고목록' 버튼 클릭
            button_clicked = False
            btn_selectors = [
                'a[id^="mf_wfm_container_wq_uuid_"][id$="_btnPrpblist"]',
                'a[title*="제안공고목록"]',
                'a:has-text("제안공고목록")',
                'div.w2textbox:has-text("제안공고목록")',
                'a[href*="Prpblist"]',
                'a[onclick*="Prpblist"]'
            ]
            for sel in btn_selectors:
                try:
                    await page.wait_for_selector(sel, timeout=3000)
                    elem = await page.query_selector(sel)
                    if elem and await elem.is_visible():
                        await elem.scroll_into_view_if_needed()
                        await elem.click()
                        button_clicked = True
                        break
                except PlaywrightTimeout:
                    continue
                except Exception:
                    continue
            if not button_clicked:
                try:
                    await page.wait_for_selector('xpath=//a[contains(text(), "제안공고목록")]', timeout=2000)
                    await page.click('xpath=//a[contains(text(), "제안공고목록")]')
                    button_clicked = True
                except Exception:
                    pass
            if not button_clicked:
                await page.evaluate("""
                    (() => {
                        const links = document.querySelectorAll('a');
                        for (let link of links) {
                            if (link.innerText && link.innerText.includes('제안공고목록')) {
                                link.click(); return true;
                            }
                            if (link.title && link.title.includes('제안공고목록')) {
                                link.click(); return true;
                            }
                        }
                        return false;
                    })();
                """)

            # 팝업, 조건 등장 대기
            await asyncio.sleep(2)

            # 3개월 radio 선택 (wait_for_selector + JS)
            try:
                await page.click('input[title="3개월"]', timeout=3000)
            except Exception:
                await page.evaluate("""
                    document.querySelectorAll('input[type="radio"]').forEach(r => {
                        if (r.title && r.title.includes('3개월')) r.click();
                    });
                """)

            # 검색어 입력
            input_success = False
            try:
                input_elem = await page.query_selector('td[data-title="제안공고명"] input[type="text"]')
                if input_elem:
                    await input_elem.click()
                    await asyncio.sleep(0.2)
                    await input_elem.fill("")
                    await asyncio.sleep(0.1)
                    await input_elem.type(query, delay=80)
                    input_value = await input_elem.input_value()
                    if input_value == query:
                        input_success = True
                else:
                    input_elem = await page.query_selector('input[placeholder*="제안공고명"], input[title*="제안공고명"]')
                    if input_elem:
                        await input_elem.click()
                        await asyncio.sleep(0.2)
                        await input_elem.fill("")
                        await asyncio.sleep(0.1)
                        await input_elem.type(query, delay=80)
                        input_value = await input_elem.input_value()
                        if input_value == query:
                            input_success = True
            except Exception:
                pass
            if not input_success:
                js_result = await page.evaluate(f"""
                    (() => {{
                        const inputs = document.querySelectorAll('input[type="text"]');
                        for (let input of inputs) {{
                            const td = input.closest('td');
                            if (td) {{
                                const dataTitle = td.getAttribute('data-title');
                                if (dataTitle && dataTitle === '제안공고명') {{
                                    input.focus();
                                    input.value = '{query}';
                                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    input.dispatchEvent(new KeyboardEvent('keyup', {{ bubbles: true }}));
                                    return {{ success: true, value: input.value }};
                                }}
                            }}
                            if ((input.placeholder && input.placeholder.includes('제안공고')) ||
                                (input.title && input.title.includes('제안공고'))) {{
                                input.focus();
                                input.value = '{query}';
                                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                return {{ success: true, value: input.value }};
                            }}
                        }}
                        return {{ success: false, value: null }};
                    }})()
                """)
                if js_result and js_result.get('success'):
                    input_success = True

            # 표시수 100개 (wait_for_selector + JS)
            try:
                await page.wait_for_selector('select[id*="RecordCountPerPage"]', timeout=2000)
                await page.select_option('select[id*="RecordCountPerPage"]', "100")
            except Exception:
                await page.evaluate("""
                    document.querySelectorAll('select').forEach(s => {
                        if (s.id && s.id.includes('RecordCountPerPage')) {
                            s.value = '100';
                            s.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    });
                """)

            # 적용/검색 버튼
            try:
                await page.wait_for_selector('input[value="적용"], input[value="검색"]', timeout=2500)
                try:
                    await page.click('input[value="적용"]', timeout=1200)
                except Exception:
                    pass
                try:
                    await page.click('input[value="검색"]', timeout=2000)
                except Exception:
                    await page.evaluate("""
                        document.querySelectorAll('input[type="button"]').forEach(btn => {
                            if (btn.value === '검색') btn.click();
                        });
                    """)
            except Exception:
                pass

            # 검색결과 테이블 등장 대기(최대 7초)
            table_data = None
            try:
                await page.wait_for_selector('table[id*="grdPrps"], table[id*="Pbanc"]', timeout=7000)
                table_data = await page.evaluate("""
                    () => {
                        const tables = document.querySelectorAll('table');
                        for (let table of tables) {
                            if (table.id && (table.id.includes('grdPrps') || table.id.includes('Pbanc'))) {
                                const rows = [];
                                const trs = table.querySelectorAll('tr');
                                for (let tr of trs) {
                                    const row = [];
                                    const tds = tr.querySelectorAll('td');
                                    for (let td of tds) {
                                        let text = '';
                                        const nobr = td.querySelector('nobr');
                                        const link = td.querySelector('a');
                                        if (nobr) text = nobr.innerText;
                                        else if (link) text = link.innerText;
                                        else text = td.innerText;
                                        row.push(text.trim());
                                    }
                                    if (row.length > 0 && row.some(cell => cell !== '')) rows.push(row);
                                }
                                if (rows.length > 0) return rows;
                            }
                        }
                        return null;
                    }
                """)
            except PlaywrightTimeout:
                table_data = None

            if table_data:
                df = pd.DataFrame(table_data)
                headers = ["No", "제안공고번호", "수요기관", "제안공고명", "공고게시일자", "공고마감일시", "공고상태", "사유", "기타"]
                if len(df.columns) < len(headers):
                    headers = headers[:len(df.columns)]
                elif len(df.columns) > len(headers):
                    df = df.iloc[:, :len(headers)]
                df.columns = headers
                return headers, df.values.tolist()
            else:
                return None, None
    except Exception as e:
        print(f"[G2B Crawler Error] {str(e)}")
        return None, None
    finally:
        try:
            if page: await page.close()
            if context: await context.close()
            if browser: await browser.close()
        except:
            pass

def run_g2b_crawler(query="컴퓨터", browser_executable_path=None):
    """
    Streamlit Cloud 환경용 G2B 크롤러 실행 진입점
    :param query: 검색어
    :param browser_executable_path: 브라우저 경로 (자동감지)
    :return: (headers, table_data)
    """
    if not browser_executable_path:
        possible_paths = [
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/app/.apt/usr/bin/chromium",
            "/app/.apt/usr/bin/chromium-browser",
            "/home/appuser/.cache/ms-playwright/chromium-*/chrome-linux/chrome"
        ]
        for path in possible_paths:
            if os.path.exists(path):
                browser_executable_path = path
                break
    try:
        loop = asyncio.get_running_loop()
        import nest_asyncio
        nest_asyncio.apply()
        task = loop.create_task(run_crawler_async(query, browser_executable_path))
        return loop.run_until_complete(task)
    except RuntimeError:
        return asyncio.run(run_crawler_async(query, browser_executable_path))
    except Exception:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(run_crawler_async(query, browser_executable_path))
        finally:
            loop.close()
