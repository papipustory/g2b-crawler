import streamlit as st
import asyncio
import pandas as pd
import openpyxl
from openpyxl.styles import Alignment
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
import traceback
import logging

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="나라장터 제안공고 크롤러", layout="centered")

st.title("💻 나라장터 제안공고 크롤링")

# 디버그 정보 표시
if st.checkbox("🔍 디버그 모드 활성화"):
    st.session_state.debug_mode = True
else:
    st.session_state.debug_mode = False

def debug_log(message):
    """디버그 로그 출력"""
    if st.session_state.get('debug_mode', False):
        st.write(f"🔍 DEBUG: {message}")
    print(f"DEBUG: {message}")

# Playwright 브라우저 설치 확인 및 설치
@st.cache_resource
def ensure_playwright_installed():
    try:
        import subprocess
        debug_log("Playwright 설치 확인 시작...")
        result = subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], 
                              capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            st.error(f"Playwright 설치 실패: {result.stderr}")
            debug_log(f"Playwright 설치 실패: {result.stderr}")
            return False
        debug_log("Playwright 설치 완료")
        return True
    except Exception as e:
        st.error(f"Playwright 설치 중 오류: {e}")
        debug_log(f"Playwright 설치 오류: {e}")
        return False

async def close_notice_popups(page):
    for loop_idx in range(5):
        popup_divs = await page.query_selector_all("div[id^='mf_wfm_container_wq_uuid_'][class*='w2popup_window']")
        print(f"[팝업 닫기] {loop_idx+1}회차, 발견된 팝업 수: {len(popup_divs)}")
        closed = False
        for idx, popup in enumerate(popup_divs):
            try:
                for sel in ["button[class*='w2window_close']", "input[type='button'][value='닫기']"]:
                    btn = await popup.query_selector(sel)
                    if btn:
                        print(f"[팝업 닫기] 팝업 {idx+1}: '{sel}' 버튼 클릭")
                        await btn.click()
                        await asyncio.sleep(0.3)
                        closed = True
                        break
                checkbox = await popup.query_selector("input[type='checkbox'][title*='오늘 하루']")
                if checkbox:
                    print(f"[팝업 닫기] 팝업 {idx+1}: '오늘 하루' 체크박스 클릭")
                    await checkbox.check()
                    await asyncio.sleep(0.2)
                    btn = await popup.query_selector("input[type='button'][value='닫기']")
                    if btn:
                        print(f"[팝업 닫기] 팝업 {idx+1}: '닫기' 버튼 클릭(체크박스 이후)")
                        await btn.click()
                        closed = True
                        break
            except Exception as e:
                print(f"[팝업 닫기] 팝업 {idx+1} 처리 중 에러: {e}")
                continue
        if not closed:
            print("[팝업 닫기] 더 이상 닫을 팝업이 없음, 종료")
            break
        await asyncio.sleep(0.5)

async def wait_and_click(page, selector, desc, timeout=3000, scroll=True):
    """원본 코드 기반의 안정적인 클릭 함수"""
    try:
        debug_log(f"클릭 시도: {desc} (셀렉터: {selector})")
        await page.wait_for_selector(selector, timeout=timeout, state="visible")
        elem = await page.query_selector(selector)
        if elem and await elem.is_visible():
            if scroll:
                await elem.scroll_into_view_if_needed()
                await asyncio.sleep(0.02)
            await elem.click()
            debug_log(f"클릭 성공: {desc}")
            return True
        debug_log(f"클릭 실패: {desc} - 요소가 보이지 않음")
        return False
    except Exception as e:
        debug_log(f"클릭 실패: {desc} - {str(e)}")
        return False

