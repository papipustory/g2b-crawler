from playwright.sync_api import sync_playwright
import time

def run_g2b_crawler(query="컴퓨터"):
    """나라장터 크롤러 - 동기 버전 (디버깅 포함)"""
    
    print(f"[START] 크롤링 시작: {query}")
    browser = None
    
    try:
        with sync_playwright() as p:
            print("[1] Playwright 시작")
            
            # 브라우저 실행
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--single-process'
                ]
            )
            print("[2] 브라우저 실행 완료")
            
            page = browser.new_page()
            print("[3] 새 페이지 생성")
            
            # 1. 사이트 접속
            print("[4] 나라장터 접속 시도...")
            page.goto("https://shop.g2b.go.kr/", timeout=30000)
            print("[5] 나라장터 접속 성공")
            
            # 페이지 로드 대기
            page.wait_for_load_state('domcontentloaded')
            time.sleep(3)
            print("[6] 페이지 로드 완료")
            
            # 2. 팝업 닫기 시도
            print("[7] 팝업 확인 중...")
            popup_closed = False
            popup_selectors = [
                'button.close',
                '.popup_close',
                '.layerPopup-close',
                'button[class*="w2window_close"]',
                'input[type="button"][value="닫기"]'
            ]
            
            for selector in popup_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        page.locator(selector).first.click()
                        popup_closed = True
                        print(f"[8] 팝업 닫기 성공: {selector}")
                        break
                except:
                    continue
            
            if not popup_closed:
                print("[8] 팝업 없음 또는 이미 닫혀있음")
            
            time.sleep(2)
            
            # 3. 제안공고목록 버튼 찾기
            print("[9] 제안공고목록 버튼 찾는 중...")
            
            # JavaScript로 직접 클릭 시도
            try:
                page.evaluate("""
                    const links = document.querySelectorAll('a');
                    for (let link of links) {
                        const text = link.innerText || link.textContent || '';
                        const title = link.getAttribute('title') || '';
                        const onclick = link.getAttribute('onclick') || '';
                        
                        if (text.includes('제안공고') || title.includes('제안공고') || onclick.includes('popNoticeList')) {
                            console.log('Found button:', text, title);
                            link.click();
                            return true;
                        }
                    }
                    return false;
                """)
                print("[10] 제안공고목록 버튼 클릭 성공")
            except Exception as e:
                print(f"[10] 제안공고목록 버튼 클릭 실패: {e}")
                browser.close()
                return None
            
            time.sleep(3)
            
            # 4. 새 창 또는 iframe 확인
            print("[11] 팝업 창/프레임 확인 중...")
            
            # 새 창 확인
            if len(browser.contexts[0].pages) > 1:
                popup_page = browser.contexts[0].pages[-1]
                print("[12] 새 창에서 작업")
                working_page = popup_page
            else:
                # iframe 확인
                frames = page.frames
                print(f"[12] 프레임 개수: {len(frames)}")
                
                if len(frames) > 1:
                    working_page = frames[-1]  # 마지막 프레임 사용
                    print("[12] iframe에서 작업")
                else:
                    working_page = page
                    print("[12] 메인 페이지에서 작업")
            
            # 5. 검색 수행
            print("[13] 검색 필드 찾는 중...")
            try:
                # 검색어 입력
                search_input = working_page.locator('input[name="searchWrd"]').or_(
                    working_page.locator('input[type="text"]').first
                )
                search_input.fill(query)
                print(f"[14] 검색어 '{query}' 입력 완료")
                
                # 검색 버튼 클릭
                search_button = working_page.locator('button[onclick*="fn_search"]').or_(
                    working_page.locator('button:has-text("검색")').or_(
                        working_page.locator('input[type="button"][value="검색"]')
                    )
                )
                search_button.click()
                print("[15] 검색 버튼 클릭")
                
            except Exception as e:
                print(f"[ERROR] 검색 실패: {e}")
                browser.close()
                return None
            
            time.sleep(3)
            
            # 6. 데이터 추출
            print("[16] 테이블 데이터 추출 중...")
            try:
                # 테이블 찾기
                table = working_page.locator('table.tb_list').or_(
                    working_page.locator('table').first
                )
                
                # 헤더 추출
                headers = []
                header_cells = working_page.locator('table thead th').all()
                if not header_cells:
                    header_cells = working_page.locator('table tr').first.locator('th').all()
                
                for th in header_cells:
                    headers.append(th.inner_text().strip())
                
                if not headers:
                    headers = ["No", "제안공고번호", "수요기관", "제안공고명", 
                              "공고게시일자", "공고마감일시", "공고상태"]
                
                print(f"[17] 헤더: {headers[:3]}...")  # 처음 3개만 출력
                
                # 데이터 추출
                rows = working_page.locator('table tbody tr').all()
                data = []
                
                for row in rows:
                    cols = []
                    cells = row.locator('td').all()
                    for cell in cells:
                        cols.append(cell.inner_text().strip())
                    if cols and any(cols):
                        data.append(cols)
                
                print(f"[18] 데이터 추출 완료: {len(data)}개 행")
                
                browser.close()
                
                if data:
                    return headers[:len(data[0])], data
                else:
                    print("[WARNING] 데이터가 없습니다")
                    return None
                    
            except Exception as e:
                print(f"[ERROR] 데이터 추출 실패: {e}")
                browser.close()
                return None
    
    except Exception as e:
        print(f"[FATAL ERROR] 크롤링 중 오류: {e}")
        if browser:
            browser.close()
        return None
