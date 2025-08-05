import streamlit as st
import asyncio
import pandas as pd
import openpyxl
from openpyxl.styles import Alignment
import os
import sys
import subprocess
import logging
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="💻 나라장터 제안공고 크롤러", layout="centered")
st.title("💻 나라장터 제안공고 크롤러")

# Playwright 설치 확인 및 설치
@st.cache_resource
def install_playwright():
    """Playwright 브라우저 설치"""
    try:
        # pip로 playwright 설치
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright==1.40.0"], check=True)
        
        # 브라우저 설치 경로 설정
        os.environ['PLAYWRIGHT_BROWSERS_PATH'] = '0'
        
        # Chromium 브라우저 설치
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        subprocess.run([sys.executable, "-m", "playwright", "install-deps", "chromium"], check=True)
        
        return True
    except Exception as e:
        logger.error(f"Playwright 설치 실패: {str(e)}")
        return False

# 초기 설치
if 'playwright_installed' not in st.session_state:
    with st.spinner("Playwright 브라우저 설치 중... (처음 한 번만 실행됩니다)"):
        st.session_state.playwright_installed = install_playwright()

if not st.session_state.playwright_installed:
    st.error("Playwright 설치에 실패했습니다. 페이지를 새로고침해주세요.")
    st.stop()

progress_text = st.empty()
progress_bar = st.progress(0)

def update_progress(step: int, total_steps: int, message: str):
    progress_bar.progress(step / total_steps)
    progress_text.info(f"{message} ({step}/{total_steps})")

async def create_browser():
    """브라우저 생성 및 설정"""
    async with async_playwright() as p:
        # 브라우저 실행 옵션
        browser_args = [
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-web-security',
            '--disable-features=IsolateOrigins,site-per-process',
            '--disable-site-isolation-trials',
            '--no-zygote',
            '--single-process',
            '--disable-gpu'
        ]
        
        # Streamlit Cloud 환경 감지
        if os.environ.get('STREAMLIT_SHARING_MODE'):
            browser_args.extend([
                '--disable-accelerated-2d-canvas',
                '--disable-gpu-sandbox',
                '--disable-software-rasterizer'
            ])
        
        browser = await p.chromium.launch(
            headless=True,
            args=browser_args,
            timeout=60000
        )
        
        return browser

async def close_popups_advanced(page):
    """고급 팝업 닫기 로직"""
    try:
        # 1. iframe 내부의 팝업 확인
        frames = page.frames
        for frame in frames:
            try:
                await frame.evaluate("""
                    const closeButtons = document.querySelectorAll('[class*="close"], [class*="Close"], button[title*="닫"], button[title*="Close"]');
                    closeButtons.forEach(btn => btn.click());
                """)
            except:
                pass
        
        # 2. Shadow DOM 팝업 처리
        await page.evaluate("""
            function closeShadowPopups() {
                const allElements = document.querySelectorAll('*');
                allElements.forEach(el => {
                    if (el.shadowRoot) {
                        const shadowCloseButtons = el.shadowRoot.querySelectorAll('[class*="close"], [class*="Close"]');
                        shadowCloseButtons.forEach(btn => btn.click());
                    }
                });
            }
            closeShadowPopups();
        """)
        
        # 3. 동적으로 생성되는 팝업 대기 및 처리
        await page.wait_for_timeout(1000)
        
        # 4. 모든 모달/팝업 강제 숨김
        await page.evaluate("""
            // 팝업 관련 요소들 숨기기
            const popupSelectors = [
                '[class*="popup"]', '[class*="modal"]', '[class*="overlay"]',
                '[id*="popup"]', '[id*="modal"]', '[role="dialog"]',
                '.layer_popup', '.pop_wrap', '.popup_wrap'
            ];
            
            popupSelectors.forEach(selector => {
                document.querySelectorAll(selector).forEach(el => {
                    el.style.display = 'none';
                    el.style.visibility = 'hidden';
                });
            });
            
            // body 스크롤 활성화
            document.body.style.overflow = 'auto';
            document.documentElement.style.overflow = 'auto';
            
            // 배경 클릭 불가 해제
            const masks = document.querySelectorAll('.mask, .dimmed, .backdrop');
            masks.forEach(mask => mask.remove());
        """)
        
    except Exception as e:
        logger.warning(f"팝업 처리 중 경고: {str(e)}")

