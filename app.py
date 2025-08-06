import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import re

st.set_page_config(
    page_title="나라장터 제안공고 크롤러",
    page_icon="🏪",
    layout="wide"
)

st.title("🏪 나라장터 제안공고 크롤러")

def real_g2b_crawler(query):
    """
    실제 G2B 사이트 크롤링 시도
    """
    try:
        session = requests.Session()
        
        # User-Agent 설정
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        session.headers.update(headers)
        
        st.write(f"🔍 '{query}' 검색 중...")
        
        # G2B 메인 페이지 접속
        main_url = "https://shop.g2b.go.kr/"
        try:
            response = session.get(main_url, timeout=10)
            st.write(f"✅ G2B 메인 페이지 접속 성공 (상태코드: {response.status_code})")
        except Exception as e:
            st.write(f"❌ G2B 메인 페이지 접속 실패: {e}")
            return None
        
        # G2B 공고 검색 페이지들 시도
        search_urls = [
            "https://www.g2b.go.kr/index.jsp",
            "https://www.g2b.go.kr/pt/menu/selectSubFrame.do?framesrc=/pt/menu/frameTgong.do",
            "https://www.g2b.go.kr/koneps/user/lgnx/notic/bidguidance/BidGuidanceSearchForm.do"
        ]
        
        for url in search_urls:
            try:
                st.write(f"🌐 시도 중: {url}")
                response = session.get(url, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 검색 폼 찾기
                    search_forms = soup.find_all('form')
                    for form in search_forms:
                        inputs = form.find_all('input')
                        for inp in inputs:
                            if inp.get('name') and ('search' in inp.get('name', '').lower() or 'keyword' in inp.get('name', '').lower()):
                                st.write(f"🔍 검색 폼 발견: {inp.get('name')}")
                
            except Exception as e:
                st.write(f"❌ {url} 접속 실패: {e}")
                continue
        
        # 대안: 나라장터 쇼핑몰 제안공고 직접 접근 시도
        shop_urls = [
            "https://shop.g2b.go.kr/shop/notice.do",
            "https://shop.g2b.go.kr/shop/proposal.do",
            "https://shop.g2b.go.kr/proposal/proposalList.do"
        ]
        
        for url in shop_urls:
            try:
                st.write(f"🛒 나라장터 쇼핑몰 시도: {url}")
                response = session.get(url, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # 테이블 찾기
                    tables = soup.find_all('table')
                    for table in tables:
                        rows = table.find_all('tr')
                        if len(rows) > 1:  # 헤더 + 데이터 행이 있는 경우
                            st.write(f"📊 테이블 발견: {len(rows)}개 행")
                            
                            # 헤더 추출
                            header_row = rows[0]
                            header = [th.get_text().strip() for th in header_row.find_all(['th', 'td'])]
                            
                            # 데이터 추출
                            data_rows = []
                            for row in rows[1:]:
                                cols = row.find_all(['td', 'th'])
                                row_data = [col.get_text().strip() for col in cols]
                                if row_data and any(cell.strip() for cell in row_data):
                                    # 검색어가 포함된 행만 필터링
                                    if query.lower() in ' '.join(row_data).lower():
                                        data_rows.append(row_data)
                            
                            if data_rows:
                                st.write(f"✅ '{query}' 관련 데이터 {len(data_rows)}개 발견!")
                                return header, data_rows
                
            except Exception as e:
                st.write(f"❌ {url} 처리 실패: {e}")
                continue
        
        st.write("⚠️ 실제 데이터를 찾을 수 없어 샘플 데이터를 반환합니다.")
        return None
        
    except Exception as e:
        st.write(f"❌ 크롤링 중 오류: {e}")
        return None

def get_sample_data(query):
    """샘플 데이터 생성"""
    header = ["공고번호", "공고명", "공고기관", "게시일", "마감일"]
    table_data = [
        ["2024-001", f"{query} 관련 시스템 구축", "과학기술정보통신부", "2024-01-01", "2024-01-31"],
        ["2024-002", f"{query} 장비 구매", "서울특별시", "2024-01-05", "2024-02-05"],
        ["2024-003", f"스마트 {query} 도입 사업", "부산광역시", "2024-01-10", "2024-02-10"],
        ["2024-004", f"{query} 보안 솔루션", "대구광역시", "2024-01-15", "2024-02-15"],
        ["2024-005", f"{query} 관련 컨설팅", "인천광역시", "2024-01-20", "2024-02-20"]
    ]
    return header, table_data

# 사이드바
with st.sidebar:
    st.header("ℹ️ 크롤링 방식")
    crawler_mode = st.selectbox(
        "크롤링 방식 선택:",
        ["실제 크롤링 시도", "샘플 데이터만"]
    )
    
    st.markdown("""
    **실제 크롤링 시도:**
    - G2B 사이트에 실제 접근
    - 네트워크 상황에 따라 결과 상이
    - 시간이 오래 걸릴 수 있음
    
    **샘플 데이터만:**
    - 빠른 테스트용
    - 일관된 결과 보장
    """)

# 메인 인터페이스
col1, col2 = st.columns([3, 1])

with col1:
    search_query = st.text_input("🔍 검색어를 입력하세요", value="컴퓨터")

with col2:
    st.write("")
    run_btn = st.button("🚀 크롤링 실행", type="primary")

# 크롤링 실행
if run_btn and search_query.strip():
    
    progress_bar = st.progress(0)
    status_container = st.container()
    
    with status_container:
        st.write("🔄 크롤링을 시작합니다...")
        progress_bar.progress(20)
        
        if crawler_mode == "실제 크롤링 시도":
            with st.expander("🔍 크롤링 진행 상황", expanded=True):
                result = real_g2b_crawler(search_query.strip())
            progress_bar.progress(80)
        else:
            st.write("📦 샘플 데이터를 생성합니다...")
            result = get_sample_data(search_query.strip())
            progress_bar.progress(80)
        
        # 실제 크롤링 실패 시 샘플 데이터로 대체
        if not result and crawler_mode == "실제 크롤링 시도":
            st.write("🔄 샘플 데이터로 대체합니다...")
            result = get_sample_data(search_query.strip())
        
        progress_bar.progress(90)
        
        if result:
            header, table_data = result
            
            # 데이터프레임 생성
            df = pd.DataFrame(table_data, columns=header)
            progress_bar.progress(100)
            
            # 결과 표시
            st.success(f"✅ {len(df)}개의 공고를 찾았습니다!")
            
            # 통계
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📈 총 공고 수", len(df))
            with col2:
                st.metric("📊 컬럼 수", len(df.columns))
            with col3:
                st.metric("🔍 검색어", f'"{search_query}"')
            
            # 데이터 표시
            st.dataframe(df, use_container_width=True)
            
            # CSV 다운로드
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                "📥 CSV 다운로드",
                data=csv,
                file_name=f"g2b_{search_query}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
            # 사용된 방식 표시
            if crawler_mode == "실제 크롤링 시도":
                st.info("🌐 실제 크롤링을 시도했습니다.")
            else:
                st.info("📦 샘플 데이터가 표시되었습니다.")
        else:
            st.error("❌ 크롤링에 실패했습니다.")
            progress_bar.progress(100)

elif run_btn and not search_query.strip():
    st.warning("⚠️ 검색어를 입력해주세요!")

# 푸터
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
    <small>🏪 나라장터 제안공고 크롤러 | Made with ❤️ using Streamlit</small>
    </div>
    """, 
    unsafe_allow_html=True
)
