import streamlit as st
import pandas as pd
import altair as alt

# 1. 페이지 설정 및 아이콘 오류 방지 설정
st.set_page_config(page_title="GS25 수익 시뮬레이터", layout="centered")

# --- 비밀번호 인증 로직 ---
PW = "gs25" 

def check_password():
    if "password" not in st.session_state:
        st.session_state["password"] = ""
    if st.session_state["password"] == PW:
        return True

    st.title("🔒 인증이 필요합니다")
    pwd = st.text_input("임직원 전용 비밀번호", type="password")
    if st.button("접속하기"):
        if pwd == PW:
            st.session_state["password"] = pwd
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    return False

if check_password():
    # 2. CSS 수정 (화면 깨짐 방지 및 디자인 개선)
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
        * { font-family: 'Noto Sans KR', sans-serif !important; }
        
        /* 헤더 부분의 불필요한 아이콘 텍스트 숨기기 */
        .stExpander span { font-family: 'Noto Sans KR', sans-serif !important; }
        
        /* 메트릭 카드 디자인 */
        [data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #f0f0f0;
            padding: 12px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        
        /* 모바일 폰트 크기 최적화 */
        h1 { font-size: 1.8rem !important; padding-bottom: 0px; }
        .stCaption { font-size: 0.9rem !important; margin-bottom: 20px; }
        </style>
        """, unsafe_allow_html=True)

    # 3. 데이터 및 헤더
    type_info = {
        "GS1": {"support": 184.0, "royalty": 0.71},
        "GS2": {"support": 205.8, "royalty": 0.65},
        "GS3": {"support": 240.4, "royalty": 0.46}
    }

    st.title("📊 GS25 수익 시뮬레이터")
    st.caption("경영주 수익 개선을 위한 정밀 시뮬레이션")

    # 4. 입력 섹션 (Expander 아이콘 깨짐 방지를 위해 제목 단순화)
    with st.expander("⚙️ 정보 입력 및 목표 설정", expanded=True):
        st.subheader("📍 [1] 현재 현황")
        c_type = st.selectbox("현재 타입", ["GS1", "GS2", "GS3"], key="c_t")
        c_rent = 0
        if c_type == "GS2":
            c_rent = st.number_input("현재 월 임차료 (천원)", value=0, step=10)
        c_sales = st.number_input("현재 일매출 (천원)", value=1500, step=10)
        c_margin = st.slider("현재 매익률 (%)", 20.0, 45.0, 30.0, step=0.1)
        c_o4o = st.number_input("현재 O4O 매출 (천원)", value=0, step=10)

        st.divider()
        
        st.subheader("🚀 [2] 코칭 목표")
        t_type = st.selectbox("목표 타입", ["GS1", "GS2", "GS3"], index=(["GS1", "GS2", "GS3"].index(c_type)))
        t_rent = 0
        if t_type == "GS2":
            t_rent = st.number_input("목표 월 임차료 (천원)", value=0, step=10)
        t_sales = st.number_input("목표 일매출 (천원)", value=c_sales + 200, step=10)
        t_margin = st.slider("목표 매익률 (%)", 20.0, 45.0, c_margin + 1.5, step=0.1)
        t_o4o = st.number_input("목표 O4O 매출 (천원)", value=500, step=10)

    # 5. 계산 및 결과
    def calc(sales, margin, utype, o4o, rent=0):
        m_sales = sales * 30.41
        m_profit = m_sales * (margin / 100)
        royalty = m_profit * type_info[utype]["royalty"]
        support = type_info[utype]["support"]
        o4o_profit = o4o * 0.16
        return (royalty + support + o4o_profit) - rent

    cur_total = calc(c_sales, c_margin, c_type, c_o4o, c_rent)
    tar_total = calc(t_sales, t_margin, t_type, t_o4o, t_rent)
    diff = tar_total - cur_total

    st.subheader("💰 수익 분석 결과")
    m1, m2 = st.columns(2)
    m1.metric("기존 수익", f"{int(cur_total):,}원")
    m2.metric("목표 수익", f"{int(tar_total):,}원", delta=f"{int(diff):,}원")

    st.success(f"✅ 월 **{int(diff):,}원** 수익 개선이 가능합니다!")

    # 6. 차트 및 상세 데이터
    chart_df = pd.DataFrame({
        "구분": ["현재", "목표"],
        "수익": [cur_total, tar_total],
        "색상": ["#dee2e6", "#007aff"]
    })
    chart = alt.Chart(chart_df).mark_bar(size=40, cornerRadius=8).encode(
        x=alt.X('구분:N', axis=alt.Axis(labelAngle=0)),
        y=alt.Y('수익:Q', title=None),
        color=alt.Color('색상:N', scale=None)
    ).properties(height=200)
    st.altair_chart(chart, use_container_width=True)

    with st.expander("📑 상세 내역 보기"):
        df_data = {
            "항목": ["타입", "임차료", "매익률", "일매출", "월정산금"],
            "현재": [c_type, f"{c_rent:,}", f"{c_margin}%", f"{c_sales:,}", f"{int(cur_total):,}"],
            "목표": [t_type, f"{t_rent:,}", f"{t_margin}%", f"{t_sales:,}", f"{int(tar_total):,}"],
        }
        st.table(pd.DataFrame(df_data))
