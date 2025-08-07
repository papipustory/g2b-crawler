import asyncio
from playwright.async_api import async_playwright

async def run_crawler_async(query="컴퓨터"):
    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                # 실행 환경에 함께 복사된 브라우저를 사용하도록 경로를 명시합니다.
                executable_path="./pw-browsers/chromium-1091/chrome-linux/chrome",
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--single-process',
                    '--no-zygote'
                ]
            )
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto("https://shop.g2b.go.kr/", timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=10000)
            await asyncio.sleep(3)

            # 팝업 닫기
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
                    except Exception:
                        continue
                if not closed:
                    break
                await asyncio.sleep(0.5)
            await page.keyboard.press('End')
            await asyncio.sleep(1)

            # 제안공고목록 진입
            btn_selectors = [
                'a[id^="mf_wfm_container_wq_uuid_"][id$="_btnPrpblist"]',
                'a[title*="제안공고목록"]',
                'a:has-text("제안공고목록")',
                'div.w2textbox:text("제안공고목록")',
            ]
            clicked = False
            for sel in btn_selectors:
                try:
                    await page.wait_for_selector(sel, timeout=3000, state="visible")
                    elem = await page.query_selector(sel)
                    if elem and await elem.is_visible():
                        await elem.scroll_into_view_if_needed()
                        await asyncio.sleep(0.02)
                        await elem.click()
                        clicked = True
                        break
                except Exception:
                    continue
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
                    except Exception:
                        continue
            await asyncio.sleep(0.3)

            # 3개월 라디오 버튼 클릭
            radio_3month = await page.query_selector('input[title="3개월"]')
            if radio_3month:
                await radio_3month.click()
                await asyncio.sleep(1)

            # 검색어 입력
            input_elem = await page.query_selector('td[data-title="제안공고명"] input[type="text"]')
            if input_elem:
                await input_elem.fill(query)
                await asyncio.sleep(0.5)

            # 표시수 100개 선택
            select_elem = await page.query_selector('select[id*="RecordCountPerPage"]')
            if select_elem:
                await select_elem.select_option("100")
                await asyncio.sleep(1)

            # 적용/검색 버튼 클릭
            for sel in ['input[type="button"][value="적용"]', 'input[type="button"][value="검색"]']:
                try:
                    await page.wait_for_selector(sel, timeout=3000, state="visible")
                    elem = await page.query_selector(sel)
                    if elem:
                        await elem.click()
                        await asyncio.sleep(0.8)
                except Exception:
                    continue

            # 테이블 파싱
            table_elem = await page.query_selector('table[id$="grdPrpsPbanc_body_table"]')
            headers = []
            data = []
            if table_elem:
                rows = await table_elem.query_selector_all('tr')
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

                headers = ["No", "제안공고번호", "수요기관", "제안공고명",
                           "공고게시일자", "공고마감일시", "공고상태", "사유", "기타"]
                if data and len(data[0]) < len(headers):
                    headers = headers[:len(data[0])]
            await asyncio.sleep(2)

            return headers, data

    except Exception as e:
        print(f"[ERROR] {e}")
        return None
    finally:
        if browser:
            await browser.close()

def run_g2b_crawler(query="컴퓨터"):
    """
    이벤트루프 중첩 없이 1회만 실행!
    PC/Streamlit/Jupyter 어디서든 100% 일관동작
    """
    try:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Streamlit/Jupyter 환경: 중첩 방지, 반드시 1회만!
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(run_crawler_async(query))
        else:
            # 일반 실행: PC 원본과 동일!
            return asyncio.run(run_crawler_async(query))
    except Exception as e:
        print(f"[ERROR] Crawler error: {e}")
        return None
