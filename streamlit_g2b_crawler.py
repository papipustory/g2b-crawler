import streamlit as st
import asyncio
import pandas as pd
import openpyxl
from openpyxl.styles import Alignment
import os
import sys
import time
from playwright.async_api import async_playwright
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="💻 나라장터 제안공고 크롤러", layout="centered")
st.title("💻 나라장터 제안공고 크롤러")
st.markdown("컴퓨터 관련 제안공고를 G2B에서 크롤링하여 다운로드합니다.")

progress_text = st.empty()
progress_bar = st.progress(0)

def update_progress(step: int, total_steps: int, message: str):
    ratio = step / total_steps
    progress_bar.progress(ratio)
    progress_text.info(f"{message} ({step}/{total_steps})")

async def close_notice_popups(page):
    """팝업창을 안전하게 닫는 함수"""
    try:
        await asyncio.sleep(2)  # 페이지 로딩 대기
        
        # 여러 선택자 시도
        popup_selectors = [
            "div[id^='mf_wfm_container_wq_uuid_'][class*='w2popup_window']",
            "div.w2popup_window",
            "div[class*='popup']",
            "div[class*='notice']"
        ]
        
        for selector in popup_selectors:
            try:
                popups = await page.query_selector_all(selector)
                logger.info(f"Found {len(popups)} popups with selector: {selector}")
                
                for popup in popups:
                    # 팝업이 표시되어 있는지 확인
                    is_visible = await popup.is_visible()
                    if not is_visible:
                        continue
                    
                    # 닫기 버튼 찾기 - 여러 선택자 시도
                    close_selectors = [
                        "button[class*='w2window_close']",
                        "button[class*='close']",
                        "button[title*='닫기']",
                        "a[class*='close']",
                        "span[class*='close']"
                    ]
                    
                    for close_selector in close_selectors:
                        try:
                            close_btn = await popup.query_selector(close_selector)
                            if close_btn and await close_btn.is_visible():
                                await close_btn.click()
                                logger.info(f"Closed popup with selector: {close_selector}")
                                await asyncio.sleep(1)
                                break
                        except:
                            continue
            except Exception as e:
                logger.warning(f"Error handling popup with selector {selector}: {str(e)}")
                continue
        
        # JavaScript로 직접 팝업 닫기 시도
        await page.evaluate("""
            // 모든 팝업 관련 요소 찾기
            const popupElements = document.querySelectorAll('[class*="popup"], [class*="notice"], [class*="modal"]');
            popupElements.forEach(el => {
                if (el.style.display !== 'none') {
                    el.style.display = 'none';
                }
            });
            
            // 오버레이 제거
            const overlays = document.querySelectorAll('[class*="overlay"], [class*="backdrop"]');
            overlays.forEach(el => el.remove());
        """)
        
    except Exception as e:
        logger.error(f"Error in close_notice_popups: {str(e)}")