async def find_and_click_by_text(page, text, element_type="a"):
    """텍스트로 요소를 찾아서 클릭"""
    try:
        debug_log(f"텍스트 검색 시작: '{text}' ({element_type})")
        # 다양한 방법으로 텍스트 검색
        selectors = [
            f'{element_type}:has-text("{text}")',
            f'{element_type}[title*="{text}"]',
            f'{element_type}[alt*="{text}"]',
            f'//{element_type}[contains(text(), "{text}")]',
            f'//{element_type}[contains(@title, "{text}")]'
        ]
        
        for selector in selectors:
            try:
                debug_log(f"셀렉터 시도: {selector}")
                if selector.startswith('//'):
                    # XPath 사용
                    elements = await page.query_selector_all(f'xpath={selector}')
                else:
                    elements = await page.query_selector_all(selector)
                
                debug_log(f"찾은 요소 수: {len(elements)}")
                
                for i, element in enumerate(elements):
                    try:
                        await element.scroll_into_view_if_needed()
                        await asyncio.sleep(0.5)
                        await element.click()
                        debug_log(f"성공: '{text}' 텍스트로 클릭 (요소 {i+1})")
                        return True
                    except Exception as e:
                        debug_log(f"요소 {i+1} 클릭 실패: {e}")
                        continue
            except Exception as e:
                debug_log(f"셀렉터 실패 {selector}: {e}")
                continue
        
        debug_log(f"텍스트 검색 실패: '{text}'")
        return False
    except Exception as e:
        debug_log(f"텍스트 검색 오류: {e}")
        return False

async def main():
    """메인 크롤링 함수"""
    browser = None
    try:
        debug_log("크롤러 시작...")
        # Playwright 동적 import (설치 후)
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            debug_log("Playwright 컨텍스트 생성...")
            # Streamlit Cloud 환경에 최적화된 브라우저 설정
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            page = await context.new_page()
            
            debug_log("나라장터 페이지 접속...")
            # 타임아웃 증가 (3초 → 30초)
            await page.goto("https://shop.g2b.go.kr/", timeout=30000)
            # 로딩 상태 대기 타임아웃도 증가 (5초 → 30초)
            await page.wait_for_load_state('domcontentloaded', timeout=30000)
            await asyncio.sleep(3)

            await close_notice_popups(page)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(1)

            # 제안공고목록 버튼 찾기 - 원본 코드 방식
            debug_log("제안공고목록 버튼 검색 시작...")
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
                debug_log("셀렉터 기반 검색 실패, 모든 링크 검색 시도...")
                all_a = await page.query_selector_all("a")
                debug_log(f"페이지의 모든 링크 수: {len(all_a)}")
                for i, a in enumerate(all_a):
                    try:
                        title = await a.get_attribute("title")
                        href = await a.get_attribute("href")
                        inner = await a.inner_text()
                        debug_log(f"링크 {i+1}: title='{title}', text='{inner}', href='{href}'")
                        if (title and "제안공고" in title) or (inner and "제안공고" in inner):
                            if href and href.strip() != "javascript:void(null)":
                                await a.scroll_into_view_if_needed()
                                await asyncio.sleep(0.2)
                                await a.click()
                                clicked = True
                                debug_log(f"링크 {i+1} 클릭 성공")
                                break
                    except Exception as e:
                        debug_log(f"링크 {i+1} 처리 오류: {e}")
                        continue
            
            if not clicked:
                debug_log("모든 방법 실패: 제안공고목록 버튼을 찾을 수 없음")
                return {"error": "제안공고목록 버튼을 찾을 수 없습니다."}

            await asyncio.sleep(0.3)

            # 3개월 라디오 버튼 선택 - 원본 코드 방식
            debug_log("3개월 라디오 버튼 설정...")
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
            debug_log("검색어 입력...")
            input_elem = await page.query_selector('td[data-title="제안공고명"] input[type="text"]')
            if input_elem:
                await input_elem.fill('컴퓨터', timeout=1000)
                debug_log("검색어 입력 성공")

            # 페이지당 표시 개수 설정 - 원본 코드 방식
            debug_log("페이지당 표시 개수 설정...")
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
            debug_log("적용 버튼 클릭...")
            await wait_and_click(page, 'input[type="button"][value="적용"]', "적용버튼", scroll=False)
            
            debug_log("검색 버튼 클릭...")
            await wait_and_click(page, 'input[type="button"][value="검색"]', "검색버튼", scroll=False)
            await asyncio.sleep(0.8)

            # 테이블 데이터 추출
            debug_log("테이블 데이터 추출...")
            table_elem = await page.query_selector('table[id$="grdPrpsPbanc_body_table"]')
            if table_elem:
                debug_log("테이블 찾기 성공")
                rows = await table_elem.query_selector_all('tr')
                debug_log(f"테이블 행 수: {len(rows)}")
                data = []
                for i, row in enumerate(rows):
                    try:
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
                            debug_log(f"행 {i+1} 데이터: {cols[:3]}...")  # 처음 3개 컬럼만 로그
                    except Exception as e:
                        debug_log(f"행 {i+1} 처리 오류: {e}")
                        continue

                if data:
                    debug_log(f"총 {len(data)}개 행 데이터 수집 완료")
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
                            debug_log("기존 데이터와 병합 완료")
                        except Exception as e:
                            debug_log(f"기존 데이터 병합 오류: {e}")
                            combined_df = new_df
                    else:
                        combined_df = new_df

                    # Excel 파일 저장
                    combined_df.to_excel(file_path, index=False)
                    debug_log("Excel 파일 저장 완료")

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
                    debug_log("Excel 스타일링 완료")

                    return {"success": True, "data": combined_df, "file_path": file_path}
                else:
                    debug_log("수집된 데이터가 없음")
                    return {"error": "공고 목록을 찾을 수 없습니다."}
            else:
                debug_log("테이블을 찾을 수 없음")
                return {"error": "테이블을 찾을 수 없습니다."}

    except Exception as e:
        error_msg = f"크롤링 중 오류 발생: {str(e)}"
        debug_log(error_msg)
        debug_log(f"상세 오류: {traceback.format_exc()}")
        return {"error": error_msg}

    finally:
        if browser:
            try:
                await browser.close()
                debug_log("브라우저 종료 완료")
            except Exception as e:
                debug_log(f"브라우저 종료 오류: {e}")

