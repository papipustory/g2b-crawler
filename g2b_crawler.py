import os
import time
import logging
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_g2b_crawler(query: str = "컴퓨터", max_retries: int = 3):
    """
    나라장터 제안공고 크롤러
    Streamlit Cloud 환경에 최적화된 버전
    """
    
    # Streamlit Cloud 환경 변수 설정
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"  # 시스템 기본 경로 사용
    
    for attempt in range(max_retries):
        try:
            logger.info(f"크롤링 시도 {attempt + 1}/{max_retries}")
            
            with sync_playwright() as p:
                # Chromium 브라우저 실행 (Streamlit Cloud 최적화 옵션)
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-accelerated-2d-canvas',
                        '--no-first-run',
                        '--no-zygote',
                        '--single-process',  # 중요: 단일 프로세스 모드
                        '--disable-gpu',
                        '--disable-features=VizDisplayCompositor',
                        '--disable-web-security',
                        '--disable-features=IsolateOrigins',
                        '--disable-site-isolation-trials'
                    ]
                )
                
                # 컨텍스트 생성 (더 안정적인 설정)
                context = browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                
                page = context.new_page()
                page.set_default_timeout(30000)  # 30초 타임아웃
                
                logger.info("나라장터 페이지 접속 시도...")
                
                # 1. 메인 페이지 접속
                url = "https://shop.g2b.go.kr/"
                response = page.goto(url, wait_until='networkidle', timeout=30000)
                
                if not response or response.status != 200:
                    logger.error(f"페이지 접속 실패: {response.status if response else 'No response'}")
                    raise Exception("페이지 접속 실패")
                
                logger.info("페이지 접속 성공")
                
                # 2. 페이지 로딩 대기
                page.wait_for_load_state('domcontentloaded')
                time.sleep(2)  # 추가 대기
                
                # 3. 팝업 처리 (여러 선택자 시도)
                popup_selectors = [
                    'button.close',
                    '.popup_close',
                    '.layerPopup-close',
                    'a.close',
                    'button[onclick*="close"]',
                    'img[alt*="닫기"]'
                ]
                
                for selector in popup_selectors:
                    try:
                        if page.locator(selector).count() > 0:
                            page.click(selector, timeout=2000)
                            logger.info(f"팝업 닫기 성공: {selector}")
                            break
                    except:
                        continue
                
                # 4. 제안공고목록 버튼 찾기 및 클릭
                logger.info("제안공고목록 버튼 찾는 중...")
                
                # 여러 가능한 선택자 시도
                button_selectors = [
                    'a[onclick*="popNoticeList"]',
                    'a:has-text("제안공고목록")',
                    'button:has-text("제안공고목록")',
                    '//a[contains(text(), "제안공고목록")]',
                    '//button[contains(text(), "제안공고목록")]'
                ]
                
                button_clicked = False
                for selector in button_selectors:
                    try:
                        if selector.startswith('//'):
                            page.click(selector, timeout=5000)
                        else:
                            page.click(selector, timeout=5000)
                        button_clicked = True
                        logger.info(f"제안공고목록 버튼 클릭 성공: {selector}")
                        break
                    except:
                        continue
                
                if not button_clicked:
                    logger.error("제안공고목록 버튼을 찾을 수 없습니다")
                    raise Exception("제안공고목록 버튼 없음")
                
                # 5. 새 창/프레임 대기
                time.sleep(3)
                
                # 팝업 윈도우 처리
                if len(context.pages) > 1:
                    # 새 창이 열린 경우
                    popup_page = context.pages[-1]
                    logger.info("새 창에서 작업 진행")
                    
                    # 검색 수행
                    popup_page.wait_for_load_state('domcontentloaded')
                    popup_page.fill('input[name="searchWrd"]', query)
                    popup_page.click('button[onclick*="fn_search"]')
                    time.sleep(3)
                    
                    # 데이터 추출
                    popup_page.wait_for_selector('table.tb_list', timeout=10000)
                    header = [th.inner_text().strip() for th in popup_page.query_selector_all('table.tb_list thead th')]
                    
                    rows = popup_page.query_selector_all('table.tb_list tbody tr')
                    table_data = []
                    for row in rows:
                        cols = [col.inner_text().strip() for col in row.query_selector_all('td')]
                        if cols and any(cols):  # 빈 행 제외
                            table_data.append(cols)
                    
                else:
                    # iframe 처리
                    frames = page.frames
                    popup_frame = None
                    
                    for frame in frames:
                        if "popNoticeList" in frame.url or "pop" in frame.url.lower():
                            popup_frame = frame
                            break
                    
                    if not popup_frame and len(frames) > 1:
                        popup_frame = frames[-1]  # 마지막 프레임 시도
                    
                    if not popup_frame:
                        logger.error("팝업 프레임을 찾을 수 없습니다")
                        raise Exception("팝업 프레임 없음")
                    
                    logger.info("iframe에서 작업 진행")
                    
                    # 검색 수행
                    popup_frame.fill('input[name="searchWrd"]', query)
                    popup_frame.click('button[onclick*="fn_search"]')
                    time.sleep(3)
                    
                    # 데이터 추출
                    popup_frame.wait_for_selector('table.tb_list', timeout=10000)
                    header = [th.inner_text().strip() for th in popup_frame.query_selector_all('table.tb_list thead th')]
                    
                    rows = popup_frame.query_selector_all('table.tb_list tbody tr')
                    table_data = []
                    for row in rows:
                        cols = [col.inner_text().strip() for col in row.query_selector_all('td')]
                        if cols and any(cols):
                            table_data.append(cols)
                
                browser.close()
                
                if table_data:
                    logger.info(f"크롤링 성공: {len(table_data)}개 항목")
                    return header, table_data
                else:
                    logger.warning("검색 결과가 없습니다")
                    return None
                    
        except PlaywrightTimeout as e:
            logger.error(f"타임아웃 오류: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
            return None
            
        except Exception as e:
            logger.error(f"크롤링 오류: {e}")
            if attempt < max_retries - 1:
                time.sleep(5)
                continue
            return None
    
    return None