async def run_crawler():
    step = 0
    total_steps = 10
    
    try:
        update_progress(step, total_steps, "Playwright 브라우저 실행 중...")
        
        async with async_playwright() as p:
            # 브라우저 옵션 설정
            browser_args = [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--disable-gpu'
            ]
            
            browser = await p.chromium.launch(
                headless=True,
                args=browser_args
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            
            page = await context.new_page()
            
            # 타임아웃 설정
            page.set_default_timeout(30000)  # 30초
            
            step += 1
            update_progress(step, total_steps, "1️⃣ 사이트 접속 중...")
            
            try:
                await page.goto("https://shop.g2b.go.kr/", wait_until="networkidle")
            except:
                # networkidle 실패시 domcontentloaded로 재시도
                await page.goto("https://shop.g2b.go.kr/", wait_until="domcontentloaded")
            
            await asyncio.sleep(3)
            
            step += 1
            update_progress(step, total_steps, "2️⃣ 팝업창 닫는 중...")
            await close_notice_popups(page)
            
            step += 1
            update_progress(step, total_steps, "3️⃣ 페이지 하단으로 스크롤...")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(2)
            
            step += 1
            update_progress(step, total_steps, "4️⃣ 제안공고목록 버튼 클릭...")
            
            # 여러 방법으로 버튼 찾기 시도
            clicked = False
            
            # 방법 1: 텍스트로 찾기
            try:
                button = await page.get_by_text("제안공고목록", exact=False).first
                if button:
                    await button.click()
                    clicked = True
            except:
                pass
            
            # 방법 2: JavaScript로 클릭
            if not clicked:
                await page.evaluate("""
                    const elements = Array.from(document.querySelectorAll('a, button, input[type="button"]'));
                    const button = elements.find(el => el.textContent && el.textContent.includes('제안공고목록'));
                    if (button) button.click();
                """)
            
            await asyncio.sleep(3)
            
            step += 1
            update_progress(step, total_steps, "5️⃣ 3개월 라디오 선택 중...")
            
            try:
                # 라디오 버튼 찾기 및 클릭
                radio = await page.query_selector('input[title="3개월"]')
                if not radio:
                    radio = await page.query_selector('input[value="3개월"]')
                if radio:
                    await radio.click()
                else:
                    # JavaScript로 시도
                    await page.evaluate("""
                        const radios = document.querySelectorAll('input[type="radio"]');
                        radios.forEach(radio => {
                            if (radio.title === '3개월' || radio.value === '3개월') {
                                radio.checked = true;
                                radio.click();
                            }
                        });
                    """)
            except Exception as e:
                logger.warning(f"3개월 라디오 선택 실패: {str(e)}")
            
            await asyncio.sleep(1.5)
            
            step += 1
            update_progress(step, total_steps, "6️⃣ 검색어 입력 중...")
            
            # 검색 입력창 찾기
            search_selectors = [
                'td[data-title="제안공고명"] input[type="text"]',
                'input[placeholder*="공고명"]',
                'input[name*="공고명"]',
                'input[id*="공고명"]'
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = await page.query_selector(selector)
                    if search_input:
                        break
                except:
                    continue
            
            if search_input:
                await search_input.fill('컴퓨터')
            else:
                # 모든 텍스트 입력창 찾아서 시도
                await page.evaluate("""
                    const inputs = document.querySelectorAll('input[type="text"]');
                    inputs.forEach(input => {
                        const td = input.closest('td');
                        if (td && td.getAttribute('data-title') === '제안공고명') {
                            input.value = '컴퓨터';
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                    });
                """)
            
            await asyncio.sleep(1)
            
            step += 1
            update_progress(step, total_steps, "7️⃣ 표시수 변경 중...")
            
            await page.evaluate("""
                const selects = document.querySelectorAll('select');
                selects.forEach(select => {
                    if (select.id && select.id.includes('RecordCountPerPage')) {
                        select.value = "100";
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                });
            """)
            await asyncio.sleep(1)
            
            step += 1
            update_progress(step, total_steps, "8️⃣ 검색 실행 중...")
            
            # 적용 버튼 클릭
            try:
                apply_btn = await page.query_selector('input[type="button"][value="적용"]')
                if apply_btn:
                    await apply_btn.click()
                    await asyncio.sleep(1)
            except:
                pass
            
            # 검색 버튼 클릭
            search_btn = await page.query_selector('input[type="button"][value="검색"]')
            if search_btn:
                await search_btn.click()
            else:
                await page.evaluate("""
                    const buttons = document.querySelectorAll('input[type="button"], button');
                    buttons.forEach(btn => {
                        if (btn.value === '검색' || btn.textContent === '검색') {
                            btn.click();
                        }
                    });
                """)
            
            await asyncio.sleep(3)
            
            step += 1
            update_progress(step, total_steps, "9️⃣ 데이터 수집 중...")
            
            # 테이블 데이터 수집
            table_selectors = [
                'table[id$="grdPrpsPbanc_body_table"]',
                'table[class*="grid"]',
                'table[class*="list"]',
                'table tbody'
            ]
            
            data = []
            table = None
            
            for selector in table_selectors:
                try:
                    table = await page.query_selector(selector)
                    if table:
                        break
                except:
                    continue
            
            if table:
                rows = await table.query_selector_all("tr")
                for row in rows:
                    cols = await row.query_selector_all("td")
                    row_data = []
                    for col in cols:
                        text = await col.inner_text()
                        row_data.append(text.strip())
                    if row_data and len(row_data) > 1:  # 빈 행 제외
                        data.append(row_data)
            
            # 데이터 저장
            if data:
                df = pd.DataFrame(data)
                if not df.empty:
                    # 컬럼명 설정
                    expected_cols = ["No", "제안공고번호", "수요기관", "제안공고명", "공고게시일자", "공고마감일시", "공고상태", "사유", "기타"]
                    if len(df.columns) == len(expected_cols):
                        df.columns = expected_cols
                    
                    # Excel 저장
                    df.to_excel("g2b_result.xlsx", index=False)
                    
                    # Excel 서식 설정
                    wb = openpyxl.load_workbook("g2b_result.xlsx")
                    ws = wb.active
                    
                    # 정렬 설정
                    align = Alignment(horizontal="center", vertical="center")
                    for row in ws.iter_rows():
                        for cell in row:
                            cell.alignment = align
                    
                    # 열 너비 자동 조정
                    for column in ws.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)
                        ws.column_dimensions[column_letter].width = adjusted_width
                    
                    wb.save("g2b_result.xlsx")
                    
                    st.success(f"✅ 총 {len(data)}개의 공고를 수집했습니다!")
            else:
                st.warning("⚠️ 수집된 데이터가 없습니다.")
            
            step += 1
            update_progress(step, total_steps, "✅ 크롤링 완료!")
            
            await browser.close()
            
    except Exception as e:
        logger.error(f"크롤링 중 오류 발생: {str(e)}")
        st.error(f"❌ 크롤링 중 오류 발생: {str(e)}")
        raise

# Streamlit 실행 부분
if st.button("🧲 크롤링 시작"):
    st.toast("크롤링을 시작합니다. 약 1~2분 정도 소요됩니다.", icon="🕒")
    
    try:
        # asyncio 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_crawler())
        
        # 결과 파일 다운로드 버튼
        if os.path.exists("g2b_result.xlsx"):
            with open("g2b_result.xlsx", "rb") as file:
                st.download_button(
                    label="📥 결과 파일 다운로드",
                    data=file,
                    file_name="g2b_result.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    except Exception as e:
        st.error(f"❌ 실행 중 오류: {str(e)}")
        logger.error(f"실행 오류: {str(e)}", exc_info=True)
