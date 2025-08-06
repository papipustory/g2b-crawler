import asyncio
from playwright.async_api import async_playwright
import nest_asyncio
import urllib.request
import json

def get_server_country():
    """서버의 공인 IP/국가코드/통신사 반환"""
    try:
        with urllib.request.urlopen("https://ipinfo.io/json", timeout=5) as url:
            data = json.loads(url.read().decode())
            ip = data.get("ip", "")
            country = data.get("country", "")
            org = data.get("org", "")
            return ip, country, org
    except Exception as e:
        print(f"[ERROR] 서버 위치 확인 실패: {e}")
        return None, None, None

def test_site_access(url="https://shop.g2b.go.kr/"):
    """해당 URL이 서버(클라우드/로컬)에서 정상 접근 가능한지 미리 테스트"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read(2048).decode(errors='ignore')
            lower = html.lower()
            if ("접근" in lower and "제한" in lower) or ("blocked" in lower) or ("captcha" in lower) or ("cloudflare" in lower):
                return False, "사이트에서 접근이 제한/차단됨 (페이지 내 경고 탐지)"
            if resp.status not in (200, 302):
                return False, f"비정상 응답코드: {resp.status}"
            return True, "정상 접근 가능"
    except Exception as e:
        return False, f"접근 실패: {e}"

async def close_notice_popups(page):
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

async def wait_and_click(page, selector, desc, timeout=3000, scroll=True):
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
    except Exception:
        return False

async def run_crawler_async(query="컴퓨터"):
    browser = None
    try:
        # 서버 위치/접속 정보 로그
        ip, country, org = get_server_country()
        print(f"[INFO] 서버 공인IP: {ip}, 국가: {country}, 통신사: {org}")
        ok, access_msg = test_site_access("https://shop.g2b.go.kr/")
        print(f"[INFO] 사이트 접근 체크: {access_msg}")
        if not ok:
            raise RuntimeError(f"사이트 접근 차단: {access_msg}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(
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
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto("https://shop.g2b.go.kr/", timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=10000)
            print(f"[INFO] 접속 페이지 URL: {page.url}")
            html = await page.content()
            print(f"[INFO] 페이지 헤드: {html[:500]}")
            await asyncio.sleep(3)

            await close_notice_popups(page)
            await page.keyboard.press('End')
            await asyncio.sleep(1)

            btn_selectors = [
                'a[id^="mf_wfm_container_wq_uuid_"][id$="_btnPrpblist"]',
                'a[title*="제안공고목록"]',
                'a:has-text("제안공고목록")',
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
                    except Exception:
                        continue

            await asyncio.sleep(0.3)

            radio_3month = await page.query_selector('input[title="3개월"]')
            if radio_3month:
                await radio_3month.click()
                await asyncio.sleep(1)

            input_elem = await page.query_selector('td[data-title="제안공고명"] input[type="text"]')
            if input_elem:
                await input_elem.fill(query)
                await asyncio.sleep(0.5)

            select_elem = await page.query_selector('select[id*="RecordCountPerPage"]')
            if select_elem:
                await select_elem.select_option("100")
                await asyncio.sleep(1)

            await wait_and_click(page, 'input[type="button"][value="적용"]', "적용버튼", scroll=False)
            await wait_and_click(page, 'input[type="button"][value="검색"]', "검색버튼", scroll=False)
            await asyncio.sleep(0.8)

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
    """동기 래퍼: 접속 진단 포함, Streamlit/Jupyter에서도 Future Cancelled 방지"""
    try:
        try:
            loop = asyncio.get_running_loop()
            import nest_asyncio
            nest_asyncio.apply()
            return loop.run_until_complete(run_crawler_async(query))
        except RuntimeError:
            return asyncio.run(run_crawler_async(query))
    except Exception as e:
        print(f"[ERROR] Crawler error: {e}")
        return None
