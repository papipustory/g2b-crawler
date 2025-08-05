import time
import pandas as pd
import os
import openpyxl
from openpyxl.styles import Alignment
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

def main():
    """Selenium을 사용한 크롤링"""
    print("[DEBUG] Selenium 크롤링 시작")
    
    # Chrome 옵션 설정
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = None
    try:
        # 드라이버 생성
        driver = webdriver.Chrome(options=chrome_options)
        wait = WebDriverWait(driver, 10)
        
        # 사이트 접속
        print("[DEBUG] 나라장터 접속")
        driver.get("https://shop.g2b.go.kr/")
        time.sleep(3)
        
        # 팝업 닫기
        try:
            popups = driver.find_elements(By.CSS_SELECTOR, "button.w2window_close")
            for popup in popups:
                if popup.is_displayed():
                    popup.click()
                    time.sleep(0.5)
        except:
            pass
        
        # 제안공고목록 클릭
        print("[DEBUG] 제안공고목록 검색")
        try:
            # 여러 선택자 시도
            selectors = [
                'a[title*="제안공고목록"]',
                'a:contains("제안공고목록")',
                '//a[contains(text(), "제안공고목록")]'
            ]
            
            clicked = False
            for selector in selectors:
                try:
                    if selector.startswith('//'):
                        elem = driver.find_element(By.XPATH, selector)
                    else:
                        elem = driver.find_element(By.CSS_SELECTOR, selector)
                    
                    driver.execute_script("arguments[0].scrollIntoView();", elem)
                    time.sleep(0.5)
                    elem.click()
                    clicked = True
                    break
                except:
                    continue
            
            if not clicked:
                print("[ERROR] 제안공고목록 버튼을 찾을 수 없습니다")
                return
                
        except Exception as e:
            print(f"[ERROR] 제안공고목록 클릭 실패: {e}")
            return
        
        time.sleep(3)
        
        # 조회 기간 3개월 설정
        try:
            driver.execute_script("""
                const radio = document.querySelector('input[title="3개월"]');
                if (radio) {
                    radio.checked = true;
                    radio.click();
                }
            """)
            time.sleep(1)
        except:
            pass
        
        # 검색어 입력
        try:
            search_input = driver.find_element(By.CSS_SELECTOR, 'td[data-title="제안공고명"] input[type="text"]')
            search_input.clear()
            search_input.send_keys("컴퓨터")
            time.sleep(1)
        except:
            print("[ERROR] 검색어 입력 실패")
        
        # 표시 건수 100건
        try:
            driver.execute_script("""
                const selects = document.querySelectorAll('select[id*="RecordCountPerPage"]');
                selects.forEach(select => {
                    select.value = "100";
                    select.dispatchEvent(new Event('change'));
                });
            """)
            time.sleep(1)
        except:
            pass
        
        # 적용 및 검색
        try:
            apply_btn = driver.find_element(By.CSS_SELECTOR, 'input[type="button"][value="적용"]')
            apply_btn.click()
            time.sleep(1)
            
            search_btn = driver.find_element(By.CSS_SELECTOR, 'input[type="button"][value="검색"]')
            search_btn.click()
            time.sleep(3)
        except:
            print("[ERROR] 검색 버튼 클릭 실패")
        
        # 데이터 수집
        print("[DEBUG] 데이터 수집 시작")
        try:
            table = driver.find_element(By.CSS_SELECTOR, 'table[id$="grdPrpsPbanc_body_table"]')
            rows = table.find_elements(By.TAG_NAME, 'tr')
            
            data = []
            for row in rows:
                cols = []
                cells = row.find_elements(By.TAG_NAME, 'td')
                for cell in cells:
                    text = cell.text.strip()
                    cols.append(text)
                
                if cols and any(cols):
                    data.append(cols)
            
            # 데이터 저장
            if data:
                save_to_excel(data)
                print(f"[DEBUG] {len(data)}개 항목 저장 완료")
            else:
                print("[WARNING] 수집된 데이터가 없습니다")
                
        except Exception as e:
            print(f"[ERROR] 데이터 수집 실패: {e}")
    
    except Exception as e:
        print(f"[ERROR] 크롤링 실패: {e}")
        import traceback
        print(traceback.format_exc())
    
    finally:
        if driver:
            driver.quit()
        print("[DEBUG] 크롤링 종료")

def save_to_excel(data):
    """엑셀 파일로 저장"""
    new_df = pd.DataFrame(data)
    headers = ["No", "제안공고번호", "수요기관", "제안공고명", "공고게시일자", "공고마감일시", "공고상태", "사유", "기타"]
    
    if len(new_df.columns) < len(headers):
        headers = headers[:len(new_df.columns)]
    elif len(new_df.columns) > len(headers):
        new_df = new_df.iloc[:, :len(headers)]
    
    new_df.columns = headers
    
    file_path = 'g2b_result.xlsx'
    
    # 기존 파일과 병합
    if os.path.exists(file_path):
        old_df = pd.read_excel(file_path)
        combined_df = pd.concat([old_df, new_df])
        combined_df.drop_duplicates(subset="제안공고번호", keep='last', inplace=True)
        combined_df.reset_index(drop=True, inplace=True)
    else:
        combined_df = new_df
    
    # 엑셀 저장
    combined_df.to_excel(file_path, index=False)
    
    # 서식 적용
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
