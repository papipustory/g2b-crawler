import asyncio
import streamlit as st
from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright
import time  # 동기 Playwright 버전에서 지연을 위해 사용
import pandas as pd
import os
import openpyxl
from openpyxl.styles import Alignment
import base64
import subprocess
import sys

# Playwright 브라우저 설치 함수
@st.cache_resource
def install_playwright() -> bool:
    """
    Playwright용 브라우저 바이너리를 설치합니다.

    Streamlit Cloud에서는 시스템 패키지가 이미 `packages.txt`를 통해 설치되므로
    여기서는 `playwright install`만 호출합니다. 여러 명령을 시도해보고,
    성공하면 True를 반환합니다.
    """
    try:
        with st.spinner("브라우저를 설치하는 중입니다... (최초 1회만 실행됩니다)"):
            install_cmds = [
                # python -m playwright install (브라우저 전체 설치)
                [sys.executable, "-m", "playwright", "install"],
                # 특정 브라우저만 설치
                [sys.executable, "-m", "playwright", "install", "chromium"],
                # fallback to playwright executable in PATH
                ["playwright", "install"]
            ]
            for cmd in install_cmds:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                    if result.returncode == 0:
                        st.success("브라우저 설치 완료!")
                        return True
                except Exception:
                    # 다른 명령 시도로 넘어갑니다.
                    continue
            st.error("브라우저 설치에 실패했습니다. 관리자에게 문의하세요.")
            return False
    except Exception as e:
        st.error(f"브라우저 설치 중 오류: {str(e)}")
        return False

# 팝업창 닫기 함수
async def close_notice_popups(page):
    """공지사항 팝업을 닫습니다."""
    try:
        for _ in range(5):
            popup_divs = await page.query_selector_all("div[id^='mf_wfm_container_wq_uuid_'][class*='w2popup_window']")
            for popup in popup_divs:
                try:
                    # 닫기 버튼 찾기
                    for sel in ["button[class*='w2window_close']", "input[type='button'][value='닫기']"]:
                        btn = await popup.query_selector(sel)
                        if btn:
                            await btn.click()
                            await asyncio.sleep(0.2)
                            break
                    
                    # "오늘 하루 보지 않기" 체크박스
                    checkbox = await popup.query_selector("input[type='checkbox'][title*='오늘 하루']")
                    if checkbox:
                        await checkbox.check()
                        await asyncio.sleep(0.1)
                        btn = await popup.query_selector("input[type='button'][value='닫기']")
                        if btn:
                            await btn.click()
                            break
                except Exception:
                    continue
            await asyncio.sleep(0.5)
    except Exception as e:
        print(f"팝업 닫기 중 오류: {e}")

# 버튼 대기 및 클릭 함수
async def wait_and_click(page, selector, desc, timeout=3000, scroll=True):
    """요소를 기다리고 클릭합니다."""
    try:
        await page.wait_for_selector(selector, timeout=timeout, state="visible")
        elem = await page.query_selector(selector)
        if elem and await elem.is_visible():
            if scroll:
                await elem.scroll_into_view_if_needed()
                await asyncio.sleep(0.1)
            await elem.click()
            return True
        return False
    except Exception as e:
        print(f"{desc} 클릭 실패: {e}")
        return False

