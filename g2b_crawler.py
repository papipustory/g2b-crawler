# ======================== 동적 ID 팝업 처리 로직 설명 ==========================
# "제안공고목록" 클릭 시 매번 ID가 변하는 div 팝업이 DOM에 삽입됩니다.
# (예: id="mf_wfm_container_wq_uuid_427_popPrpbList" → _427 등 숫자 부분이 항상 다름)
# 기존에는 고정 ID나 전체 일치로 찾았으나, 동적 ID로 인해 실패하는 문제가 빈번했습니다.
# 이를 해결하기 위해, 부분 일치 CSS 선택자(div[id*="popPrpbList"])를 사용합니다.
# 이렇게 하면 어떤 동적 ID 상황에서도 팝업을 항상 안정적으로 찾을 수 있습니다.
# 이후 모든 팝업 내부 조작도 popup_locator를 통해 수행합니다.
# ============================================================================

import asyncio
from playwright.async_api import async_playwright, TimeoutError
import json

async def debug_page_state(page, step_name):
    """페이지 상태를 디버깅하는 헬퍼 함수"""
    print(f"\n=== DEBUG [{step_name}] ===")
    
    # 현재 URL
    print(f"현재 URL: {page.url}")
    
    # 제목
    title = await page.title()
    print(f"페이지 제목: {title}")
    
    # 모든 div[id*="pop"] 요소 찾기
    popup_divs = await page.query_selector_all('div[id*="pop"]')
    print(f"팝업 가능성 있는 div 개수: {len(popup_divs)}")
    
    for i, div in enumerate(popup_divs[:5]):  # 최대 5개만
        try:
            div_id = await div.get_attribute("id")
            div_class = await div.get_attribute("class")
            is_visible = await div.is_visible()
            print(f"  [{i}] id='{div_id}', class='{div_class}', visible={is_visible}")
        except:
            pass
    
    # w2popup_window 클래스를 가진 요소들
    w2popup_elements = await page.query_selector_all('.w2popup_window')
    print(f"w2popup_window 클래스 요소 개수: {len(w2popup_elements)}")
    
    for i, elem in enumerate(w2popup_elements[:3]):
        try:
            elem_id = await elem.get_attribute("id")
            is_visible = await elem.is_visible()
            print(f"  w2popup [{i}] id='{elem_id}', visible={is_visible}")
        except:
            pass
    
    # iframe 체크
    iframes = await page.query_selector_all('iframe')
    print(f"iframe 개수: {len(iframes)}")
    
    print("=== DEBUG END ===\n")

async def close_notice_popups(page):
    """초기 공지 팝업 닫기"""
    print("공지 팝업 닫기 시도...")
    closed_count = 0
    
    for _ in range(5):
        popup_divs = await page.query_selector_all("div[id^='mf_wfm_container_wq_uuid_'][class*='w2popup_window']")
        closed = False
        
        for popup in popup_divs:
            try:
                # 닫기 버튼 찾기
                for sel in ["button[class*='w2window_close']", "input[type='button'][value='닫기']"]:
                    btn = await popup.query_selector(sel)
                    if btn and await btn.is_visible():
                        await btn.click()
                        await asyncio.sleep(0.2)
                        closed = True
                        closed_count += 1
                        print(f"  - 팝업 {closed_count}개 닫음")
                        break
                
                # 오늘 하루 체크박스
                if not closed:
                    checkbox = await popup.query_selector("input[type='checkbox'][title*='오늘 하루']")
                    if checkbox:
                        await checkbox.check()
                        await asyncio.sleep(0.1)
                        btn = await popup.query_selector("input[type='button'][value='닫기']")
                        if btn:
                            await btn.click()
                            closed = True
                            closed_count += 1
                            print(f"  - 팝업 {closed_count}개 닫음 (오늘 하루 체크)")
                            break
            except Exception as e:
                print(f"  - 팝업 닫기 실패: {e}")
                continue
        
        if not closed:
            break
        await asyncio.sleep(0.5)
    
    print(f"총 {closed_count}개의 공지 팝업 닫음")

