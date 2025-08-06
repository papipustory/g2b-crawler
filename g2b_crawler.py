from playwright.sync_api import sync_playwright
import time

def close_notice_popups(page):
    """팝업 닫기"""
    for _ in range(5):
        popup_divs = page.query_selector_all("div[id^='mf_wfm_container_wq_uuid_'][class*='w2popup_window']")
        closed = False
        for popup in popup_divs:
            try:
                # 닫기 버튼 찾기
                for sel in ["button[class*='w2window_close']", "input[type='button'][value='닫기']"]:
                    btn = popup.query_selector(sel)
                    if btn:
                        btn.click()
                        time.sleep(0.2)
                        closed = True
                        break
                # 오늘 하루 체크박스
                checkbox = popup.query_selector("input[type='checkbox'][title*='오늘 하루']")
                if checkbox:
                    checkbox.check()
                    time.sleep(0.1)
                    btn = popup.query_selector("input[type='button'][value='닫기']")
                    if btn:
                        btn.click()
                        closed = True
                        break
            except:
                continue
        if not closed:
            break
        time.sleep(0.5)

def wait_and_click(page, selector, desc, timeout=3000, scroll=True):
    """요소 대기 후 클릭"""
    try:
        page.wait_for_selector(selector, timeout=timeout, state="visible")
        elem = page.query_selector(selector)
        if elem and elem.is_visible():
            if scroll:
                elem.scroll_into_view_if_needed()
                time.sleep(0.02)
            elem.click()
            return True
        return False
    except:
        return False

def run_g2b_crawler(query="컴퓨터"):
    """나라장터 크롤러 - 동기 버전"""
    browser = None
    try:
        with sync_playwright() as p:
            # Streamlit Cloud용 브라우저 옵션
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox', 
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--single-process',
                    '--no-zygote'
                ]
            )
            
            context = browser.new_context(
                viewport={'width': 1280, 'height': 720}
            )
            page = context.new_page()
            
            # 1. 사이트 접속
            print("[INFO] 나라장터 접속 중...")
            page.goto("https://shop.g2b.go.kr/", timeout=30000)
            page.wait_for_load_state('networkidle', timeout=5000)
            time.sleep(3)

            # 2. 팝업 닫기
            print("[INFO] 팝업 처리 중...")
            close_notice_popups(page)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)

            # 3. 제안공고목록 버튼 클릭
            print("[INFO] 제안공고목록 버튼 찾는 중...")
            btn_selectors = [
                'a[id^="mf_wfm_container_wq_uuid_"][id$="_btnPrpblist"]',
                'a[title*="제안공고목록"]',
                'a:has-text("제안공고목록")',
                '//a[contains(text(), "제안공고목록")]',
                'div.w2textbox:text("제안공고목록")',
            ]
            
            clicked = False
            for sel in btn_selectors:
                if wait_and_click(page, sel, "제안공고목록 버튼"):
                    clicked = True
                    break
            
            # 대체: 모든 a 태그 검색
            if not clicked:
                all_a = page.query_selector_all("a")
                for a in all_a:
                    try:
                        title = a.get_attribute("title")
                        href = a.get_attribute("href")
                        inner = a.inner_text()
                        if (title and "제안공고" in title) or (inner and "제안공고" in inner):
                            if href and href.strip() != "javascript:void(null)":
                                a.scroll_into_view_if_needed()
                                time.sleep(0.2)
                                a.click()
                                clicked = True
                                break
                    except:
                        continue

            if not clicked:
                print("[ERROR] 제안공고목록 버튼을 찾을 수 없습니다")
                browser.close()
                return None

            time.sleep(0.3)

            # 4. 3개월 설정
            print("[INFO] 검색 조건 설정 중...")
            page.evaluate("""
                const radio = document.querySelector('input[title="3개월"]');
                if (radio) {
                    radio.checked = true;
                    const event = new Event('click', { bubbles: true });
                    radio.dispatchEvent(event);
                }
            """)
            time.sleep(1)

            # 5. 검색어 입력
            input_elem = page.query_selector('td[data-title="제안공고명"] input[type="text"]')
            if input_elem:
                input_elem.fill(query, timeout=1000)

            # 6. 표시수 100개로 설정
            page.evaluate("""
                const selects = document.querySelectorAll('select[id*="RecordCountPerPage"]');
                selects.forEach(select => {
                    select.value = "100";
                    const event = new Event('change', { bubbles: true });
                    select.dispatchEvent(event);
                });
            """)
            time.sleep(1)

            # 7. 적용 및 검색
            wait_and_click(page, 'input[type="button"][value="적용"]', "적용버튼", scroll=False)
            wait_and_click(page, 'input[type="button"][value="검색"]', "검색버튼", scroll=False)
            time.sleep(0.8)

            # 8. 데이터 추출
            print("[INFO] 데이터 추출 중...")
            table_elem = page.query_selector('table[id$="grdPrpsPbanc_body_table"]')
            if table_elem:
                rows = table_elem.query_selector_all('tr')
                data = []
                for row in rows:
                    tds = row.query_selector_all('td')
                    cols = []
                    for td in tds:
                        nobr = td.query_selector('nobr')
                        if nobr:
                            text = nobr.inner_text()
                        else:
                            a = td.query_selector('a')
                            if a:
                                text = a.inner_text()
                            else:
                                text = td.inner_text()
                        cols.append(text.strip())
                    if cols and any(cols):
                        data.append(cols)

                if data:
                    headers = ["No", "제안공고번호", "수요기관", "제안공고명", 
                              "공고게시일자", "공고마감일시", "공고상태", "사유", "기타"]
                    if len(data[0]) < len(headers):
                        headers = headers[:len(data[0])]
                    
                    print(f"[INFO] 크롤링 성공: {len(data)}개 항목")
                    browser.close()
                    return headers, data

            browser.close()
            return None

    except Exception as e:
        print(f"[ERROR] 크롤링 실패: {str(e)}")
        if browser:
            browser.close()
        return None
