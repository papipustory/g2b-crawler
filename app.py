import streamlit as st
import pandas as pd
import sys
import traceback
from g2b_crawler import run_g2b_crawler

# Streamlit 페이지 설정
st.set_page_config(
    page_title="나라장터 제안공고 크롤러",
    page_icon="🏪",
    layout="wide"
)

st.title("🏪 나라장터 제안공고 크롤러")
st.markdown("**Streamlit Cloud 최적화 버전**")

# 사이드바 정보
with st.sidebar:
    st.header("ℹ️ 사용 안내")
    st.markdown("""
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

# 크롤링 실행
if run_btn and search_query.strip():
    
    # 진행 상황 표시
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text("🔄 크롤링을 시작합니다...")
        progress_bar.progress(10)
        
        status_text.text("🌐 나라장터 사이트에 접속 중...")
        progress_bar.progress(30)
        
        # 크롤링 실행
        result = run_g2b_crawler(search_query.strip())
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
                    if len(df) > 0:
                        st.metric("📅 검색어", f'"{search_query}"')
                
                # CSV 다운로드
                csv = df.to_csv(index=False, encoding='utf-8-sig')
                st.download_button(
                    label="📥 CSV 파일 다운로드",
                    data=csv,
                    file_name=f"g2b_{search_query}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    type="secondary"
                )
                
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
    Made with ❤️ using Streamlit & Playwright
    </small>
    </div>
    """, 
    unsafe_allow_html=True
)