# 크롤링 함수
async def crawl_and_save(search_term, progress_callback=None):
    """G2B 사이트를 크롤링하여 데이터를 수집합니다."""
    result_msg = ""
    browser = None
    
    try:
        if progress_callback:
            progress_callback("브라우저 시작 중...")
            
        async with async_playwright() as p:
            # 브라우저 옵션 설정
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-extensions',
                    '--no-first-run',
                    '--disable-default-apps'
                ]
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            
            page = await context.new_page()
            
            if progress_callback:
                progress_callback("G2B 사이트 접속 중...")
            
            # G2B 사이트 접속
            await page.goto("https://shop.g2b.go.kr/", timeout=30000)
            await page.wait_for_load_state('networkidle', timeout=10000)
            await asyncio.sleep(3)

            if progress_callback:
                progress_callback("팝업 닫는 중...")
            
            # 팝업 닫기
            await close_notice_popups(page)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)

            if progress_callback:
                progress_callback("제안공고목록 페이지로 이동 중...")
            
            # 제안공고목록 버튼 클릭
            btn_selectors = [
                'a[id^="mf_wfm_container_wq_uuid_"][id$="_btnPrpblist"]',
                'a[title*="제안공고목록"]',
                'a:has-text("제안공고목록")',
                '//a[contains(text(), "제안공고목록")]'
            ]
            
            clicked = False
            for sel in btn_selectors:
                if await wait_and_click(page, sel, "제안공고목록 버튼"):
                    clicked = True
                    break
            
            if not clicked:
                raise Exception("제안공고목록 버튼을 찾을 수 없습니다.")

            await asyncio.sleep(2)

            if progress_callback:
                progress_callback("검색 조건 설정 중...")
            
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
                await input_elem.fill(search_term, timeout=5000)
            else:
                raise Exception("검색어 입력창을 찾을 수 없습니다.")

            # 페이지당 레코드 수를 100으로 설정
            await page.evaluate("""
                const selects = document.querySelectorAll('select[id*="RecordCountPerPage"]');
                selects.forEach(select => {
                    select.value = "100";
                    const event = new Event('change', { bubbles: true });
                    select.dispatchEvent(event);
                });
            """)
            await asyncio.sleep(1)

            # 적용 버튼 클릭
            if not await wait_and_click(page, 'input[type="button"][value="적용"]', "적용버튼", scroll=False):
                print("적용 버튼을 찾을 수 없어 건너뜁니다.")

            if progress_callback:
                progress_callback("검색 실행 중...")
            
            # 검색 버튼 클릭
            if not await wait_and_click(page, 'input[type="button"][value="검색"]', "검색버튼", scroll=False):
                raise Exception("검색 버튼을 찾을 수 없습니다.")
            
            await asyncio.sleep(3)

            if progress_callback:
                progress_callback("데이터 수집 중...")
            
            # 테이블 데이터 추출
            table_elem = await page.query_selector('table[id$="grdPrpsPbanc_body_table"]')
            if not table_elem:
                raise Exception("데이터 테이블을 찾을 수 없습니다.")

            rows = await table_elem.query_selector_all('tr')
            data = []
            
            for row in rows:
                tds = await row.query_selector_all('td')
                cols = []
                for td in tds:
                    try:
                        # nobr 태그 내용 우선 확인
                        nobr = await td.query_selector('nobr')
                        if nobr:
                            text = await nobr.inner_text()
                        else:
                            # a 태그 내용 확인
                            a = await td.query_selector('a')
                            text = await a.inner_text() if a else await td.inner_text()
                        cols.append(text.strip())
                    except Exception:
                        cols.append("")
                
                if cols and any(col.strip() for col in cols):
                    data.append(cols)

            if not data:
                return "⚠️ 검색 결과가 없습니다."

            if progress_callback:
                progress_callback("데이터 저장 중...")
            
            # DataFrame 생성
            new_df = pd.DataFrame(data)
            headers = ["No", "제안공고번호", "수요기관", "제안공고명", "공고게시일자", "공고마감일시", "공고상태", "사유", "기타"]
            new_df.columns = headers[:len(new_df.columns)]
            new_df.insert(0, "검색어", search_term)

            # 파일 저장
            file_path = 'g2b_result.xlsx'
            if os.path.exists(file_path):
                try:
                    old_df = pd.read_excel(file_path)
                    combined_df = pd.concat([old_df, new_df], ignore_index=True)
                    combined_df.drop_duplicates(subset="제안공고번호", keep='last', inplace=True)
                    combined_df.reset_index(drop=True, inplace=True)
                except Exception:
                    combined_df = new_df
            else:
                combined_df = new_df

            # 엑셀 파일 저장 및 포맷팅
            combined_df.to_excel(file_path, index=False)

            # 엑셀 파일 포맷팅
            try:
                wb = openpyxl.load_workbook(file_path)
                ws = wb.active
                align = Alignment(horizontal='center', vertical='center')
                
                for row in ws.iter_rows():
                    for cell in row:
                        cell.alignment = align
                
                # 컬럼 너비 설정
                col_widths = [15, 3.5, 17, 44, 55, 15, 17.5, 17, 17, 17]
                for i, width in enumerate(col_widths[:ws.max_column], start=1):
                    col_letter = openpyxl.utils.get_column_letter(i)
                    ws.column_dimensions[col_letter].width = width
                
                wb.save(file_path)
            except Exception as e:
                print(f"엑셀 포맷팅 중 오류: {e}")

            result_msg = f"✅ 크롤링 완료: `{search_term}` 검색어로 {len(data)}건의 데이터를 수집하여 저장했습니다."

    except Exception as e:
        result_msg = f"❌ 오류 발생: {str(e)}"
        print(f"크롤링 오류: {e}")
    
    finally:
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
    
    return result_msg

