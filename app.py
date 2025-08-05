import streamlit as st
import pandas as pd
from g2b_crawler import run_g2b_crawler

st.title("나라장터 제안공고 크롤러 (Streamlit Cloud 최적화)")
search_query = st.text_input("검색어를 입력하세요", value="컴퓨터")
run_btn = st.button("크롤링 실행")

if run_btn:
    st.write("크롤링을 시작합니다...")
    result = run_g2b_crawler(search_query)
    if result:
        header, table_data = result
        df = pd.DataFrame(table_data, columns=header)
        st.dataframe(df)
        csv = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("CSV 다운로드", csv, file_name="g2b_result.csv", mime="text/csv")
    else:
        st.error("크롤링 실패 또는 데이터 없음")
