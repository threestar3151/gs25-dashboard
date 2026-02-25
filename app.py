import streamlit as st
import pandas as pd
import altair as alt

# 1. 페이지 설정
st.set_page_config(page_title="GS25 수익 시뮬레이터", layout="centered")

# --- 비밀번호 인증 로직 ---
PW = "gs254"  # << 원하는 비밀번호로 변경하세요

def check_password():
    if "password" not in st.session_state:
        st.session_state["password"] = ""

    if st.session_state["password"] == PW:
        return True

    st.title("🔒 인증이 필요합니다")
    st.write("본 앱은 GS25 임직원 전용 시뮬레이터입니다.")
    pwd = st.text_input("비밀번호를 입력하세요", type="password")
    if st.button("접속하기"):
        if pwd == PW:
            st.session_state["password"] = pwd
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    return False

# 비밀번호 통과 시에만 메인 화면 표시
if check_password():
    # 2. 스타일 설정
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
        * { font-family: 'Noto Sans KR', sans-serif !important; }
        [data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #eee;
            padding: 15px;
            border-radius: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .stTable td, .stTable th { font-size: 13px !important; padding: 5px !important; }
        </style>
        """, unsafe_allow_html=True)

    # 3. 기초 데이터
    type_info = {
        "GS1": {"support": 184.0, "royalty": 0.71},
        "GS2": {"support": 205.8, "royalty": 0.65},
        "GS3": {"support": 240.4, "royalty": 0.46}
    }

    st.title("📊 GS25 수익 시뮬레이터")
    st.caption("경영주님의 수익 개선을 위한 정밀 분석 도구")

    # 4. 입력 섹션
    with st.expander("⚙️ 데이터 입력 및 목표 설정", expanded=True):
        st.subheader("📍 [1] 현재 현황")
        c_type = st.selectbox("현재 타입", ["GS1", "GS2", "GS3"], key="c_t")
        c_rent = 0
        if c_type == "GS2":
            c_rent = st.number_input("현재 월 임차료 (천원)", value=0, step=10)
        c_sales = st.number_input("현재 일매출 (천원)", value=1500, step=10, key="c_s")
        c_margin = st.slider("현재 매익률 (%)", 20.0, 45.0, 30.0, step=0.1, key="c_m")
        c_o4o = st.number_input("현재 O4O 매출 (천원)", value=0, step=10, key="c_o")

        st.divider()
        
        st.subheader("🚀 [2] 코칭 목표")
        t_type = st.selectbox("목표 타입", ["GS1", "GS2", "GS3"], index=(["GS1", "GS2", "GS3"].index(c_type)), key="t_t")
        t_rent = 0
        if t_type == "GS2":
            t_rent = st.number_input("목표 월 임차료 (천원)", value=0, step=10)
        t_sales = st.number_input("목표 일매출 (천원)", value=c_sales + 200, step=10, key="t_s")
        t_margin = st.slider("목표 매익률 (%)", 20.0, 45.0, c_margin + 1.5, step=0.1, key="t_m")
        t_o4o = st.number_input("목표 O4O 매출 (천원)", value=500, step=10, key="t_o")

    # 5. 계산 로직
    def calc(sales, margin, utype, o4o, rent=0):
        m_sales = sales * 30.41
        m_profit = m_sales * (margin / 100)
        royalty = m_profit * type_info[utype]["royalty"]
        support = type_info[utype]["support"]
        o4o_profit = o4o * 0.16
        total = (royalty + support + o4o_profit) - rent
        return {"total": total}

    cur_total = calc(c_sales, c_margin, c_type, c_o4o, c_rent)["total"]
    tar_total = calc(t_sales, t_margin, t_type, t_o4o, t_rent)["total"]
    diff = tar_total - cur_total

    # 6. 결과 출력
    st.subheader("💰 수익 분석 결과")
    col1, col2 = st.columns(2)
    col1.metric("기존 수익", f"{int(cur_total):,}원")
    col2.metric("목표 수익", f"{int(tar_total):,}원", delta=f"{int(diff):,}원")

    st.success(f"💡 월 **{int(diff):,}원** 만큼의 수익이 개선됩니다!")

    # 7. 차트
    chart_df = pd.DataFrame({
        "구분": ["현재", "목표"],
        "수익": [cur_total, tar_total],
        "color": ["#dee2e6", "#007aff"]
    })
    chart = alt.Chart(chart_df).mark_bar(size=50, cornerRadiusTopLeft=10, cornerRadiusTopRight=10).encode(
        x=alt.X('구분:N', axis=alt.Axis(labelAngle=0)),
        y=alt.Y('수익:Q', title=None),
        color=alt.Color('color:N', scale=None)
    ).properties(height=250)
    st.altair_chart(chart, use_container_width=True)

    # 8. 상세 데이터
    with st.expander("📑 상세 데이터 확인"):
        df_data = {
            "항목": ["타입", "임차료", "매익률", "일매출", "월정산금"],
            "현재": [c_type, f"{c_rent:,}", f"{c_margin}%", f"{c_sales:,}", f"{int(cur_total):,}"],
            "목표": [t_type, f"{t_rent:,}", f"{t_margin}%", f"{t_sales:,}", f"{int(tar_total):,}"],
        }
        st.table(pd.DataFrame(df_data))

    st.caption("본 결과는 입력값에 근거하며 실제 정산과 차이가 있을 수 있습니다.")