# -----------------------------------------------------------------------------
# 동기 버전 크롤러 및 보조 함수들
# -----------------------------------------------------------------------------
def close_notice_popups_sync(page):
    """
    G2B 사이트에서 나타나는 팝업 창을 닫는 동기 Playwright 버전 함수입니다.
    여러 종류의 팝업을 감지하여 닫고, "오늘 하루 보지 않기" 체크박스를 선택합니다.
    """
    try:
        for _ in range(5):
            popup_divs = page.query_selector_all("div[id^='mf_wfm_container_wq_uuid_'][class*='w2popup_window']")
            for popup in popup_divs:
                try:
                    # 닫기 버튼 찾기
                    for sel in ["button[class*='w2window_close']", "input[type='button'][value='닫기']"]:
                        btn = popup.query_selector(sel)
                        if btn:
                            btn.click()
                            time.sleep(0.2)
                            break
                    # "오늘 하루 보지 않기" 체크박스
                    checkbox = popup.query_selector("input[type='checkbox'][title*='오늘 하루']")
                    if checkbox:
                        checkbox.check()
                        time.sleep(0.1)
                        btn = popup.query_selector("input[type='button'][value='닫기']")
                        if btn:
                            btn.click()
                            break
                except Exception:
                    continue
            time.sleep(0.5)
    except Exception as e:
        print(f"팝업 닫기 중 오류: {e}")

def wait_and_click_sync(page, selector: str, desc: str, timeout: int = 10000, scroll: bool = True) -> bool:
    """
    특정 셀렉터의 요소가 나타날 때까지 대기한 후 클릭하는 동기 함수입니다.
    """
    try:
        page.wait_for_selector(selector, timeout=timeout, state="visible")
        elem = page.query_selector(selector)
        if elem and elem.is_visible():
            if scroll:
                elem.scroll_into_view_if_needed()
                time.sleep(0.1)
            elem.click()
            return True
        return False
    except Exception as e:
        print(f"{desc} 클릭 실패: {e}")
        return False

