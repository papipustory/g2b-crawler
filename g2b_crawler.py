import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import pandas as pd
import os
import platform

async def run_crawler_async(query="컴퓨터", browser_executable_path=None):
    """Streamlit Cloud 환경에 최적화된 G2B 크롤러 (속도 개선 버전)"""
    browser = None
    context = None
    page = None

    try:
        async with async_playwright() as p:
            # --- 브라우저 실행 옵션 (생략) ---
            browser_args = [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--single-process',
                '--no-zygote',
                '--disable-blink-features=AutomationControlled',
                '--window-size=1920,1080',
                '--start-maximized',
                '--disable-extensions',
                '--disable-images',
                '--disable-javascript-harmony-shipping',
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection'
            ]

            # --- 브라우저 실행 ---
            if browser_executable_path:
                browser = await p.chromium.launch(
                    headless=True,
                    executable_path=browser_executable_path,
                    args=browser_args,
                    timeout=8000
                )
            else:
                browser = await p.chromium.launch(
                    headless=True,
                    args=browser_args,
                    timeout=10000
                )

            # --- 컨텍스트 생성 ---
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='ko-KR',
                timezone_id='Asia/Seoul',
                ignore_https_errors=True,
                extra_http_headers={
                    'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
            )
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = {runtime: {}, loadTimes: function() {}, csi: function() {}, app: {}};
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                        { name: 'Native Client', filename: 'internal-nacl-plugin' }
                    ],
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ko-KR', 'ko', 'en-US', 'en'],
                });
                Object.defineProperty(navigator, 'platform', {get: () => 'Linux x86_64'});
                Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 4});
                Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
            """)

            page = await context.new_page()

            # --- 사이트 접속 (속도 개선) ---
            urls_to_try = [
                "https://shop.g2b.go.kr/index.do",
                "https://shop.g2b.go.kr/",
                "https://www.g2b.go.kr/"
            ]
            page_loaded = False
            for url in urls_to_try:
                try:
                    response = await page.goto(url, wait_until='domcontentloaded', timeout=5000)
                    if response and response.status == 200:
                        await asyncio.sleep(0.7)
                        title = await page.title()
                        if "나라장터" in title or "조달청" in title or "G2B" in title.upper():
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
                await asyncio.sleep(0.7)

            try:
                await page.wait_for_load_state('domcontentloaded', timeout=5000)
            except PlaywrightTimeout:
                pass

            # --- 공지 팝업 닫기 (최대 2회 반복, sleep↓) ---
            for attempt in range(2):
                popup_headers = await page.query_selector_all("div[id^='mf_wfm_container_wq_uuid_'][class='w2window_header']")
                if len(popup_headers) == 0:
                    await asyncio.sleep(0.2)
                    continue

                for header in popup_headers:
                    try:
                        popup_container = await header.evaluate_handle("""
                            (element) => {
                                let parent = element.parentElement;
                                while (parent) {
                                    if (parent.classList && parent.classList.contains('w2popup_window')) {
                                        return parent;
                                    }
                                    parent = parent.parentElement;
                                }
                                return element.parentElement;
                            }
                        """)
                        is_visible = await popup_container.is_visible()
                        if not is_visible:
                            continue
                        close_button = await header.query_selector('button[type="button"][class="w2window_close"]')
                        if not close_button:
                            close_button = await header.query_selector('button.w2window_close')
                        if not close_button:
                            close_button = await popup_container.query_selector('button[id$="_close"]')
                        if not close_button:
                            close_button = await popup_container.query_selector('input[type="button"][value="닫기"]')
                        if close_button and await close_button.is_visible():
                            await close_button.click()
                            await asyncio.sleep(0.18)
                    except Exception:
                        continue
                await asyncio.sleep(0.18)

            # 팝업 JS 강제 닫기(빠르게)
            await page.evaluate("""
                (() => {
                    document.querySelectorAll('button.w2window_close').forEach(btn => {
                        if (btn && btn.offsetParent !== null) btn.click();
                    });
                    document.querySelectorAll('input[type="button"][value="닫기"]').forEach(btn => {
                        if (btn && btn.offsetParent !== null) btn.click();
                    });
                })();
            """)

            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(0.22)
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(0.12)

            # --- '제안공고목록' 버튼 찾기 ---
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
                    elem = await page.query_selector(sel)
                    if elem and await elem.is_visible():
                        await elem.scroll_into_view_if_needed()
                        await asyncio.sleep(0.1)
                        await elem.click()
                        button_clicked = True
                        break
                except Exception:
                    continue
            if not button_clicked:
                try:
                    await page.click('xpath=//a[contains(text(), "제안공고목록")]', timeout=1500)
                    button_clicked = True
                except Exception:
                    pass
            if not button_clicked:
                all_a = await page.query_selector_all("a")
                for a in all_a:
                    try:
                        title = await a.get_attribute("title")
                        href = await a.get_attribute("href")
                        inner = await a.inner_text()
                        if (title and "제안공고" in title) or (inner and "제안공고" in inner):
                            if href and href.strip() != "javascript:void(null)":
                                await a.scroll_into_view_if_needed()
                                await asyncio.sleep(0.12)
                                await a.click()
                                button_clicked = True
                                break
                    except Exception:
                        continue
            if not button_clicked:
                clicked = await page.evaluate("""
                    (() => {
                        const links = document.querySelectorAll('a');
                        for (let link of links) {
                            if (link.innerText && link.innerText.includes('제안공고목록')) {
                                link.click();
                                return true;
                            }
                            if (link.title && link.title.includes('제안공고목록')) {
                                link.click();
                                return true;
                            }
                        }
                        return false;
                    })();
                """)
                if clicked:
                    button_clicked = True
            if not button_clicked:
                content = await page.content()
                if len(content) < 5000:
                    raise Exception(f"페이지가 제대로 로드되지 않음 (크기: {len(content)} bytes)")
                else:
                    try:
                        await page.screenshot(path="debug_screenshot.png")
                    except Exception:
                        pass
                    raise Exception("제안공고목록 버튼을 찾을 수 없음")

            await asyncio.sleep(0.7)

            # --- 검색 조건 설정 ---
            if len(context.pages) > 1:
                page = context.pages[-1]
                await page.bring_to_front()

            # 3개월 선택
            try:
                await page.click('input[title="3개월"]', timeout=1000)
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
                    await asyncio.sleep(0.07)
                    await input_elem.clear()
                    await asyncio.sleep(0.07)
                    await input_elem.type(query, delay=60)
                    await asyncio.sleep(0.08)
                    input_value = await input_elem.input_value()
                    if input_value == query:
                        input_success = True
            except Exception:
                pass
            if not input_success:
                try:
                    input_elem = await page.query_selector('input[placeholder*="제안공고명"], input[title*="제안공고명"]')
                    if input_elem:
                        await input_elem.click()
                        await asyncio.sleep(0.07)
                        await input_elem.clear()
                        await asyncio.sleep(0.07)
                        await input_elem.type(query, delay=60)
                        await asyncio.sleep(0.08)
                        input_value = await input_elem.input_value()
                        if input_value == query:
                            input_success = True
                except Exception:
                    pass
            if not input_success:
                try:
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
                except Exception:
                    pass
            if input_success:
                await asyncio.sleep(0.15)

            # 표시 수 100개
            try:
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

            try:
                await page.click('input[value="적용"]', timeout=1000)
                await asyncio.sleep(0.18)
            except Exception:
                pass

            try:
                await page.click('input[value="검색"]', timeout=1100)
            except Exception:
                await page.evaluate("""
                    document.querySelectorAll('input[type="button"]').forEach(btn => {
                        if (btn.value === '검색') btn.click();
                    });
                """)

            await asyncio.sleep(0.85)  # 결과 로딩 대기 (속도 개선)

            # --- 결과 테이블 수집 ---
            table_found = False
            data = []
            table_data = await page.evaluate("""
                (() => {
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
                                    if (nobr) {
                                        text = nobr.innerText;
                                    } else if (link) {
                                        text = link.innerText;
                                    } else {
                                        text = td.innerText;
                                    }
                                    row.push(text.trim());
                                }
                                if (row.length > 0 && row.some(cell => cell !== '')) {
                                    rows.push(row);
                                }
                            }
                            if (rows.length > 0) {
                                return rows;
                            }
                        }
                    }
                    return null;
                })()
            """)
            if table_data:
                data = table_data
                table_found = True

            if table_found and data:
                df = pd.DataFrame(data)
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
        import traceback
        traceback.print_exc()
        return None, None

    finally:
        try:
            if page:
                await page.close()
            if context:
                await context.close()
            if browser:
                await browser.close()
        except Exception:
            pass

def run_g2b_crawler(query="컴퓨터", browser_executable_path=None):
    """Streamlit Cloud 환경용 G2B 크롤러 실행"""
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
    except Exception as e:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(run_crawler_async(query, browser_executable_path))
        finally:
            loop.close()