async def run_crawler():
    browser = None
    context = None
    page = None
    
    try:
        step = 0
        total_steps = 10
        update_progress(step, total_steps, "브라우저 실행 준비 중...")
        
        async with async_playwright() as p:
            # 브라우저 실행
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            
            # 컨텍스트 생성 (쿠키, 로컬 스토리지 등 설정)
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='ko-KR',
                timezone_id='Asia/Seoul'
            )
            
            # 페이지 생성
            page = await context.new_page()
            
            # JavaScript 활성화 확인
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)
            
            step += 1
            update_progress(step, total_steps, "1️⃣ G2B 사이트 접속 중...")
            
            # 페이지 로드 (여러 시도)
            try:
                await page.goto("https://shop.g2b.go.kr/", wait_until="domcontentloaded", timeout=30000)
            except PlaywrightTimeout:
                logger.warning("초기 로드 타임아웃, 재시도...")
                await page.goto("https://shop.g2b.go.kr/", wait_until="load", timeout=30000)
            
            # 페이지 로드 완료 대기
            await page.wait_for_load_state("networkidle", timeout=10000)
            await page.wait_for_timeout(3000)
            
            step += 1
            update_progress(step, total_steps, "2️⃣ 팝업 처리 중...")
            
            # 팝업 닫기 (여러 번 시도)
            for i in range(3):
                await close_popups_advanced(page)
                await page.wait_for_timeout(1000)
            
            step += 1
            update_progress(step, total_steps, "3️⃣ 메뉴 탐색 중...")
            
            # 스크롤 및 메뉴 찾기
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)
            await page.evaluate("window.scrollTo(0, 0)")
            
            step += 1
            update_progress(step, total_steps, "4️⃣ 제안공고목록 클릭...")
            
            # 제안공고목록 찾기 및 클릭
            proposal_clicked = False
            
            # 방법 1: 텍스트로 찾기
            try:
                proposal_link = await page.locator('text="제안공고목록"').first
                if await proposal_link.is_visible():
                    await proposal_link.click()
                    proposal_clicked = True
            except:
                pass
            
            # 방법 2: 부분 텍스트 매칭
            if not proposal_clicked:
                try:
                    links = await page.locator('a, button').all()
                    for link in links[:50]:  # 처음 50개만 확인
                        text = await link.text_content()
                        if text and "제안공고" in text:
                            await link.click()
                            proposal_clicked = True
                            break
                except:
                    pass
            
            # 방법 3: JavaScript 실행
            if not proposal_clicked:
                await page.evaluate("""
                    const elements = [...document.querySelectorAll('a, button, span, div')];
                    const target = elements.find(el => 
                        el.textContent && el.textContent.includes('제안공고목록')
                    );
                    if (target) target.click();
                """)
            
            await page.wait_for_timeout(3000)
            
            step += 1
            update_progress(step, total_steps, "5️⃣ 검색 조건 설정...")
            
            # 3개월 라디오 버튼 선택
            await page.evaluate("""
                const radios = document.querySelectorAll('input[type="radio"]');
                radios.forEach(radio => {
                    const label = radio.parentElement?.textContent || '';
                    if (label.includes('3개월') || radio.value === '3' || radio.title === '3개월') {
                        radio.checked = true;
                        radio.click();
                    }
                });
            """)
            
            step += 1
            update_progress(step, total_steps, "6️⃣ 검색어 입력...")
            
            # 검색어 입력
            search_completed = False
            
            # 방법 1: data-title로 찾기
            try:
                search_input = await page.locator('td[data-title="제안공고명"] input[type="text"]').first
                if await search_input.is_visible():
                    await search_input.fill("컴퓨터")
                    search_completed = True
            except:
                pass
            
            # 방법 2: 모든 input 확인
            if not search_completed:
                await page.evaluate("""
                    const inputs = document.querySelectorAll('input[type="text"]');
                    inputs.forEach(input => {
                        const parent = input.closest('td, div');
                        if (parent && parent.textContent.includes('공고명')) {
                            input.value = '컴퓨터';
                            input.dispatchEvent(new Event('input', {bubbles: true}));
                        }
                    });
                """)
            
            step += 1
            update_progress(step, total_steps, "7️⃣ 검색 옵션 설정...")
            
            # 100건 표시 설정
            await page.evaluate("""
                const selects = document.querySelectorAll('select');
                selects.forEach(select => {
                    if (select.innerHTML.includes('100')) {
                        select.value = '100';
                        select.dispatchEvent(new Event('change', {bubbles: true}));
                    }
                });
            """)
            
            step += 1
            update_progress(step, total_steps, "8️⃣ 검색 실행...")
            
            # 검색 버튼 클릭
            search_executed = False
            
            # 적용 버튼 먼저
            try:
                apply_btn = await page.locator('input[value="적용"]').first
                if await apply_btn.is_visible():
                    await apply_btn.click()
                    await page.wait_for_timeout(1000)
            except:
                pass
            
            # 검색 버튼
            try:
                search_btn = await page.locator('input[value="검색"]').first
                if await search_btn.is_visible():
                    await search_btn.click()
                    search_executed = True
            except:
                pass
            
            if not search_executed:
                await page.evaluate("""
                    const buttons = document.querySelectorAll('button, input[type="button"]');
                    buttons.forEach(btn => {
                        if (btn.textContent === '검색' || btn.value === '검색') {
                            btn.click();
                        }
                    });
                """)
            
            # 검색 결과 로드 대기
            await page.wait_for_timeout(5000)
            
            step += 1
            update_progress(step, total_steps, "9️⃣ 데이터 수집...")
            
            # 테이블 데이터 수집
            data = await page.evaluate("""
                function extractTableData() {
                    const data = [];
                    const tables = document.querySelectorAll('table');
                    
                    for (const table of tables) {
                        // 테이블 ID나 클래스로 확인
                        if (table.id.includes('grd') || table.className.includes('grid')) {
                            const rows = table.querySelectorAll('tbody tr');
                            
                            rows.forEach(row => {
                                const cells = row.querySelectorAll('td');
                                if (cells.length > 0) {
                                    const rowData = Array.from(cells).map(cell => 
                                        cell.textContent.trim()
                                    );
                                    if (rowData.some(cell => cell !== '')) {
                                        data.push(rowData);
                                    }
                                }
                            });
                            
                            if (data.length > 0) break;
                        }
                    }
                    
                    return data;
                }
                
                return extractTableData();
            """)
            
            step += 1
            update_progress(step, total_steps, "✅ 완료!")
            
            # 데이터 처리 및 저장
            if data and len(data) > 0:
                df = pd.DataFrame(data)
                
                # 컬럼명 설정
                columns = ["No", "제안공고번호", "수요기관", "제안공고명", "공고게시일자", "공고마감일시", "공고상태", "사유", "기타"]
                if len(df.columns) <= len(columns):
                    df.columns = columns[:len(df.columns)]
                
                # Excel 저장
                df.to_excel("g2b_result.xlsx", index=False)
                
                # 서식 적용
                wb = openpyxl.load_workbook("g2b_result.xlsx")
                ws = wb.active
                
                alignment = Alignment(horizontal="center", vertical="center")
                for row in ws.iter_rows():
                    for cell in row:
                        cell.alignment = alignment
                
                wb.save("g2b_result.xlsx")
                
                st.success(f"✅ 총 {len(data)}개의 공고를 수집했습니다!")
                return True
            else:
                st.warning("⚠️ 수집된 데이터가 없습니다.")
                return False
                
    except Exception as e:
        st.error(f"크롤링 중 오류 발생: {str(e)}")
        logger.exception("상세 오류:")
        return False
    finally:
        # 리소스 정리
        if page:
            await page.close()
        if context:
            await context.close()
        if browser:
            await browser.close()

