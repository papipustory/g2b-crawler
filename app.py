import streamlit as st
import pandas as pd
import io
from contextlib import redirect_stdout
from g2b_crawler import run_g2b_crawler

st.title("🏛️ 나라장터 제안공고 크롤러")
st.markdown("---")

with st.sidebar:
    st.header("🔍 디버그 로그")
    debug_container = st.container()

search_query = st.text_input("검색어를 입력하세요", value="컴퓨터")

if st.button("🔍 크롤링 시작"):
    status_placeholder = st.empty()
    log_capture = io.StringIO()
    try:
        status_placeholder.info(f"'{search_query}' 검색 중... (최대 1분 소요)")

        with redirect_stdout(log_capture):
            result = run_g2b_crawler(search_query)

        log_output = log_capture.getvalue()
        with debug_container:
            st.code(log_output, language='text')

        if result and result[1]:  # (headers, data)
            header, table_data = result
            df = pd.DataFrame(table_data, columns=header)
            status_placeholder.success(f"✅ {len(df)}개의 공고를 찾았습니다!")
            st.dataframe(df, use_container_width=True)

            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "📥 CSV 다운로드",
                csv,
                file_name=f"g2b_{search_query}.csv",
                mime="text/csv"
            )
        else:
            status_placeholder.error("❌ 검색 결과가 없거나 크롤링 실패")
            st.info("💡 왼쪽 사이드바의 디버그 로그를 확인하세요")

    except Exception as e:
        status_placeholder.error(f"❌ 오류 발생: {str(e)}")
        log_output = log_capture.getvalue()
        with debug_container:
            st.code(log_output, language='text')
        with st.expander("오류 상세"):
            st.code(str(e))
