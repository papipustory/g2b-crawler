import os
import time
import asyncio
import nest_asyncio
from playwright.sync_api import sync_playwright

# 비동기 환경 설정 (Streamlit Cloud용)
nest_asyncio.apply()

def run_g2b_crawler(query: str = "컴퓨터"):
    """
    G2B 크롤러 실행 함수 (Streamlit Cloud 최적화)
    """
    try:
        # Streamlit Cloud 환경 변수 설정
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
        
        with sync_playwright() as p:
            # Chromium 브라우저 실행 (Streamlit Cloud 최적화)
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-web-security",
                    "--disable-software-rasterizer",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--disable-features=TranslateUI",
                    "--disable-ipc-flooding-protection",
                    "--single-process"
                ]
            )
            
            # 새 페이지 생성
            page = browser.new_page()
            
            # User Agent 설정 (차단 방지)
            page.set_extra_http_headers({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            # 타임아웃 설정
            page.set_default_timeout(30000)  # 30초
            
            print(f"검색어: {query}")
            
            # (1) 나라장터 제안공고 페이지 진입
            url = "https://shop.g2b.go.kr/"
            print(f"페이지 접속 중: {url}")
            page.goto(url, wait_until="networkidle")
            
            # 페이지 로드 대기
            time.sleep(3)
            
            # (2) 팝업 닫기 (존재할 때만)
            try:
                popup_selectors = [
                    'button.close',
                    '.popup_close', 
                    '.layerPopup-close',
                    '[onclick*="closeLayer"]',
                    '.btn_close'
                ]
                for selector in popup_selectors:
                    try:
                        if page.query_selector(selector):
                            page.click(selector)
                            print("팝업 닫기 성공")
                            time.sleep(1)
                            break
                    except:
                        continue
            except Exception as e:
                print(f"팝업 닫기 실패: {e}")
            
            # (3) '제안공고목록' 버튼 찾기 및 클릭
            try:
                # 여러 가능한 셀렉터 시도
                notice_selectors = [
                    'a[onclick*="popNoticeList"]',
                    'a[href*="popNoticeList"]',
                    'a:has-text("제안공고목록")',
                    'button:has-text("제안공고목록")'
                ]
                
                clicked = False
                for selector in notice_selectors:
                    try:
                        element = page.wait_for_selector(selector, timeout=5000)
                        if element:
                            page.click(selector)
                            print("제안공고목록 버튼 클릭 성공")
                            clicked = True
                            break
                    except:
                        continue
                
                if not clicked:
                    print("제안공고목록 버튼을 찾을 수 없습니다")
                    browser.close()
                    return None
                    
            except Exception as e:
                print(f"제안공고목록 버튼 클릭 실패: {e}")
                browser.close()
                return None
            
            # 팝업 로딩 대기
            time.sleep(5)
            
            # (4) 팝업 프레임 탐색
            frames = page.frames
            popup_frame = None
            
            print(f"총 프레임 수: {len(frames)}")
            for i, frame in enumerate(frames):
                print(f"프레임 {i}: {frame.url}")
                if "popNoticeList" in frame.url or "Notice" in frame.url:
                    popup_frame = frame
                    print(f"타겟 프레임 발견: {frame.url}")
                    break
            
            # 프레임을 찾지 못한 경우 새 창/탭 확인
            if not popup_frame:
                try:
                    # 새 페이지가 열렸는지 확인
                    all_pages = browser.contexts[0].pages
                    if len(all_pages) > 1:
                        popup_frame = all_pages[-1]  # 마지막에 열린 페이지
                        print("새 페이지에서 팝업 발견")
                    else:
                        print("팝업 프레임을 찾을 수 없습니다")
                        browser.close()
                        return None
                except Exception as e:
                    print(f"새 페이지 확인 실패: {e}")
                    browser.close()
                    return None
            
            # (5) 검색창에 입력 및 검색 실행
            try:
                # 검색창 찾기
                search_selectors = [
                    'input[name="searchWrd"]',
                    'input[id*="search"]',
                    'input[placeholder*="검색"]',
                    'input[type="text"]'
                ]
                
                search_input = None
                for selector in search_selectors:
                    try:
                        search_input = popup_frame.wait_for_selector(selector, timeout=5000)
                        if search_input:
                            break
                    except:
                        continue
                
                if not search_input:
                    print("검색창을 찾을 수 없습니다")
                    browser.close()
                    return None
                
                # 검색어 입력
                popup_frame.fill(search_selectors[0], query)
                print(f"검색어 입력 완료: {query}")
                
                # 검색 버튼 클릭
                search_btn_selectors = [
                    'button[onclick*="fn_search"]',
                    'button[onclick*="search"]',
                    'input[type="submit"]',
                    'button:has-text("검색")'
                ]
                
                for selector in search_btn_selectors:
                    try:
                        popup_frame.click(selector)
                        print("검색 버튼 클릭 성공")
                        break
                    except:
                        continue
                
                # 검색 결과 로딩 대기
                time.sleep(5)
                
            except Exception as e:
                print(f"검색 실행 실패: {e}")
                browser.close()
                return None
            
            # (6) 테이블 데이터 추출
            try:
                # 테이블 대기
                table_selectors = [
                    'table.tb_list',
                    'table[class*="list"]',
                    'table tbody tr',
                    '.list-table'
                ]
                
                table_found = False
                for selector in table_selectors:
                    try:
                        popup_frame.wait_for_selector(selector, timeout=10000)
                        table_found = True
                        break
                    except:
                        continue
                
                if not table_found:
                    print("테이블을 찾을 수 없습니다")
                    browser.close()
                    return None
                
                # 헤더 추출
                header_selectors = [
                    'table.tb_list thead th',
                    'table thead th',
                    'table th'
                ]
                
                header = []
                for selector in header_selectors:
                    try:
                        header_elements = popup_frame.query_selector_all(selector)
                        if header_elements:
                            header = [th.inner_text().strip() for th in header_elements]
                            break
                    except:
                        continue
                
                # 데이터 행 추출
                row_selectors = [
                    'table.tb_list tbody tr',
                    'table tbody tr',
                    'table tr'
                ]
                
                table_data = []
                for selector in row_selectors:
                    try:
                        rows = popup_frame.query_selector_all(selector)
                        if rows:
                            for row in rows:
                                cols = row.query_selector_all('td')
                                if cols:
                                    row_data = [col.inner_text().strip() for col in cols]
                                    if row_data and any(cell.strip() for cell in row_data):
                                        table_data.append(row_data)
                            if table_data:
                                break
                    except:
                        continue
                
                if not table_data:
                    print("테이블 데이터가 없습니다")
                    browser.close()
                    return None
                
                print(f"데이터 추출 완료: {len(table_data)}개 행")
                browser.close()
                return header, table_data
                
            except Exception as e:
                print(f"테이블 데이터 추출 실패: {e}")
                browser.close()
                return None
                
    except Exception as e:
        print(f"크롤러 실행 중 오류 발생: {e}")
        return None
