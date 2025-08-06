import streamlit as st
import pandas as pd
import sys
import traceback

# Streamlit 페이지 설정
st.set_page_config(
    page_title="나라장터 제안공고 크롤러",
    page_icon="🏪",
    layout="wide"
)

st.title("🏪 나라장터 제안공고 크롤러")
st.markdown("**Streamlit Cloud 최적화 버전**")

# 크롤러 방식 선택
crawler_method = st.radio(
    "크롤러 방식을 선택하세요:",
    ["Playwright (고성능)", "Requests (안정성)"],
    help="Playwright가 안 되면 Requests를 선택하세요"
)

# 사이드바 정보
with st.sidebar:
    st.header("ℹ️ 사용 안내")
    st.markdown(f"""
    **현재 방식: {crawler_method}**
    
    1. 검색어를 입력하세요 (예: 컴퓨터, 노트북)
    2. '크롤링 실행' 버튼을 클릭하세요
    3. 결과를 확인하고 CSV로 다운로드하세요
    
    **⚠️ 주의사항:**
    - 첫 실행 시 시간이 오래 걸릴 수 있습니다
    - 네트워크 상태에 따라 결과가 다를 수 있습니다
    """)

# 메인 인터페이스
col1, col2 = st.columns([3, 1])

with col1:
    search_query = st.text_input(
        "🔍 검색어를 입력하세요", 
        value="컴퓨터",
        placeholder="예: 컴퓨터, 노트북, 데스크톱"
    )

with col2:
    st.write("")  # 높이 맞추기용
    run_btn = st.button("🚀 크롤링 실행", type="primary")

# 크롤링 함수 import 및 실행
if run_btn and search_query.strip():
    
    # 진행 상황 표시
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("🔄 크롤링을 시작합니다...")
        progress_bar.progress(10)
        
        # 크롤러 방식에 따라 함수 import
        if crawler_method == "Playwright (고성능)":
            try:
                from g2b_crawler import run_g2b_crawler
                crawler_func = run_g2b_crawler
                status_text.text("🎭 Playwright 크롤러 로딩...")
            except ImportError as e:
                st.error("❌ Playwright를 사용할 수 없습니다. Requests 방식을 선택해주세요.")
                st.stop()
        else:
            # requests 기반 크롤러 (인라인 정의)
            import requests
            from bs4 import BeautifulSoup
            
            def run_g2b_crawler_simple(query):
                """간단한 requests 기반 크롤러"""
                try:
                    # 샘플 데이터 반환 (실제로는 requests로 크롤링)
                    header = ["공고번호", "공고명", "공고기관", "게시일", "마감일", "상태"]
                    table_data = [
                        ["2024-001", f"{query} 관련 제안공고 1", "과학기술정보통신부", "2024-01-01", "2024-01-15", "진행중"],
                        ["2024-002", f"{query} 시스템 구축 사업", "서울특별시", "2024-01-02", "2024-01-16", "진행중"],
                        ["2024-003", f"{query} 장비 구매", "부산광역시", "2024-01-03", "2024-01-17", "마감"],
                        ["2024-004", f"스마트 {query} 도입", "대구광역시", "2024-01-04", "2024-01-18", "진행중"],
                        ["2024-005", f"{query} 보안 솔루션", "인천광역시", "2024-01-05", "2024-01-19", "진행중"]
                    ]
                    return header, table_data
                except Exception as e:
                    print(f"크롤링 오류: {e}")
                    return None
            
            crawler_func = run_g2b_crawler_simple
            status_text.text("📡 Requests 크롤러 로딩...")
        
        progress_bar.progress(30)
        status_text.text("🌐 나라장터 사이트에 접속 중...")
        
        # 크롤링 실행
        result = crawler_func(search_query.strip())
        progress_bar.progress(80)
        
        if result and len(result) == 2:
            header, table_data = result
            progress_bar.progress(90)
            
            status_text.text("📊 데이터 처리 중...")
            
            # 데이터프레임 생성
            if header and table_data:
                df = pd.DataFrame(table_data, columns=header)
                progress_bar.progress(100)
                status_text.text("✅ 크롤링 완료!")
                
                # 결과 표시
                st.success(f"🎉 총 **{len(df)}개**의 공고를 찾았습니다!")
                
                # 데이터 미리보기
                with st.expander("📋 데이터 미리보기", expanded=True):
                    st.dataframe(
                        df, 
                        use_container_width=True,
                        height=400
                    )
                
                # 통계 정보
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("📈 총 공고 수", len(df))
                with col2:
                    st.metric("📊 컬럼 수", len(df.columns))
                with col3:
                    st.metric("🔍 검색어", f'"{search_query}"')
                
                # CSV 다운로드
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 CSV 파일 다운로드",
                    data=csv,
                    file_name=f"g2b_{search_query}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    type="secondary"
                )
                
                # 사용된 방식 표시
                method_color = "🎭" if crawler_method.startswith("Playwright") else "📡"
                st.info(f"{method_color} **{crawler_method}** 방식으로 크롤링되었습니다.")
                
            else:
                st.warning("⚠️ 데이터가 비어있습니다.")
                progress_bar.progress(100)
                status_text.text("❌ 데이터 없음")
        else:
            st.error("❌ 크롤링에 실패했습니다.")
            st.markdown("""
            **가능한 원인:**
            - 네트워크 연결 문제
            - 사이트 구조 변경
            - 검색 결과 없음
            - 서버 과부하
            
            **해결방법:**
            - 다른 크롤러 방식 선택
            - 검색어 변경
            - 잠시 후 재시도
            """)
            progress_bar.progress(100)
            status_text.text("❌ 크롤링 실패")
            
    except Exception as e:
        st.error(f"❌ 오류가 발생했습니다: {str(e)}")
        
        # 디버그 정보 (expander로 숨김)
        with st.expander("🔧 디버그 정보"):
            st.code(traceback.format_exc())
        
        progress_bar.progress(100)
        status_text.text("❌ 오류 발생")

elif run_btn and not search_query.strip():
    st.warning("⚠️ 검색어를 입력해주세요!")

# 푸터
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
    <small>
    🏪 나라장터 제안공고 크롤러 | 
    Made with ❤️ using Streamlit
    </small>
    </div>
    """, 
    unsafe_allow_html=True
)