def crawl_and_save_sync(search_term: str, progress_callback=None) -> str:
    """
    G2B 사이트를 동기 Playwright API로 크롤링하여 데이터를 수집하고 저장합니다.
    비동기 이벤트 루프 충돌을 피하기 위해 sync_playwright를 사용합니다.
    """
    result_msg = ""
    browser = None
    try:
        if progress_callback:
            progress_callback("브라우저 시작 중...")
        with sync_playwright() as p:
            # 브라우저 옵션 설정
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-extensions',
                    '--no-first-run',
                    '--disable-default-apps'
                ]
            )
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = context.new_page()

            if progress_callback:
                progress_callback("G2B 사이트 접속 중...")
            # 사이트 접속
            page.goto("https://shop.g2b.go.kr/", timeout=30000)
            try:
                page.wait_for_load_state('networkidle', timeout=10000)
            except Exception:
                pass
            time.sleep(3)
            if progress_callback:
                progress_callback("팝업 닫는 중...")
            # 팝업 닫기
            close_notice_popups_sync(page)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)
            if progress_callback:
                progress_callback("제안공고목록 페이지로 이동 중...")
            # 제안공고목록 버튼 클릭
            btn_selectors = [
                'a[id^="mf_wfm_container_wq_uuid_"][id$="_btnPrpblist"]',
                'a[title*="제안공고목록"]',
                'text=제안공고목록',
                'a:has-text("제안공고목록")',
                '//a[contains(text(), "제안공고목록")]'
            ]
            clicked = False
            for sel in btn_selectors:
                if wait_and_click_sync(page, sel, "제안공고목록 버튼"):
                    clicked = True
                    break
            if not clicked:
                # 지정한 셀렉터에서 찾지 못한 경우, 모든 <a> 태그를 순회하며 공고 메뉴를 찾습니다.
                all_links = page.query_selector_all("a")
                for a in all_links:
                    try:
                        title_attr = a.get_attribute("title")
                        href_attr = a.get_attribute("href")
                        inner_text = a.inner_text()
                        if ((title_attr and "제안공고" in title_attr) or (inner_text and "제안공고" in inner_text)):
                            # href가 정상적인 링크인지 확인 후 클릭
                            if href_attr and href_attr.strip() != "javascript:void(null)":
                                a.scroll_into_view_if_needed()
                                time.sleep(0.2)
                                a.click()
                                clicked = True
                                break
                    except Exception:
                        continue
                if not clicked:
                    raise Exception("제안공고목록 버튼을 찾을 수 없습니다.")
            time.sleep(2)
            if progress_callback:
                progress_callback("검색 조건 설정 중...")
            # 3개월 라디오 버튼 선택
            page.evaluate("""
                const radio = document.querySelector('input[title="3개월"]');
                if (radio) {
                    radio.checked = true;
                    const event = new Event('click', { bubbles: true });
                    radio.dispatchEvent(event);
                }
            """)
            time.sleep(1)
            # 검색어 입력
            input_elem = page.query_selector('td[data-title="제안공고명"] input[type="text"]')
            if input_elem:
                input_elem.fill(search_term)
            else:
                raise Exception("검색어 입력창을 찾을 수 없습니다.")
            # 페이지당 레코드 수를 100으로 설정
            page.evaluate("""
                const selects = document.querySelectorAll('select[id*="RecordCountPerPage"]');
                selects.forEach(select => {
                    select.value = "100";
                    const event = new Event('change', { bubbles: true });
                    select.dispatchEvent(event);
                });
            """)
            time.sleep(1)
            # 적용 버튼 클릭
            if not wait_and_click_sync(page, 'input[type="button"][value="적용"]', "적용버튼", scroll=False):
                print("적용 버튼을 찾을 수 없어 건너뜁니다.")
            if progress_callback:
                progress_callback("검색 실행 중...")
            # 검색 버튼 클릭
            if not wait_and_click_sync(page, 'input[type="button"][value="검색"]', "검색버튼", scroll=False):
                raise Exception("검색 버튼을 찾을 수 없습니다.")
            time.sleep(3)
            if progress_callback:
                progress_callback("데이터 수집 중...")
            # 테이블 데이터 추출
            table_elem = page.query_selector('table[id$="grdPrpsPbanc_body_table"]')
            if not table_elem:
                raise Exception("데이터 테이블을 찾을 수 없습니다.")
            rows = table_elem.query_selector_all('tr')
            data = []
            for row in rows:
                tds = row.query_selector_all('td')
                cols = []
                for td in tds:
                    try:
                        nobr = td.query_selector('nobr')
                        if nobr:
                            text = nobr.inner_text()
                        else:
                            a_tag = td.query_selector('a')
                            text = a_tag.inner_text() if a_tag else td.inner_text()
                        cols.append(text.strip())
                    except Exception:
                        cols.append("")
                if cols and any(col.strip() for col in cols):
                    data.append(cols)
            if not data:
                return "⚠️ 검색 결과가 없습니다."
            if progress_callback:
                progress_callback("데이터 저장 중...")
            # DataFrame 생성 및 병합
            new_df = pd.DataFrame(data)
            headers = ["No", "제안공고번호", "수요기관", "제안공고명", "공고게시일자", "공고마감일시", "공고상태", "사유", "기타"]
            new_df.columns = headers[:len(new_df.columns)]
            new_df.insert(0, "검색어", search_term)
            file_path = 'g2b_result.xlsx'
            if os.path.exists(file_path):
                try:
                    old_df = pd.read_excel(file_path)
                    combined_df = pd.concat([old_df, new_df], ignore_index=True)
                    combined_df.drop_duplicates(subset="제안공고번호", keep='last', inplace=True)
                    combined_df.reset_index(drop=True, inplace=True)
                except Exception:
                    combined_df = new_df
            else:
                combined_df = new_df
            combined_df.to_excel(file_path, index=False)
            # 엑셀 포맷팅
            try:
                wb = openpyxl.load_workbook(file_path)
                ws = wb.active
                align = Alignment(horizontal='center', vertical='center')
                for row in ws.iter_rows():
                    for cell in row:
                        cell.alignment = align
                col_widths = [15, 3.5, 17, 44, 55, 15, 17.5, 17, 17, 17]
                for i, width in enumerate(col_widths[:ws.max_column], start=1):
                    col_letter = openpyxl.utils.get_column_letter(i)
                    ws.column_dimensions[col_letter].width = width
                wb.save(file_path)
            except Exception as e:
                print(f"엑셀 포맷팅 중 오류: {e}")
            result_msg = f"✅ 크롤링 완료: `{search_term}` 검색어로 {len(data)}건의 데이터를 수집하여 저장했습니다."
    except Exception as e:
        result_msg = f"❌ 오류 발생: {str(e)}"
        print(f"크롤링 오류: {e}")
    finally:
        if browser:
            try:
                browser.close()
            except Exception:
                pass
    return result_msg

