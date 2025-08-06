import streamlit as st
import pandas as pd
import sys
import subprocess
import logging
from g2b_crawler import run_g2b_crawler

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Streamlit 페이지 설정
st.set_page_config(
    page_title="나라장터 크롤러",
    page_icon="🏛️",
    layout="wide"
)

st.title("🏛️ 나라장터 제안공고 크롤러")
st.markdown("---")

# Playwright 설치 확인 및 자동 설치
@st.cache_resource
def check_and_install_playwright():
    """Playwright 브라우저 설치 확인 및 자동 설치"""
    try:
        # Playwright 브라우저 설치 확인
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            st.success("✅ Playwright 브라우저 설치 완료")
            return True
        else:
            st.error(f"❌ Playwright 설치 실패: {result.stderr}")
            return False
    except Exception as e:
        st.error(f"❌ Playwright 설치 중 오류: {str(e)}")
        return False

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 설정")
    
    # Playwright 상태 확인
    if st.button("🔄 Playwright 설치/확인"):
        with st.spinner("Playwright 설치 중..."):
            if check_and_install_playwright():
                st.success("설치 완료!")
            else:
                st.error("설치 실패. 수동 설치가 필요합니다.")
    
    st.markdown("---")
    st.markdown("""
    ### 📝 사용 방법
    1. 검색어를 입력하세요
    2. '크롤링 시작' 버튼을 클릭하세요
    3. 결과를 확인하고 CSV로 다운로드하세요
    
    ### ⚠️ 주의사항
    - 첫 실행 시 Playwright 설치가 필요합니다
    - 크롤링에 30초~1분 정도 소요될 수 있습니다
    """)

# 메인 콘텐츠
col1, col2 = st.columns([3, 1])

with col1:
    search_query = st.text_input(
        "🔍 검색어를 입력하세요",
        value="컴퓨터",
        placeholder="예: 컴퓨터, 노트북, 서버 등",
        help="나라장터에서 검색할 키워드를 입력하세요"
    )

with col2:
    st.write("")  # 간격 조정
    st.write("")  # 간격 조정
    run_btn = st.button("🚀 크롤링 시작", type="primary", use_container_width=True)

# 크롤링 실행
if run_btn:
    if not search_query.strip():
        st.error("❌ 검색어를 입력해주세요!")
    else:
        # 진행 상태 표시
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # 크롤링 시작
            status_text.text("🔄 크롤링을 시작합니다...")
            progress_bar.progress(20)
            
            status_text.text("🌐 나라장터 사이트에 접속 중...")
            progress_bar.progress(40)
            
            # 크롤링 실행
            with st.spinner(f"'{search_query}' 검색 중... (최대 1분 소요)"):
                result = run_g2b_crawler(search_query)
            
            progress_bar.progress(80)
            
            if result:
                header, table_data = result
                
                # 데이터프레임 생성
                df = pd.DataFrame(table_data, columns=header)
                
                # 검색어 열 추가
                df.insert(0, '검색어', search_query)
                
                progress_bar.progress(100)
                status_text.text("✅ 크롤링 완료!")
                
                # 결과 표시
                st.success(f"🎉 총 {len(df)}개의 공고를 찾았습니다!")
                
                # 데이터 미리보기
                st.subheader("📊 검색 결과")
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "번호": st.column_config.NumberColumn(width="small"),
                        "검색어": st.column_config.TextColumn(width="small"),
                    }
                )
                
                # CSV 다운로드 버튼
                csv = df.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    label="📥 CSV 파일 다운로드",
                    data=csv,
                    file_name=f"g2b_{search_query}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    type="primary"
                )
                
                # 통계 정보
                with st.expander("📈 통계 정보"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("총 공고 수", len(df))
                    with col2:
                        st.metric("검색어", search_query)
                    with col3:
                        st.metric("컬럼 수", len(df.columns))
                
            else:
                progress_bar.progress(100)
                status_text.text("")
                st.warning(f"⚠️ '{search_query}'에 대한 검색 결과가 없습니다.")
                st.info("💡 다른 검색어를 시도해보세요.")
                
        except Exception as e:
            progress_bar.progress(0)
            status_text.text("")
            st.error(f"❌ 크롤링 중 오류가 발생했습니다: {str(e)}")
            
            with st.expander("🔍 오류 상세 정보"):
                st.code(str(e))
                st.markdown("""
                **가능한 원인:**
                - Playwright가 제대로 설치되지 않음
                - 나라장터 사이트 구조 변경
                - 네트워크 연결 문제
                - Streamlit Cloud 리소스 제한
                
                **해결 방법:**
                1. 좌측 사이드바에서 'Playwright 설치/확인' 버튼 클릭
                2. 페이지 새로고침 후 재시도
                3. 다른 검색어로 시도
                """)

# 푸터
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <small>
    나라장터 제안공고 크롤러 v1.0 | 
    Made with ❤️ using Streamlit & Playwright
    </small>
</div>
""", unsafe_allow_html=True)
