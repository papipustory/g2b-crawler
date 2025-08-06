import os
import time
from playwright.sync_api import sync_playwright

def run_g2b_crawler(query: str = "컴퓨터"):
    """
    나라장터 제안공고 크롤러 - Streamlit Cloud 최적화 버전
    """
    
    # 브라우저 초기화
    with sync_playwright() as p:
        try:
            # Chromium 브라우저 실행 (Streamlit Cloud 환경)
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-blink-features=AutomationControlled',
                    '--single-process',  # 중요: Streamlit Cloud에서 필수
                    '--no-zygote',
                    '--no-first-run',
                    '--window-size=1280,720'
                ]
            )
            
            page = browser.new_page()
            
            # 1. 나라장터 메인 페이지 접속
            print(f"[INFO] 나라장터 접속 중...")
            url = "https://shop.g2b.go.kr/"
            page.goto(url, wait_until='domcontentloaded', timeout=30000)
            
            # 페이지 로드 대기
            page.wait_for_timeout(3000)
            
            # 2. 팝업 닫기 (여러 종류의 팝업 처리)
            print(f"[INFO] 팝업 확인 중...")
            popup_closed = False
            popup_selectors = [
                'button.close',
                '.popup_close', 
                '.layerPopup-close',
                'a.close',
                'img[alt*="닫기"]',
                'button[title*="닫기"]',
                '.btn_close'
            ]
            
            for selector in popup_selectors:
                try:
                    if page.locator(selector).count() > 0:
                        page.locator(selector).first.click(timeout=2000)
                        popup_closed = True
                        print(f"[INFO] 팝업 닫기 성공: {selector}")
                        break
                except:
                    continue
            
            if not popup_closed:
                print(f"[INFO] 닫을 팝업이 없거나 이미 닫혀있음")
            
            # 3. 제안공고목록 버튼 클릭
            print(f"[INFO] 제안공고목록 버튼 찾는 중...")
            
            # JavaScript로 직접 클릭 시도
            try:
                # onclick 속성으로 찾기
                page.evaluate("""
                    const links = document.querySelectorAll('a');
                    for (let link of links) {
                        if (link.onclick && link.onclick.toString().includes('popNoticeList')) {
                            link.click();
                            break;
                        }
                    }
                """)
                page.wait_for_timeout(2000)
            except:
                # 텍스트로 찾기
                try:
                    page.click('a:has-text("제안공고목록")', timeout=5000)
                except:
                    print(f"[ERROR] 제안공고목록 버튼을 찾을 수 없습니다")
                    browser.close()
                    return None
            
            print(f"[INFO] 제안공고목록 클릭 완료")
            
            # 4. 새 창 또는 iframe 대기
            page.wait_for_timeout(3000)
            
            # 팝업 창 확인
            all_pages = browser.contexts[0].pages
            if len(all_pages) > 1:
                # 새 창이 열린 경우
                popup_page = all_pages[-1]
                print(f"[INFO] 새 창에서 작업 진행")
                
                # 새 창 로드 대기
                popup_page.wait_for_load_state('domcontentloaded')
                
                # 5. 검색 수행
                try:
                    popup_page.fill('input[name="searchWrd"]', query, timeout=5000)
                    popup_page.click('button[onclick*="fn_search"]', timeout=5000)
                except:
                    # 대체 선택자 시도
                    popup_page.fill('#searchWrd', query, timeout=5000)
                    popup_page.click('#searchBtn', timeout=5000)
                
                page.wait_for_timeout(3000)
                
                # 6. 데이터 추출
                popup_page.wait_for_selector('table.tb_list', timeout=10000)
                
                # 헤더 추출
                header = []
                header_elements = popup_page.query_selector_all('table.tb_list thead th')
                for th in header_elements:
                    header.append(th.inner_text().strip())
                
                # 데이터 추출
                rows = popup_page.query_selector_all('table.tb_list tbody tr')
                table_data = []
                for row in rows:
                    cols = row.query_selector_all('td')
                    row_data = []
                    for col in cols:
                        row_data.append(col.inner_text().strip())
                    if row_data and any(row_data):  # 빈 행 제외
                        table_data.append(row_data)
                
            else:
                # iframe 처리
                print(f"[INFO] iframe 찾는 중...")
                frames = page.frames
                popup_frame = None
                
                for frame in frames:
                    frame_url = frame.url
                    if "pop" in frame_url.lower() or frame != page.main_frame:
                        popup_frame = frame
                        break
                
                if not popup_frame:
                    print(f"[ERROR] 팝업 프레임을 찾을 수 없습니다")
                    browser.close()
                    return None
                
                print(f"[INFO] iframe에서 작업 진행")
                
                # 5. 검색 수행
                try:
                    popup_frame.fill('input[name="searchWrd"]', query, timeout=5000)
                    popup_frame.click('button[onclick*="fn_search"]', timeout=5000)
                except:
                    # 대체 선택자 시도
                    popup_frame.fill('#searchWrd', query, timeout=5000)
                    popup_frame.click('#searchBtn', timeout=5000)
                
                page.wait_for_timeout(3000)
                
                # 6. 데이터 추출
                popup_frame.wait_for_selector('table.tb_list', timeout=10000)
                
                # 헤더 추출
                header = []
                header_elements = popup_frame.query_selector_all('table.tb_list thead th')
                for th in header_elements:
                    header.append(th.inner_text().strip())
                
                # 데이터 추출  
                rows = popup_frame.query_selector_all('table.tb_list tbody tr')
                table_data = []
                for row in rows:
                    cols = row.query_selector_all('td')
                    row_data = []
                    for col in cols:
                        row_data.append(col.inner_text().strip())
                    if row_data and any(row_data):  # 빈 행 제외
                        table_data.append(row_data)
            
            browser.close()
            
            if table_data:
                print(f"[INFO] 크롤링 성공: {len(table_data)}개 항목")
                return header, table_data
            else:
                print(f"[WARNING] 검색 결과가 없습니다")
                return None
                
        except Exception as e:
            print(f"[ERROR] 크롤링 실패: {str(e)}")
            if browser:
                browser.close()
            return None
