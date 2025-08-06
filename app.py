import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.title("🏪 나라장터 제안공고 크롤러")

def simple_crawler(query):
    """
    간단한 샘플 데이터 크롤러
    (일단 앱이 실행되는지 확인용)
    """
    # 현재는 샘플 데이터를 반환
    # 나중에 실제 크롤링 로직으로 교체
    header = ["공고번호", "공고명", "공고기관", "게시일", "마감일"]
    table_data = [
        ["2024-001", f"{query} 관련 시스템 구축", "과학기술정보통신부", "2024-01-01", "2024-01-31"],
        ["2024-002", f"{query} 장비 구매", "서울특별시", "2024-01-05", "2024-02-05"],
        ["2024-003", f"스마트 {query} 도입 사업", "부산광역시", "2024-01-10", "2024-02-10"],
        ["2024-004", f"{query} 보안 솔루션", "대구광역시", "2024-01-15", "2024-02-15"],
        ["2024-005", f"{query} 관련 컨설팅", "인천광역시", "2024-01-20", "2024-02-20"]
    ]
    return header, table_data

# 검색어 입력
search_query = st.text_input("🔍 검색어를 입력하세요", value="컴퓨터")

# 실행 버튼
if st.button("🚀 크롤링 실행"):
    if search_query.strip():
        
        with st.spinner("크롤링 중..."):
            # 크롤링 실행
            result = simple_crawler(search_query.strip())
            
            if result:
                header, table_data = result
                
                # 데이터프레임 생성
                df = pd.DataFrame(table_data, columns=header)
                
                # 결과 표시
                st.success(f"✅ {len(df)}개의 공고를 찾았습니다!")
                
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
            else:
                st.error("❌ 크롤링 실패")
    else:
        st.warning("⚠️ 검색어를 입력해주세요!")

st.markdown("---")
st.markdown("**참고**: 현재는 샘플 데이터를 표시합니다. 실제 크롤링은 추후 구현 예정입니다.")
