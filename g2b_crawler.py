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

async def run_crawler_async(query, browser_executable_path):
    """동적 ID를 가진 팝업을 처리하는 최종 크롤러"""
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
            await page.get_by_role("link", name="제안공고목록").click(no_wait_after=True)
            print("   - 성공")

            # --- 동적 팝업 처리 시작 (가장 중요한 부분) ---
            print("7. 제안공고목록 팝업(div) 대기")
            # [핵심] ID에 'popPrpbList'를 포함하는 div를 부분 일치 선택자로 찾아 동적 ID 이슈 해결
            popup_selector = 'div[id*="popPrpbList"].w2popup_window'
            await page.wait_for_selector(popup_selector, state='visible', timeout=30000)
            print("   - 팝업 발견! 이제부터 모든 작업은 이 팝업 내부에서 수행됩니다.")
            
            # 팝업 내부에서 작업을 수행하기 위해 로케이터를 정의합니다.
            popup_locator = page.locator(popup_selector)

            # --- 이제부터 모든 선택은 popup_locator를 통해 수행합니다. ---
            
            print("8. '3개월' 라디오 버튼 클릭")
            await popup_locator.locator('input[title="3개월"]').click()
            print("   - 성공")

            print(f"9. 검색어 '{query}' 입력")
            await popup_locator.locator('td[data-title="제안공고명"] input[type="text"]').fill(query)
            print("   - 성공")

            print("10. 표시 수 '100'개 선택")
            await popup_locator.locator('select[id*="RecordCountPerPage"]').select_option("100")
            print("   - 성공")

            print("11. '적용' 버튼 클릭")
            await popup_locator.locator('input[type="button"][value="적용"]').click(no_wait_after=True)
            print("   - 클릭 동작 수행 완료. 이제 결과 로딩을 기다립니다.")

            print("12. 검색 결과 테이블 대기 (최대 60초)")
            await popup_locator.locator('table[id$="grdPrpsPbanc_body_table"]').wait_for(timeout=60000)
            print("13. 검색 결과 로딩 완료. 테이블 파싱 시작.")
            table_elem = popup_locator.locator('table[id$="grdPrpsPbanc_body_table"]')
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