def run_crawler():
    """별도 스레드에서 크롤러 실행"""
    # 새로운 이벤트 루프에서 실행
    def run_in_new_loop():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            debug_log("이벤트 루프 시작")
            return loop.run_until_complete(main())
        except Exception as e:
            error_msg = f"이벤트 루프 오류: {str(e)}"
            debug_log(error_msg)
            debug_log(f"이벤트 루프 상세 오류: {traceback.format_exc()}")
            return {"error": error_msg}
        finally:
            try:
                loop.close()
                debug_log("이벤트 루프 종료")
            except Exception as e:
                debug_log(f"이벤트 루프 종료 오류: {e}")
    
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
            progress_bar.progress(10)
            
            future = executor.submit(run_crawler)
            
            import time
            for i in range(11, 100):
                # 단계별 상태 표시
                if i == 15:
                    status_text.text("팝업창 닫는 중...")
                elif i == 25:
                    status_text.text("스크롤 하단으로 내리는 중...")
                elif i == 35:
                    status_text.text("제안공고목록 클릭 중...")
                elif i == 50:
                    status_text.text("3개월 라디오 버튼 선택 중...")
                elif i == 60:
                    status_text.text("검색어 입력 중...")
                elif i == 70:
                    status_text.text("페이지당 표시 개수 설정 중...")
                elif i == 80:
                    status_text.text("적용/검색 버튼 클릭 중...")
                elif i == 90:
                    status_text.text("테이블 데이터 추출 중...")
                elif i == 95:
                    status_text.text("결과 처리 중...")
                time.sleep(0.07)
                progress_bar.progress(i)
            
            result = future.result(timeout=180)  # 3분 타임아웃
            
            progress_bar.progress(100)
            status_text.text("완료!")
            
            if "error" in result:
                st.error(f"❌ {result['error']}")
                if st.session_state.get('debug_mode', False):
                    st.error("🔍 디버그 모드가 활성화되어 있습니다. 위의 로그를 확인하세요.")
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
            error_msg = f"❌ 실행 중 오류: {str(e)}"
            st.error(error_msg)
            debug_log(error_msg)
            debug_log(f"실행 오류 상세: {traceback.format_exc()}")
        finally:
            progress_bar.empty()
            status_text.empty()

# 디버그 정보 표시
if st.session_state.get('debug_mode', False):
    st.markdown("---")
    st.markdown("### 🔍 디버그 모드 활성화됨")
    st.info("위의 로그에서 각 단계별 진행 상황과 오류를 확인할 수 있습니다.")