# 다운로드 버튼 생성 함수
def create_download_link(file_path):
    """파일 다운로드 링크를 생성합니다."""
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        
        # Streamlit의 download_button 사용
        st.download_button(
            label="📥 결과 엑셀 파일 다운로드",
            data=data,
            file_name=os.path.basename(file_path),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        return True
    except Exception as e:
        st.error(f"다운로드 링크 생성 실패: {e}")
        return False

# ----------------------
# Streamlit UI 시작
# ----------------------
def main():
    st.set_page_config(
        page_title="G2B 제안공고 크롤러", 
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    
    st.title("💻 G2B 제안공고 크롤러")
    st.markdown("국가를 당사자로 하는 계약에 관한 법률에 따른 공개 데이터를 수집합니다.")
    
    # Playwright 설치 확인
    if not install_playwright():
        st.error("브라우저 설치에 실패했습니다. 페이지를 새로고침해주세요.")
        st.stop()
    
    # 사용법 안내
    with st.expander("🔍 사용법 안내"):
        st.markdown("""
        1. 검색하고자 하는 키워드를 입력하세요 (예: 컴퓨터, 데스크톱, 모니터)
        2. '크롤링 시작' 버튼을 클릭하세요
        3. 검색이 완료되면 엑셀 파일을 다운로드할 수 있습니다
        4. 여러 번 검색하면 기존 데이터에 새 데이터가 추가됩니다
        
        ⚠️ **주의사항**: 처음 실행 시 브라우저 설치로 인해 시간이 걸릴 수 있습니다.
        """)
    
    # 검색어 입력
    search_term = st.text_input(
        "🔎 검색어를 입력하세요", 
        value="컴퓨터",
        help="예: 컴퓨터, 데스크톱, 모니터, 노트북, 소프트웨어 등",
        placeholder="검색할 키워드를 입력하세요"
    )
    
    # 크롤링 시작 버튼
    if st.button("🚀 크롤링 시작", type="primary"):
        if not search_term.strip():
            st.error("검색어를 입력해주세요.")
            return
        
        # 진행상황 표시
        progress_bar = st.progress(0)
        status_text = st.empty()

        # 진행 상황과 진행률을 업데이트하는 내부 함수
        def update_progress(message: str):
            """
            크롤링 단계별 메시지를 표시하고 대략적인 진행률을 업데이트합니다.
            message 내용에 따라 progress_bar를 적절히 증가시킵니다.
            """
            status_text.text(f"⏳ {message}")
            # 단계별 키워드에 따라 진행률 할당
            if "브라우저 시작" in message or "브라우저 준비" in message:
                progress_bar.progress(10)
            elif "접속" in message:
                progress_bar.progress(20)
            elif "팝업" in message:
                progress_bar.progress(30)
            elif "이동" in message:
                progress_bar.progress(40)
            elif "검색 조건" in message:
                progress_bar.progress(50)
            elif "검색 실행" in message:
                progress_bar.progress(60)
            elif "데이터 수집" in message:
                progress_bar.progress(80)
            elif "데이터 저장" in message:
                progress_bar.progress(90)

        # 크롤링 실행 (동기 버전 사용)
        try:
            # 동기 크롤러 실행. 비동기 이벤트 루프 충돌을 방지하기 위해 sync_playwright 기반 함수를 사용합니다.
            result = crawl_and_save_sync(search_term, update_progress)
            # 완료 후 진행률 100% 설정
            progress_bar.progress(100)
            status_text.empty()

            if "완료" in result:
                st.success(result)

                # 결과 파일이 존재하는지 확인
                if os.path.exists("g2b_result.xlsx"):
                    st.markdown("---")
                    st.subheader("📥 결과 다운로드")

                    # 파일 정보 표시
                    try:
                        df = pd.read_excel("g2b_result.xlsx")
                        st.info(f"총 {len(df)}건의 데이터가 저장되었습니다.")

                        # 미리보기
                        with st.expander("📋 데이터 미리보기 (최근 5건)"):
                            st.dataframe(df.head(), use_container_width=True)
                    except Exception as e:
                        st.warning(f"파일 정보를 읽는 중 오류: {e}")

                    # 다운로드 버튼
                    create_download_link("g2b_result.xlsx")
            else:
                # result에 "완료"가 포함되지 않으면 오류 메시지로 간주합니다.
                st.error(result)
        except Exception as e:
            # 예외 처리: 전역 오류 메시지를 사용자에게 표시합니다.
            st.error(f"예기치 못한 오류가 발생했습니다: {str(e)}")
        finally:
            # 진행률 컴포넌트 정리
            try:
                progress_bar.empty()
                status_text.empty()
            except Exception:
                # 이미 정리되었거나 존재하지 않으면 무시합니다.
                pass
    
    # 기존 파일이 있는 경우 다운로드 제공
    if os.path.exists("g2b_result.xlsx"):
        st.markdown("---")
        st.markdown("### 📁 기존 파일")
        try:
            df = pd.read_excel("g2b_result.xlsx")
            st.info(f"기존 저장된 데이터: {len(df)}건")
            create_download_link("g2b_result.xlsx")
        except Exception:
            pass

if __name__ == "__main__":
    main()
