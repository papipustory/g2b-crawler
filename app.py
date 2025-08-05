import os
import time
import streamlit as st

# Playwright 환경 준비
from playwright.sync_api import sync_playwright

# Streamlit 환경에서 Chromium을 안전하게 실행하기 위한 환경 변수 설정
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/tmp/playwright"
os.environ["PYPPETEER_HOME"] = "/tmp/pyppeteer"
# Streamlit Cloud의 리눅스 컨테이너에서는 sandbox 문제로 실행이 안 되는 경우가 있어 추가 환경변수 필요
os.environ["CHROME_BIN"] = "/usr/bin/chromium-browser"
os.environ["CHROMIUM_FLAGS"] = "--no-sandbox --disable-dev-shm-usage"

def run_g2b_crawler(query: str = "컴퓨터"):
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
        st.info("나라장터 사이트 접속 중...")

        # (1) 나라장터 제안공고 목록 팝업 진입
        url = "https://shop.g2b.go.kr/"
        page.goto(url)
        st.write("사이트 진입 완료")

        # (2) 팝업 닫기(존재할 때만)
        try:
            page.wait_for_selector('button.close, .popup_close, .layerPopup-close', timeout=2000)
            page.click('button.close, .popup_close, .layerPopup-close')
            st.write("팝업 닫기 성공")
        except Exception:
            st.write("팝업 없음 또는 닫기 스킵")

        # (3) '제안공고목록' 버튼 클릭
        try:
            page.wait_for_selector('a[onclick*="popNoticeList"]', timeout=5000)
            page.click('a[onclick*="popNoticeList"]')
            st.write("제안공고목록 진입")
        except Exception as e:
            st.error(f"'제안공고목록' 버튼 클릭 실패: {e}")
            browser.close()
            return None

        # (4) 팝업 내 frame 탐색 (iframe or 새창)
        # Streamlit Cloud에서 팝업이 새탭이 아닌 layer/frame에 뜸
        frames = page.frames
        popup_frame = None
        for frame in frames:
            if "popNoticeList" in frame.url or frame.url.startswith("about:blank"):
                popup_frame = frame
                break
        if not popup_frame:
            st.error("팝업 frame을 찾을 수 없음")
            browser.close()
            return None

        st.write("팝업 진입 성공")

        # (5) 검색창에 '컴퓨터' 입력 후 검색 버튼 클릭
        try:
            popup_frame.fill('input[name="searchWrd"]', query)
            popup_frame.click('button[onclick*="fn_search"]')
            st.write(f"'{query}' 검색 실행")
            time.sleep(2)  # 검색 결과 로딩 대기
        except Exception as e:
            st.error(f"검색어 입력/검색 실패: {e}")
            browser.close()
            return None

        # (6) 표 데이터 추출
        try:
            # 10초 대기(최대) 후 테이블 로딩
            popup_frame.wait_for_selector('table.tb_list', timeout=10000)
            rows = popup_frame.query_selector_all('table.tb_list tbody tr')
            table_data = []
            for row in rows:
                cols = [col.inner_text().strip() for col in row.query_selector_all('td')]
                if cols:
                    table_data.append(cols)
            if not table_data:
                st.warning("검색 결과 없음")
                browser.close()
                return None
            # 컬럼명 추출
            header = [th.inner_text().strip() for th in popup_frame.query_selector_all('table.tb_list thead th')]
            st.success(f"검색 결과 {len(table_data)}건 추출 성공")
        except Exception as e:
            st.error(f"표 추출 실패: {e}")
            browser.close()
            return None

        browser.close()
        return header, table_data

# Streamlit UI
st.title("나라장터 제안공고 크롤러 (Streamlit Cloud 최적화)")
search_query = st.text_input("검색어를 입력하세요", value="컴퓨터")
run_btn = st.button("크롤링 실행")

if run_btn:
    st.write("크롤링을 시작합니다...")
    result = run_g2b_crawler(search_query)
    if result:
        header, table_data = result
        import pandas as pd
        df = pd.DataFrame(table_data, columns=header)
        st.dataframe(df)
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("CSV 다운로드", csv, file_name="g2b_result.csv", mime="text/csv")
    else:
        st.error("크롤링 실패 또는 데이터 없음")

# =====================
# 추가 참고사항 및 팁
# =====================
# 1. requirements.txt 예시
#   streamlit
#   playwright
#   pandas
# 2. packages.txt 예시 (필요시)
#   chromium
#   chromium-driver
# 3. 최초 배포/런칭시 playwright install 명령어 추가 필요할 수 있음
#   RUN playwright install chromium
# 4. Streamlit Cloud 환경에선 headless + no-sandbox + disable-dev-shm-usage가 필수
# 5. '팝업'을 새 탭이 아닌 iframe/layer로 띄우는 G2B 특성을 감안해 frame 검색 구조화함
