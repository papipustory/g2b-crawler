# 검색어 입력 - 더 정확한 선택자 사용
            try:
                print(f"   - 검색어 '{query}' 입력 시도...")
                
                # 방법 1: data-title 속성으로 찾기
                input_found = False
                input_elem = await page.query_selector('td[data-title="제안공고명"] input[type="text"]')
                
                if input_elem:
                    await input_elem.click()  # 먼저 클릭하여 포커스
                    await input_elem.fill("")  # 기존 내용 삭제
                    await input_elem.type(query, delay=100)  # 천천히 타이핑
                    input_found = True
                    print(f"   ✓ 검색어 '{query}' 입력 (data-title)")
                
                # 방법 2: placeholder나 title로 찾기
                if not input_found:
                    input_elem = await page.query_selector('input[placeholder*="제안공고명"], input[title*="제안공고명"]')
                    if input_elem:
                        await input_elem.click()
                        await input_elem.fill("")
                        await input_elem.type(query, delay=100)
                        input_found = True
                        print(f"   ✓ 검색어 '{query}' 입력 (placeholder/title)")
                
                # 방법 3: JavaScript로 강제 입력
                if not input_found:
                    js_result = await page.evaluate(f"""
                        () => {{
                            // 모든 input 요소를 순회
                            const inputs = document.querySelectorAll('input[type="text"]');
                            for (let input of inputs) {{
                                // TD 부모 요소 확인
                                const td = input.closest('td');
                                if (td) {{
                                    const dataTitle = td.getAttribute('data-title');
                                    const title = td.getAttribute('title');
                                    
                                    // 제안공고명 필드 찾기
                                    if ((dataTitle && dataTitle.includes('제안공고명')) ||
                                        (title && title.includes('제안공고명'))) {{
                                        input.value = '{query}';
                                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                        return true;
                                    }}
                                }}
                                
                                // placeholder나 title 확인
                                if ((input.placeholder && input.placeholder.includes('제안공고')) ||
                                    (input.title && input.title.includes('제안공고'))) {{
                                    input.value = '{query}';
                                    input# g2b_crawler.py - Streamlit Cloud 최적화 버전
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import pandas as pd
import os
import platform

async def run_crawler_async(query="컴퓨터", browser_executable_path=None):
    """Streamlit Cloud 환경에 최적화된 G2B 크롤러"""
    browser = None
    context = None
    page = None
    
    print("--- G2B 크롤러 시작 (Streamlit Cloud) ---")
    print(f"Python 버전: {platform.python_version()}")
    print(f"운영체제: {platform.system()}")
    
    try:
        async with async_playwright() as p:
            print("1. Playwright 초기화")
            
            # Streamlit Cloud용 브라우저 옵션
            browser_args = [
                '--no-sandbox',  # 필수
                '--disable-setuid-sandbox',  # 필수  
                '--disable-dev-shm-usage',  # 메모리 최적화
                '--disable-gpu',  # GPU 비활성화
                '--single-process',  # 단일 프로세스
                '--no-zygote',  # Zygote 프로세스 비활성화
                '--disable-blink-features=AutomationControlled',
                '--window-size=1920,1080',
                '--start-maximized',
                '--disable-extensions',
                '--disable-images',  # 이미지 로딩 비활성화 (속도 향상)
                '--disable-javascript-harmony-shipping',
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection'
            ]
            
            # 브라우저 실행
            if browser_executable_path:
                print(f"2. Chromium 실행 (경로: {browser_executable_path})")
                browser = await p.chromium.launch(
                    headless=True,  # Streamlit Cloud는 headless 필수
                    executable_path=browser_executable_path,
                    args=browser_args,
                    timeout=30000  # 시작 타임아웃 30초
                )
            else:
                print("2. Chromium 실행 (기본 경로)")
                browser = await p.chromium.launch(
                    headless=True,
                    args=browser_args,
                    timeout=30000
                )
            
            print("3. 브라우저 컨텍스트 생성")
            
            # User-Agent 및 컨텍스트 설정
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='ko-KR',
                timezone_id='Asia/Seoul',
                ignore_https_errors=True,  # HTTPS 에러 무시
                extra_http_headers={
                    'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache'
                }
            )
            
            # 자동화 감지 우회 스크립트
            await context.add_init_script("""
                // Webdriver 속성 숨기기
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Chrome 속성 추가
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };
                
                // Plugins 추가
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                        { name: 'Native Client', filename: 'internal-nacl-plugin' }
                    ],
                });
                
                // Languages 설정
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ko-KR', 'ko', 'en-US', 'en'],
                });
                
                // Platform 설정
                Object.defineProperty(navigator, 'platform', {
                    get: () => 'Linux x86_64'
                });
                
                // Hardware Concurrency
                Object.defineProperty(navigator, 'hardwareConcurrency', {
                    get: () => 4
                });
                
                // Device Memory
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => 8
                });
            """)
            
            page = await context.new_page()
            print("4. 새 페이지 생성 완료")
            
            # 타임아웃 설정
            page.set_default_timeout(30000)  # 기본 타임아웃 30초
            page.set_default_navigation_timeout(60000)  # 네비게이션 타임아웃 60초

            print("5. G2B 사이트 접속 시도")
            
            # 여러 URL 시도
            urls_to_try = [
                "https://shop.g2b.go.kr/index.do",
                "https://shop.g2b.go.kr/",
                "https://www.g2b.go.kr/"
            ]
            
            page_loaded = False
            for url in urls_to_try:
                try:
                    print(f"   - URL 시도: {url}")
                    response = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    
                    if response and response.status == 200:
                        await asyncio.sleep(3)
                        title = await page.title()
                        print(f"   - 페이지 제목: {title}")
                        
                        # 정상 페이지인지 확인
                        if "나라장터" in title or "조달청" in title or "G2B" in title.upper():
                            page_loaded = True
                            print("   ✓ 정상 페이지 로드 확인")
                            break
                        elif "접근" in title or "브라우저" in title:
                            print("   ⚠️ 브라우저 차단 페이지 감지")
                            continue
                except Exception as e:
                    print(f"   - 실패: {str(e)[:50]}")
                    continue
            
            if not page_loaded:
                print("\n⚠️ 모든 URL 접속 실패. 우회 방법 시도...")
                
                # 쿠키 추가 후 재시도
                await context.add_cookies([
                    {"name": "WMONID", "value": "streamlit_session", "domain": ".g2b.go.kr", "path": "/"},
                    {"name": "JSESSIONID", "value": "abcdef123456", "domain": ".g2b.go.kr", "path": "/"}
                ])
                
                await page.goto("https://shop.g2b.go.kr/index.do", wait_until='domcontentloaded')
                await asyncio.sleep(3)

            print("6. 페이지 안정화 대기")
            try:
                await page.wait_for_load_state('networkidle', timeout=10000)
            except PlaywrightTimeout:
                print("   - 네트워크 안정화 타임아웃 (정상)")

            # 공지 팝업 닫기 - 실제 HTML 구조에 맞춤
            print("7. 공지 팝업 닫기 시작")
            closed_count = 0
            
            for attempt in range(5):  # 최대 5번 시도
                # 실제 G2B 팝업 구조: w2window_header를 가진 div의 부모 요소
                popup_headers = await page.query_selector_all("div[id^='mf_wfm_container_wq_uuid_'][class='w2window_header']")
                
                print(f"   - 시도 {attempt + 1}: {len(popup_headers)}개의 팝업 헤더 발견")
                
                if len(popup_headers) == 0:
                    if attempt == 0:
                        print("   - 팝업이 없거나 로딩 중... 잠시 대기")
                        await asyncio.sleep(1)
                        continue
                    else:
                        print("   - 더 이상 팝업이 없음")
                        break
                
                closed_this_round = False
                
                for i, header in enumerate(popup_headers):
                    try:
                        # 헤더가 속한 팝업 컨테이너 찾기
                        popup_container = await header.evaluate_handle("""
                            (element) => {
                                // 부모 요소 중 w2popup_window 클래스를 가진 것 찾기
                                let parent = element.parentElement;
                                while (parent) {
                                    if (parent.classList && parent.classList.contains('w2popup_window')) {
                                        return parent;
                                    }
                                    parent = parent.parentElement;
                                }
                                return element.parentElement;  // 못 찾으면 직접 부모
                            }
                        """)
                        
                        # 팝업이 보이는지 확인
                        is_visible = await popup_container.is_visible()
                        if not is_visible:
                            print(f"     - 팝업 {i+1}은 이미 숨겨짐")
                            continue
                        
                        print(f"     - 팝업 {i+1} 처리 중...")
                        
                        # 닫기 버튼 찾기 - 실제 구조에 맞춤
                        close_button = await header.query_selector('button[type="button"][class="w2window_close"]')
                        
                        if not close_button:
                            # 대체 선택자들
                            close_button = await header.query_selector('button.w2window_close')
                        
                        if not close_button:
                            # 팝업 전체에서 닫기 버튼 찾기
                            close_button = await popup_container.query_selector('button[id$="_close"]')
                        
                        if not close_button:
                            # input 타입 닫기 버튼
                            close_button = await popup_container.query_selector('input[type="button"][value="닫기"]')
                        
                        if close_button and await close_button.is_visible():
                            await close_button.click()
                            await asyncio.sleep(0.5)  # 팝업이 닫힐 시간
                            closed_count += 1
                            closed_this_round = True
                            print(f"     ✓ 팝업 {i+1} 닫기 성공 (총 {closed_count}개)")
                        else:
                            print(f"     - 팝업 {i+1}의 닫기 버튼을 찾을 수 없음")
                            
                    except Exception as e:
                        print(f"     - 팝업 {i+1} 처리 실패: {str(e)[:50]}")
                        continue
                
                if not closed_this_round:
                    print(f"   - 이번 시도에서 닫은 팝업 없음")
                    break
                    
                await asyncio.sleep(0.5)  # 다음 팝업이 나타날 시간 대기
            
            # 대체 방법: JavaScript로 모든 팝업 강제 닫기
            if closed_count == 0:
                print("   - JavaScript로 팝업 닫기 시도...")
                js_closed = await page.evaluate("""
                    () => {
                        let closed = 0;
                        // w2window_close 클래스를 가진 모든 버튼 클릭
                        const closeButtons = document.querySelectorAll('button.w2window_close');
                        closeButtons.forEach(btn => {
                            if (btn && btn.offsetParent !== null) {  // visible check
                                btn.click();
                                closed++;
                            }
                        });
                        
                        // value가 "닫기"인 input 버튼들도 클릭
                        const inputButtons = document.querySelectorAll('input[type="button"][value="닫기"]');
                        inputButtons.forEach(btn => {
                            if (btn && btn.offsetParent !== null) {
                                btn.click();
                                closed++;
                            }
                        });
                        
                        return closed;
                    }
                """)
                
                if js_closed > 0:
                    closed_count = js_closed
                    print(f"   ✓ JavaScript로 {js_closed}개 팝업 닫기 성공")
            
            print(f"   ✓ 총 {closed_count}개의 팝업을 닫았습니다.")
            
            # 팝업을 닫은 후 페이지 스크롤
            print("   - 페이지 하단으로 스크롤")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)

            print("\n8. '제안공고목록' 버튼 찾기")
            
            # 버튼이 보이는지 확인하기 위해 스크롤 위치 조정
            await page.evaluate("window.scrollTo(0, 0)")  # 상단으로
            await asyncio.sleep(0.5)
            
            # 현재 페이지의 모든 링크 확인 (디버깅용)
            all_links = await page.query_selector_all("a")
            print(f"   - 페이지의 전체 링크 수: {len(all_links)}")
            
            # 제안공고 관련 링크 찾기
            proposal_links = []
            for link in all_links[:50]:  # 처음 50개만 확인
                try:
                    text = await link.inner_text()
                    title = await link.get_attribute("title")
                    if text and "제안" in text:
                        proposal_links.append(f"text: {text[:30]}")
                    elif title and "제안" in title:
                        proposal_links.append(f"title: {title[:30]}")
                except:
                    continue
            
            if proposal_links:
                print(f"   - 제안 관련 링크 발견: {proposal_links[:3]}")
            
            button_clicked = False
            
            # 방법 1: PC 버전과 동일한 선택자들
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
                        # 요소가 뷰포트에 있는지 확인
                        await elem.scroll_into_view_if_needed()
                        await asyncio.sleep(0.5)
                        await elem.click()
                        button_clicked = True
                        print(f"   ✓ 버튼 클릭 성공: {sel}")
                        break
                except Exception as e:
                    print(f"   - 선택자 {sel} 실패: {str(e)[:30]}")
                    continue
            
            # 방법 2: XPath로 시도
            if not button_clicked:
                try:
                    await page.click('xpath=//a[contains(text(), "제안공고목록")]', timeout=3000)
                    button_clicked = True
                    print("   ✓ 버튼 클릭 성공 (XPath)")
                except:
                    pass
            
            # 방법 3: 모든 링크를 순회하며 찾기 (PC 버전과 동일)
            if not button_clicked:
                print("   - 모든 링크를 순회하며 찾기...")
                all_a = await page.query_selector_all("a")
                
                for a in all_a:
                    try:
                        title = await a.get_attribute("title")
                        href = await a.get_attribute("href")
                        inner = await a.inner_text()
                        
                        if (title and "제안공고" in title) or (inner and "제안공고" in inner):
                            print(f"     - 발견: text='{inner[:20]}', title='{title}'")
                            
                            # javascript:void(null) 같은 무효 링크 제외
                            if href and href.strip() != "javascript:void(null)":
                                await a.scroll_into_view_if_needed()
                                await asyncio.sleep(0.2)
                                await a.click()
                                button_clicked = True
                                print("   ✓ 버튼 클릭 성공 (링크 순회)")
                                break
                    except:
                        continue
            
            # 방법 4: JavaScript로 강제 클릭
            if not button_clicked:
                print("   - JavaScript로 강제 클릭 시도...")
                clicked = await page.evaluate("""
                    () => {
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
                    }
                """)
                
                if clicked:
                    button_clicked = True
                    print("   ✓ 버튼 클릭 성공 (JavaScript)")
            
            if not button_clicked:
                # 페이지 내용 확인
                content = await page.content()
                if len(content) < 5000:
                    raise Exception(f"페이지가 제대로 로드되지 않음 (크기: {len(content)} bytes)")
                else:
                    # 스크린샷 저장 (디버깅용)
                    try:
                        await page.screenshot(path="debug_screenshot.png")
                        print("   - 디버그 스크린샷 저장: debug_screenshot.png")
                    except:
                        pass
                    raise Exception("제안공고목록 버튼을 찾을 수 없음")

            await asyncio.sleep(3)
            
            print("\n9. 검색 조건 설정")
            
            # 팝업이 새 페이지로 열렸는지 확인
            if len(context.pages) > 1:
                print("   - 새 탭/창 감지, 전환")
                page = context.pages[-1]
                await page.bring_to_front()

            # 3개월 선택
            try:
                await page.click('input[title="3개월"]', timeout=3000)
                print("   ✓ 3개월 선택")
            except:
                await page.evaluate("""
                    document.querySelectorAll('input[type="radio"]').forEach(r => {
                        if (r.title && r.title.includes('3개월')) r.click();
                    });
                """)
                print("   ✓ 3개월 선택 (JS)")

            # 검색어 입력 - 확실하게 입력되도록 개선
            print(f"   - 검색어 '{query}' 입력 중...")
            input_success = False
            
            # 방법 1: data-title로 찾기
            try:
                input_elem = await page.query_selector('td[data-title="제안공고명"] input[type="text"]')
                if input_elem:
                    await input_elem.click()  # 포커스
                    await asyncio.sleep(0.2)
                    await input_elem.fill("")  # 기존 값 삭제
                    await asyncio.sleep(0.2)
                    await input_elem.type(query, delay=50)  # 천천히 타이핑
                    await asyncio.sleep(0.3)
                    
                    # 입력 확인
                    input_value = await input_elem.input_value()
                    if input_value == query:
                        input_success = True
                        print(f"   ✓ 검색어 '{query}' 입력 완료")
                    else:
                        print(f"   ⚠️ 입력 값 불일치: '{input_value}' != '{query}'")
            except Exception as e:
                print(f"   - 방법 1 실패: {str(e)[:50]}")
            
            # 방법 2: JavaScript로 강제 입력
            if not input_success:
                try:
                    js_result = await page.evaluate(f"""
                        () => {{
                            let found = false;
                            // 모든 input 찾기
                            const inputs = document.querySelectorAll('input[type="text"]');
                            
                            for (let input of inputs) {{
                                const td = input.closest('td');
                                if (td && td.getAttribute('data-title') === '제안공고명') {{
                                    input.focus();
                                    input.value = '';
                                    input.value = '{query}';
                                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    input.dispatchEvent(new KeyboardEvent('keyup', {{ bubbles: true }}));
                                    found = true;
                                    return {{ success: true, value: input.value }};
                                }}
                            }}
                            
                            // 못 찾은 경우 placeholder로 시도
                            if (!found) {{
                                for (let input of inputs) {{
                                    if (input.placeholder && input.placeholder.includes('제안공고')) {{
                                        input.focus();
                                        input.value = '{query}';
                                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                        return {{ success: true, value: input.value }};
                                    }}
                                }}
                            }}
                            
                            return {{ success: false, value: null }};
                        }}
                    """)
                    
                    if js_result and js_result.get('success'):
                        input_success = True
                        print(f"   ✓ 검색어 '{query}' 입력 완료 (JS)")
                        print(f"     입력된 값: {js_result.get('value')}")
                except Exception as e:
                    print(f"   - 방법 2 실패: {str(e)[:50]}")
            
            # 입력 확인 대기
            if input_success:
                await asyncio.sleep(0.5)  # 입력이 반영될 시간
            else:
                print(f"   ⚠️ 검색어 입력 실패! 전체 검색이 될 수 있습니다.")

            # 표시 수 100개
            try:
                await page.select_option('select[id*="RecordCountPerPage"]', "100")
                print("   ✓ 표시 수 100개 설정")
            except:
                await page.evaluate("""
                    document.querySelectorAll('select').forEach(s => {
                        if (s.id && s.id.includes('RecordCountPerPage')) {
                            s.value = '100';
                            s.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    });
                """)
                print("   ✓ 표시 수 100개 설정 (JS)")

            # 적용 버튼
            try:
                await page.click('input[value="적용"]', timeout=2000)
                await asyncio.sleep(1)
            except:
                pass

            # 검색 버튼 클릭 전 입력 값 최종 확인
            print("   - 검색 버튼 클릭 전 입력 값 확인...")
            final_check = await page.evaluate("""
                () => {
                    const inputs = document.querySelectorAll('input[type="text"]');
                    for (let input of inputs) {
                        const td = input.closest('td');
                        if (td && td.getAttribute('data-title') === '제안공고명') {
                            return input.value;
                        }
                    }
                    return null;
                }
            """)
            
            if final_check:
                print(f"     현재 입력된 검색어: '{final_check}'")
            else:
                print("     ⚠️ 검색어 필드를 찾을 수 없음")
            
            # 검색 버튼
            try:
                await page.click('input[value="검색"]', timeout=3000)
                print("   ✓ 검색 실행")
            except:
                await page.evaluate("""
                    document.querySelectorAll('input[type="button"]').forEach(btn => {
                        if (btn.value === '검색') btn.click();
                    });
                """)
                print("   ✓ 검색 실행 (JS)")

            await asyncio.sleep(5)  # 결과 로딩 대기

            print("\n10. 검색 결과 수집")
            
            # 테이블 찾기
            table_found = False
            data = []
            
            # JavaScript로 테이블 데이터 추출
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
                }
            """)
            
            if table_data:
                data = table_data
                table_found = True
                print(f"   ✓ {len(data)}개 데이터 수집 완료")
            else:
                print("   ⚠️ 테이블 데이터를 찾을 수 없음")
                
            if table_found and data:
                # DataFrame 생성
                df = pd.DataFrame(data)
                headers = ["No", "제안공고번호", "수요기관", "제안공고명", "공고게시일자", "공고마감일시", "공고상태", "사유", "기타"]
                
                # 헤더 조정
                if len(df.columns) < len(headers):
                    headers = headers[:len(df.columns)]
                elif len(df.columns) > len(headers):
                    df = df.iloc[:, :len(headers)]
                
                df.columns = headers
                
                print(f"   ✓ DataFrame 생성 완료")
                return headers, df.values.tolist()
            else:
                return None, None

    except Exception as e:
        print(f"\n[ERROR] 크롤링 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, None
        
    finally:
        # 리소스 정리
        try:
            if page:
                await page.close()
            if context:
                await context.close()
            if browser:
                await browser.close()
        except:
            pass
        print("\n--- 크롤러 종료 ---")

def run_g2b_crawler(query="컴퓨터", browser_executable_path=None):
    """Streamlit Cloud 환경용 G2B 크롤러 실행"""
    
    # Streamlit Cloud 환경 감지
    if not browser_executable_path:
        # Streamlit Cloud의 기본 Chromium 경로들
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
                print(f"Chromium 경로 자동 감지: {path}")
                break
    
    # 이벤트 루프 처리
    try:
        loop = asyncio.get_running_loop()
        
        # Streamlit Cloud에서는 nest_asyncio 필수
        import nest_asyncio
        nest_asyncio.apply()
        
        # 새 태스크로 실행
        task = loop.create_task(run_crawler_async(query, browser_executable_path))
        return loop.run_until_complete(task)
        
    except RuntimeError:
        # 이벤트 루프가 없는 경우
        return asyncio.run(run_crawler_async(query, browser_executable_path))
    except Exception as e:
        print(f"실행 오류: {e}")
        # 새 이벤트 루프 생성
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(run_crawler_async(query, browser_executable_path))
        finally:
            loop.close()
