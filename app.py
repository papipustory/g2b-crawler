import streamlit as st
import pandas as pd
from g2b_crawler import run_g2b_crawler
import io

st.set_page_config(page_title="나라장터 크롤러", layout="wide")

st.title("🏛️ 나라장터 제안공고 크롤러")
st.markdown("---")

# 검색어 입력
col1, col2 = st.columns([3, 1])
with col1:
    search_query = st.text_input("검색어를 입력하세요", value="컴퓨터")
with col2:
    st.write("")
    st.write("")
    run_btn = st.button("🔍 크롤링 시작", type="primary")

if run_btn:
    with st.spinner(f"'{search_query}' 검색 중... (30초~1분 소요)"):
        result = run_g2b_crawler(search_query)
    
    if result:
        header, table_data = result
        
        # DataFrame 생성
        df = pd.DataFrame(table_data, columns=header)
        
        st.success(f"✅ {len(df)}개의 공고를 찾았습니다!")
        
        # 데이터 표시
        st.dataframe(df, use_container_width=True)
        
        # Excel 다운로드 (메모리에서 직접 생성)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='공고목록')
            
            # 엑셀 스타일링
            worksheet = writer.sheets['공고목록']
            
            # 열 너비 설정
            col_widths = {
                'A': 5,   # No
                'B': 17,  # 제안공고번호
                'C': 30,  # 수요기관
                'D': 50,  # 제안공고명
                'E': 15,  # 공고게시일자
                'F': 17,  # 공고마감일시
                'G': 12,  # 공고상태
                'H': 15,  # 사유
                'I': 15   # 기타
            }
            
            for col, width in col_widths.items():
                if col <= chr(ord('A') + len(header) - 1):
                    worksheet.column_dimensions[col].width = width
        
        excel_data = output.getvalue()
        
        # 다운로드 버튼
        st.download_button(
            label="📥 Excel 파일 다운로드",
            data=excel_data,
            file_name=f"g2b_{search_query}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        # CSV 다운로드도 제공
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 CSV 파일 다운로드",
            data=csv,
            file_name=f"g2b_{search_query}.csv",
            mime="text/csv"
        )
    else:
        st.error("❌ 크롤링 실패 또는 검색 결과가 없습니다.")
        st.info("💡 다시 시도하거나 다른 검색어를 사용해보세요.")