async def run_crawler_async(query, browser_executable_path):
    """동적 ID를 가진 팝업을 처리하는 최종 크롤러 - 디버그 버전"""
    browser = None
    print("--- 크롤러 시작 (DEBUG MODE) ---")
    
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
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()
            print("3. 새 페이지 생성 완료")

            # 콘솔 메시지 로깅
            page.on("console", lambda msg: print(f"[CONSOLE] {msg.type}: {msg.text}"))
            
            # 페이지 에러 로깅
            page.on("pageerror", lambda err: print(f"[PAGE ERROR] {err}"))

            await page.goto("https://shop.g2b.go.kr/", timeout=60000)
            print("4. 초기 페이지 접속 성공")
            
            # 디버그: 초기 페이지 상태
            await debug_page_state(page, "초기 페이지 로드 후")
            
            try:
                await page.wait_for_load_state('networkidle', timeout=15000)
                print("5. 페이지 네트워크 안정화 완료")
            except TimeoutError:
                print("5. 페이지 네트워크 안정화 시간 초과. 계속 진행합니다.")

            await asyncio.sleep(2)
            
            # 공지 팝업 닫기
            await close_notice_popups(page)

            print("\n6. '제안공고목록' 버튼 찾기 시작")
            
            # 다양한 선택자로 버튼 찾기
            button_selectors = [
                'a:has-text("제안공고목록")',
                'a[title*="제안공고목록"]',
                'div.w2textbox:has-text("제안공고목록")',
                '//a[contains(text(), "제안공고목록")]',
                'a[id*="btnPrpblist"]'
            ]
            
            button_found = False
            for selector in button_selectors:
                try:
                    if selector.startswith('//'):
                        elem = await page.query_selector(f'xpath={selector}')
                    else:
                        elem = await page.query_selector(selector)
                    
                    if elem and await elem.is_visible():
                        print(f"  - 버튼 발견! 선택자: {selector}")
                        
                        # 클릭 전 디버그
                        await debug_page_state(page, "버튼 클릭 전")
                        
                        await elem.scroll_into_view_if_needed()
                        await asyncio.sleep(0.5)
                        await elem.click()
                        button_found = True
                        print("  - 버튼 클릭 성공")
                        break
                except Exception as e:
                    print(f"  - 선택자 {selector} 실패: {e}")
                    continue
            
            if not button_found:
                print("  ! 표준 선택자로 버튼을 찾지 못함. 모든 링크 검사 중...")
                all_links = await page.query_selector_all("a")
                print(f"  - 전체 링크 개수: {len(all_links)}")
                
                for link in all_links:
                    try:
                        text = await link.inner_text()
                        title = await link.get_attribute("title")
                        
                        if "제안공고" in (text or "") or "제안공고" in (title or ""):
                            print(f"  - 제안공고 관련 링크 발견: text='{text}', title='{title}'")
                            await link.scroll_into_view_if_needed()
                            await asyncio.sleep(0.5)
                            await link.click()
                            button_found = True
                            print("  - 링크 클릭 성공")
                            break
                    except:
                        continue
            
            if not button_found:
                raise Exception("제안공고목록 버튼을 찾을 수 없습니다.")

            # 클릭 후 대기
            await asyncio.sleep(2)
            
            # 디버그: 클릭 후 페이지 상태
            await debug_page_state(page, "버튼 클릭 후")

            print("\n7. 제안공고목록 팝업 대기")
            
            # 다양한 팝업 선택자 시도
            popup_selectors = [
                'div[id*="popPrpbList"].w2popup_window',
                'div[id*="popPrpbList"]',
                'div.w2popup_window[id*="pop"]',
                'div.w2popup_window:visible',
                'div[id*="Prpb"][class*="popup"]'
            ]
            
            popup_found = False
            popup_locator = None
            
            for popup_sel in popup_selectors:
                try:
                    print(f"  - 팝업 선택자 시도: {popup_sel}")
                    
                    # 짧은 대기 시간으로 빠르게 체크
                    await page.wait_for_selector(popup_sel, state='visible', timeout=5000)
                    popup_locator = page.locator(popup_sel).first
                    
                    if await popup_locator.is_visible():
                        popup_found = True
                        print(f"  ✓ 팝업 발견! 선택자: {popup_sel}")
                        break
                except TimeoutError:
                    print(f"  - 타임아웃 (5초)")
                    continue
                except Exception as e:
                    print(f"  - 오류: {e}")
                    continue
            
            if not popup_found:
                print("\n  ! 표준 선택자로 팝업을 찾지 못함. 대체 방법 시도...")
                
                # iframe 내부 확인
                iframes = await page.query_selector_all('iframe')
                if iframes:
                    print(f"  - {len(iframes)}개의 iframe 발견. 첫 번째 iframe으로 전환...")
                    frame = await iframes[0].content_frame()
                    if frame:
                        page = frame
                        await debug_page_state(page, "iframe 전환 후")
                
                # 새 창/탭 확인
                if len(context.pages) > 1:
                    print(f"  - {len(context.pages)}개의 페이지 발견. 새 페이지로 전환...")
                    page = context.pages[-1]
                    await debug_page_state(page, "새 페이지 전환 후")
                    popup_locator = page
                    popup_found = True
            
            if not popup_found:
                raise Exception("팝업을 찾을 수 없습니다. DOM 구조가 변경되었을 수 있습니다.")

            print("\n8. 팝업 내부 작업 시작")
            
            # 3개월 라디오 버튼
            try:
                await popup_locator.locator('input[title="3개월"]').click(timeout=5000)
                print("  ✓ 3개월 선택 완료")
            except:
                # JavaScript로 강제 실행
                await page.evaluate("""
                    const radio = document.querySelector('input[title="3개월"]');
                    if (radio) {
                        radio.checked = true;
                        radio.click();
                    }
                """)
                print("  ✓ 3개월 선택 완료 (JS)")

            # 검색어 입력
            try:
                search_input = popup_locator.locator('td[data-title="제안공고명"] input[type="text"]')
                await search_input.fill(query)
                print(f"  ✓ 검색어 '{query}' 입력 완료")
            except:
                await page.evaluate(f"""
                    const input = document.querySelector('td[data-title="제안공고명"] input[type="text"]');
                    if (input) {{
                        input.value = '{query}';
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                """)
                print(f"  ✓ 검색어 '{query}' 입력 완료 (JS)")

            # 표시 수 100개
            try:
                await popup_locator.locator('select[id*="RecordCountPerPage"]').select_option("100")
                print("  ✓ 표시 수 100개 설정 완료")
            except:
                await page.evaluate("""
                    const selects = document.querySelectorAll('select[id*="RecordCountPerPage"]');
                    selects.forEach(select => {
                        select.value = "100";
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                    });
                """)
                print("  ✓ 표시 수 100개 설정 완료 (JS)")

            # 적용 버튼
            try:
                await popup_locator.locator('input[type="button"][value="적용"]').click()
                print("  ✓ 적용 버튼 클릭")
                await asyncio.sleep(1)
            except:
                print("  - 적용 버튼 클릭 실패 (계속 진행)")

            # 검색 버튼
            try:
                await popup_locator.locator('input[type="button"][value="검색"]').click()
                print("  ✓ 검색 버튼 클릭")
            except:
                await page.evaluate("""
                    const btn = document.querySelector('input[type="button"][value="검색"]');
                    if (btn) btn.click();
                """)
                print("  ✓ 검색 버튼 클릭 (JS)")

            await asyncio.sleep(3)

            print("\n9. 검색 결과 테이블 파싱")
            
            # 테이블 찾기
            table_selectors = [
                'table[id$="grdPrpsPbanc_body_table"]',
                'table[id*="grdPrps"]',
                'table.w2grid_body_table'
            ]
            
            table_elem = None
            for table_sel in table_selectors:
                try:
                    if popup_found and popup_locator:
                        table_elem = popup_locator.locator(table_sel)
                    else:
                        table_elem = page.locator(table_sel)
                    
                    if await table_elem.count() > 0:
                        print(f"  ✓ 테이블 발견: {table_sel}")
                        break
                except:
                    continue
            
            if not table_elem or await table_elem.count() == 0:
                print("  ! 테이블을 찾을 수 없습니다.")
                return None, None

            # 데이터 추출
            headers = ["No", "제안공고번호", "수요기관", "제안공고명", "공고게시일자", "공고마감일시", "공고상태", "사유", "기타"]
            data = []
            
            rows = await table_elem.locator('tr').all()
            print(f"  - {len(rows)}개의 행 발견")
            
            for i, row in enumerate(rows):
                tds = await row.locator('td').all()
                cols = []
                
                for td in tds:
                    text = await td.inner_text()
                    cols.append(text.strip())
                
                if cols and any(c.strip() for c in cols):
                    data.append(cols)
                    if i < 3:  # 처음 3개 행만 출력
                        print(f"  - 행 {i}: {cols[:4]}...")  # 처음 4개 컬럼만
            
            print(f"\n✓ 크롤링 성공: {len(data)}개의 데이터 수집")
            return headers, data

    except Exception as e:
        print(f"\n[CRITICAL ERROR] 크롤링 중 예외 발생:")
        print(f"  오류 타입: {type(e).__name__}")
        print(f"  오류 메시지: {str(e)}")
        
        # 스택 트레이스
        import traceback
        print("\n스택 트레이스:")
        traceback.print_exc()
        
        return None, None
        
    finally:
        if browser:
            await browser.close()
            print("\n--- 브라우저 종료, 크롤러 끝 ---")

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
