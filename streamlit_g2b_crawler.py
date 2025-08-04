import streamlit as st
import asyncio
import pandas as pd
import openpyxl
from openpyxl.styles import Alignment
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

st.set_page_config(page_title="나라장터 제안공고 크롤러", layout="centered")

st.title("💻 나라장터 제안공고 크롤링")

# Playwright 브라우저 설치 확인 및 설치
@st.cache_resource
def ensure_playwright_installed():
    try:
        import subprocess
        result = subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], 
                              capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            st.error(f"Playwright 설치 실패: {result.stderr}")
            return False
        return True
    except Exception as e:
        st.error(f"Playwright 설치 중 오류: {e}")
        return False

def run_crawler():
    """별도 스레드에서 크롤러 실행"""
    
    async def wait_and_click(page, selector, name, timeout=3000, scroll=True):
        try:
            if scroll:
                await page.evaluate(f'''
                    var el = document.querySelector('{selector}');
                    if (el) el.scrollIntoView();
                ''')
            await page.wait_for_selector(selector, timeout=timeout)
            await page.click(selector)
            return True
        except Exception:
            print(f"[실패] {name} 클릭 실패: selector {selector}")
            return False

    async def close_notice_popups(page):
        try:
            popup_buttons = await page.query_selector_all("div.popup a")
            for btn in popup_buttons:
                text = await btn.inner_text()
                if "닫기" in text:
                    await btn.click()
        except:
            pass

    async def main():
        browser = None
        try:
            # Playwright 동적 import (설치 후)
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                # 브라우저 실행 옵션
                browser_args = [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--single-process',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
                
                browser = await p.chromium.launch(
                    headless=True,
                    args=browser_args
                )
                
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                )
                
                page = await context.new_page()
                
                # 타임아웃 증가
                await page.goto("https://shop.g2b.go.kr/", timeout=60000)
                await page.wait_for_load_state('networkidle', timeout=60000)
                await asyncio.sleep(3)

                await close_notice_popups(page)
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(2)

                # 제안공고목록 버튼 찾기
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
                                    await asyncio.sleep(0.5)
                                    await a.click()
                                    clicked = True
                                    break
                        except:
                            continue
                
                if not clicked:
                    return {"error": "제안공고목록 버튼을 찾을 수 없습니다."}

                await asyncio.sleep(2)

                # 3개월 라디오 버튼 선택
                await page.evaluate("""
                    const radio = document.querySelector('input[title="3개월"]');
                    if (radio) {
                        radio.checked = true;
                        const event = new Event('click', { bubbles: true });
                        radio.dispatchEvent(event);
                    }
                """)
                await asyncio.sleep(1)

                # 검색어 입력
                input_elem = await page.query_selector('td[data-title="제안공고명"] input[type="text"]')
                if input_elem:
                    await input_elem.fill('컴퓨터')

                # 페이지당 표시 개수 설정
                await page.evaluate("""
                    const selects = document.querySelectorAll('select[id*="RecordCountPerPage"]');
                    selects.forEach(select => {
                        select.value = "100";
                        const event = new Event('change', { bubbles: true });
                        select.dispatchEvent(event);
                    });
                """)
                await asyncio.sleep(1)

                # 적용 및 검색 버튼 클릭
                await wait_and_click(page, 'input[type="button"][value="적용"]', "적용버튼", scroll=False)
                await asyncio.sleep(1)
                await wait_and_click(page, 'input[type="button"][value="검색"]', "검색버튼", scroll=False)
                await asyncio.sleep(3)

                # 테이블 데이터 추출
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
                        new_df = pd.DataFrame(data)
                        headers = ["No", "제안공고번호", "수요기관", "제안공고명", "공고게시일자", "공고마감일시", "공고상태", "사유", "기타"]
                        if len(new_df.columns) < len(headers):
                            headers = headers[:len(new_df.columns)]
                        elif len(new_df.columns) > len(headers):
                            new_df = new_df.iloc[:, :len(headers)]
                        new_df.columns = headers

                        # 임시 파일 경로
                        file_path = '/tmp/g2b_result.xlsx'
                        
                        # 기존 데이터와 병합
                        if os.path.exists(file_path):
                            try:
                                old_df = pd.read_excel(file_path)
                                combined_df = pd.concat([old_df, new_df])
                                combined_df.drop_duplicates(subset="제안공고번호", keep='last', inplace=True)
                                combined_df.reset_index(drop=True, inplace=True)
                            except:
                                combined_df = new_df
                        else:
                            combined_df = new_df

                        # Excel 파일 저장
                        combined_df.to_excel(file_path, index=False)

                        # 스타일링
                        wb = openpyxl.load_workbook(file_path)
                        ws = wb.active
                        align = Alignment(horizontal='center', vertical='center')
                        for row in ws.iter_rows():
                            for cell in row:
                                cell.alignment = align
                        col_widths = [3.5, 17, 44, 55, 15, 17.5, 17, 17, 17]
                        for i, width in enumerate(col_widths, start=1):
                            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = width
                        wb.save(file_path)

                        return {"success": True, "data": combined_df, "file_path": file_path}
                    else:
                        return {"error": "공고 목록을 찾을 수 없습니다."}
                else:
                    return {"error": "테이블을 찾을 수 없습니다."}

        except Exception as e:
            return {"error": f"크롤링 중 오류 발생: {str(e)}"}

        finally:
            if browser:
                await browser.close()

    # 새로운 이벤트 루프에서 실행
    def run_in_new_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(main())
        finally:
            loop.close()
    
    return run_in_new_loop()

if st.button("크롤링 시작"):
    # Playwright 설치 확인
    if not ensure_playwright_installed():
        st.stop()
    
    st.info("크롤링을 시작합니다. 잠시만 기다려 주세요... (1-2분 소요)")
    
    # 프로그레스 바
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 별도 스레드에서 크롤링 실행
    with ThreadPoolExecutor(max_workers=1) as executor:
        try:
            status_text.text("브라우저 시작 중...")
            progress_bar.progress(20)
            
            future = executor.submit(run_crawler)
            
            # 결과 대기
            import time
            for i in range(21, 90):
                time.sleep(0.1)
                progress_bar.progress(i)
                if i == 40:
                    status_text.text("페이지 로딩 중...")
                elif i == 60:
                    status_text.text("데이터 수집 중...")
                elif i == 80:
                    status_text.text("결과 처리 중...")
            
            result = future.result(timeout=180)  # 3분 타임아웃
            
            progress_bar.progress(100)
            status_text.text("완료!")
            
            if "error" in result:
                st.error(f"❌ {result['error']}")
            elif "success" in result:
                st.success("✅ 크롤링 완료!")
                
                # 데이터 미리보기
                st.subheader("📊 결과 미리보기")
                st.dataframe(result['data'].head(10))
                
                # 다운로드 버튼
                with open(result['file_path'], 'rb') as f:
                    st.download_button(
                        label="📥 Excel 파일 다운로드",
                        data=f.read(),
                        file_name="g2b_result.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
                st.info(f"총 {len(result['data'])}개의 공고를 수집했습니다.")
                
        except Exception as e:
            st.error(f"❌ 실행 중 오류: {str(e)}")
        finally:
            progress_bar.empty()
            status_text.empty()
