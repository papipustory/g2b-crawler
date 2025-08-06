import asyncio
from playwright.async_api import async_playwright
import nest_asyncio

# Streamlit Cloud에서 asyncio 실행 가능하게
nest_asyncio.apply()

async def close_notice_popups(page):
    """팝업 닫기"""
    for _ in range(5):
        popup_divs = await page.query_selector_all("div[id^='mf_wfm_container_wq_uuid_'][class*='w2popup_window']")
        closed = False
        for popup in popup_divs:
            try:
                for sel in ["button[class*='w2window_close']", "input[type='button'][value='닫기']"]:
                    btn = await popup.query_selector(sel)
                    if btn:
                        await btn.click()
                        await asyncio.sleep(0.2)
                        closed = True
                        break
                checkbox = await popup.query_selector("input[type='checkbox'][title*='오늘 하루']")
                if checkbox:
                    await checkbox.check()
                    await asyncio.sleep(0.1)
                    btn = await popup.query_selector("input[type='button'][value='닫기']")
                    if btn:
                        await btn.click()
                        closed = True
                        break
            except:
                continue
        if not closed:
            break
        await asyncio.sleep(0.5)

async def wait_and_click(page, selector, desc, timeout=3000, scroll=True):
    """요소 대기 후 클릭"""
    try:
        await page.wait_for_selector(selector, timeout=timeout, state="visible")
        elem = await page.query_selector(selector)
        if elem and await elem.is_visible():
            if scroll:
                await elem.scroll_into_view_if_needed()
                await asyncio.sleep(0.02)
            await elem.click()
            return True
        return False
    except:
        return False

async def run_crawler_async(query="컴퓨터"):
    """비동기 크롤러"""
    browser = None
    try:
        async with async_playwright() as p:
            # Streamlit Cloud용 브라우저 설정
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--single-process',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process'
                ]
            )
            context = await browser.new_context()
            page = await context.new_page()
            
            # 1. 사이트 접속
            await page.goto("https://shop.g2b.go.kr/", timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=5000)
            await asyncio.sleep(3)

            # 2. 팝업 닫기
            await close_notice_popups(page)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)

            # 3. 제안공고목록 버튼 클릭
            btn_selectors = [
                'a[id^="mf_wfm_container_wq_uuid_"][id$="_btnPrpblist"]',
                'a[title*="제안공고목록"]',
                'a:has-text("제안공고목록")',
                '//a[contains(text(), "제안공고목록")]',
                'div.w2textbox:text("제안공고목록")',
            ]
            
            clicked = False
            for sel in btn_selectors:
                if await wait_and_click(page, sel, "제안공고목록 버튼"):
                    clicked = True
                    break
            
            if not clicked:
                all_a = await page.query_selector_all("a")
                for a in all_a:
                    try:
                        title = await a.get_attribute("title")
                        href = await a.get_attribute("href")
                        inner = await a.inner_text()
                        if (title and "제안공고" in title) or (inner and "제안공고" in inner):
                            if href and href.strip() != "javascript:void(null)":
                                await a.scroll_into_view_if_needed()
                                await asyncio.sleep(0.2)
                                await a.click()
                                clicked = True
                                break
                    except:
                        continue

            if not clicked:
                await browser.close()
                return None

            await asyncio.sleep(0.3)

            # 4. 3개월 설정
            await page.evaluate("""
                const radio = document.querySelector('input[title="3개월"]');
                if (radio) {
                    radio.checked = true;
                    const event = new Event('click', { bubbles: true });
                    radio.dispatchEvent(event);
                }
            """)
            await asyncio.sleep(1)

            # 5. 검색어 입력
            input_elem = await page.query_selector('td[data-title="제안공고명"] input[type="text"]')
            if input_elem:
                await input_elem.fill(query, timeout=1000)

            # 6. 표시수 100개 설정
            await page.evaluate("""
                const selects = document.querySelectorAll('select[id*="RecordCountPerPage"]');
                selects.forEach(select => {
                    select.value = "100";
                    const event = new Event('change', { bubbles: true });
                    select.dispatchEvent(event);
                });
            """)
            await asyncio.sleep(1)

            # 7. 적용 및 검색
            await wait_and_click(page, 'input[type="button"][value="적용"]', "적용버튼", scroll=False)
            await wait_and_click(page, 'input[type="button"][value="검색"]', "검색버튼", scroll=False)
            await asyncio.sleep(0.8)

            # 8. 데이터 추출
            table_elem = await page.query_selector('table[id$="grdPrpsPbanc_body_table"]')
            if table_elem:
                rows = await table_elem.query_selector_all('tr')
                data = []
                for row in rows:
                    tds = await row.query_selector_all('td')
                    cols = []
                    for td in tds:
                        nobr = await td.query_selector('nobr')
                        if nobr:
                            text = await nobr.inner_text()
                        else:
                            a = await td.query_selector('a')
                            if a:
                                text = await a.inner_text()
                            else:
                                text = await td.inner_text()
                        cols.append(text.strip())
                    if cols and any(cols):
                        data.append(cols)

                if data:
                    headers = ["No", "제안공고번호", "수요기관", "제안공고명", 
                              "공고게시일자", "공고마감일시", "공고상태", "사유", "기타"]
                    if len(data[0]) < len(headers):
                        headers = headers[:len(data[0])]
                    
                    await browser.close()
                    return headers, data

            await browser.close()
            return None

    except Exception as e:
        print(f"Error occurred: {e}")
        if browser:
            await browser.close()
        return None

def run_g2b_crawler(query="컴퓨터"):
    """동기 함수 래퍼 (Streamlit용)"""
    try:
        # 비동기 함수를 동기적으로 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(run_crawler_async(query))
        loop.close()
        return result
    except Exception as e:
        print(f"Crawler error: {e}")
        return None