# 메인 UI
st.markdown("""
### 사용 방법
1. 아래 버튼을 클릭하여 크롤링을 시작합니다
2. 자동으로 나라장터에 접속하여 컴퓨터 관련 제안공고를 검색합니다
3. 결과는 Excel 파일로 다운로드할 수 있습니다
""")

if st.button("🚀 크롤링 시작", type="primary", use_container_width=True):
    with st.spinner("크롤링 진행 중... (약 1-2분 소요)"):
        # asyncio 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        success = loop.run_until_complete(run_crawler())
        
        if success and os.path.exists("g2b_result.xlsx"):
            st.balloons()
            
            with open("g2b_result.xlsx", "rb") as file:
                st.download_button(
                    label="📥 결과 파일 다운로드 (Excel)",
                    data=file,
                    file_name="g2b_result.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

# 추가 정보
with st.expander("❓ 문제 해결 가이드"):
    st.markdown("""
    ### 자주 발생하는 문제와 해결 방법
    
    **1. 브라우저 실행 오류**
    - 페이지를 새로고침하여 다시 시도해주세요
    - 여전히 안 되면 잠시 후 다시 시도해주세요
    
    **2. 데이터 수집 실패**
    - 나라장터 사이트가 점검 중일 수 있습니다
    - 검색 결과가 없을 수 있습니다
    
    **3. 타임아웃 오류**
    - 네트워크 연결을 확인해주세요
    - 나라장터 서버가 느릴 수 있습니다
    """)

# 대안 제시
st.markdown("---")
st.markdown("### 🔄 대안: 수동 다운로드 후 처리")

uploaded_file = st.file_uploader(
    "나라장터에서 직접 다운로드한 Excel 파일을 업로드하세요",
    type=['xlsx', 'xls'],
    help="크롤링이 작동하지 않을 경우 사용하세요"
)

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success(f"✅ 파일 업로드 성공! (총 {len(df)}개 데이터)")
    st.dataframe(df.head(10))
