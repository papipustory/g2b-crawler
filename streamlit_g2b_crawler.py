import os
import time
from playwright.sync_api import sync_playwright

# 크롤링 함수 정의
def run_g2b_crawler(query: str = "컴퓨터"):
    # 환경 변수 설정 (Streamlit Cloud 최적화)
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/tmp/playwright"
    os.environ["PYPPETEER_HOME"] = "/tmp/pyppeteer"
    os.environ["CHROME_BIN"] = "/usr/bin/chromium-browser"
    os.environ["CHROMIUM_FLAGS"] = "--no-sandbox --disable-dev-shm-usage"

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--single-process",
                "--disable-software-rasterizer",
            ]
        )
        page = browser.new_page()

        # (1) 나라장터 제안공고 페이지 진입
        url = "https://shop.g2b.go.kr/"
        page.goto(url)

        # (2) 팝업 닫기(존재할 때만)
        try:
            page.wait_for_selector('button.close, .popup_close, .layerPopup-close', timeout=2000)
            page.click('button.close, .popup_close, .layerPopup-close')
        except Exception:
            pass  # 팝업이 없거나 이미 닫힘

        # (3) '제안공고목록' 버튼 클릭
        try:
            page.wait_for_selector('a[onclick*="popNoticeList"]', timeout=5000)
            page.click('a[onclick*="popNoticeList"]')
        except Exception as e:
            browser.close()
            return None

        # (4) 팝업 frame 탐색
        frames = page.frames
        popup_frame = None
        for frame in frames:
            if "popNoticeList" in frame.url or frame.url.startswith("about:blank"):
                popup_frame = frame
                break
        if not popup_frame:
            browser.close()
            return None

        # (5) 검색창에 입력/검색 클릭
        try:
            popup_frame.fill('input[name="searchWrd"]', query)
            popup_frame.click('button[onclick*="fn_search"]')
            time.sleep(2)  # 검색 결과 로딩 대기
        except Exception as e:
            browser.close()
            return None

        # (6) 표 데이터 추출
        try:
            popup_frame.wait_for_selector('table.tb_list', timeout=10000)
            rows = popup_frame.query_selector_all('table.tb_list tbody tr')
            table_data = []
            for row in rows:
                cols = [col.inner_text().strip() for col in row.query_selector_all('td')]
                if cols:
                    table_data.append(cols)
            if not table_data:
                browser.close()
                return None
            header = [th.inner_text().strip() for th in popup_frame.query_selector_all('table.tb_list thead th')]
        except Exception as e:
            browser.close()
            return None

        browser.close()
        return header, table_data
