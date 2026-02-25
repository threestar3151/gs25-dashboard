import streamlit as st
import pandas as pd
import altair as alt

# 1. 페이지 설정
st.set_page_config(page_title="GS25 수익 시뮬레이터", layout="centered")

# --- 비밀번호 인증 로직 ---
PW = "gs25"  # 설정하신 비밀번호

def check_password():
    if "password" not in st.session_state:
        st.session_state["password"] = ""
    if st.session_state["password"] == PW:
        return True

    st.title("🔐 임직원 인증")
    pwd = st.text_input("비밀번호를 입력하세요", type="password")
    if st.button("접속하기"):
        if pwd == PW:
            st.session_state["password"] = pwd
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    return False

if check_password():
    # 2. CSS 수정 (아이콘 강제 제거 및 간격 확보)
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
        * { font-family: 'Noto Sans KR', sans-serif !important; }
        
        /* 깨지는 아이콘 텍스트 숨기기 */
        span[data-testid="stWidgetLabel"] > div > div > display-element {
            display: none !important;
        }
        
        /* 메트릭 카드 간격 확보 */
        [data-testid="stMetric"] {
            background-color: #ffffff;
            border: 1px solid #eee;
            padding: 20px !important;
            margin-bottom: 10px;
            border-radius: 15px;
        }
        
        /* 겹침 방지를 위한 섹션 간격 */
        .stSlider { margin-top: 20px; margin-bottom: 20px; }
        .stNumberInput { margin-bottom: 15px; }
        
        /* 표 가독성 */
        .stTable { margin-top: 20px; }
        </style>
        """, unsafe_allow_html=True)

    # 3. 데이터
    type_info = {
        "GS1": {"support": 184.0, "royalty": 0.71},
        "GS2": {"support": 205.8, "royalty": 0.65},
        "GS3": {"support": 240.4, "royalty": 0.46}
    }

    st.title("📊 GS25 수익 시뮬레이터")
    st.write("---")

    # 4. 입력 섹션
    st.subheader("📋 [1] 현재 현황 입력")
    c_type = st.selectbox("현재 가맹 타입", ["GS1", "GS2", "GS3"])
    c_rent = 0
    if c_type == "GS2":
        c_rent = st.number_input("현재 월 임차료 (천원)", value=0, step=10)
    c_sales = st.number_input("현재 일매출 (천원)", value=1500, step=10)
    c_margin = st.slider("현재 매익률 (%)", 20.0, 45.0, 30.0, step=0.1)
    c_o4o = st.number_input("현재 O4O 월매출 (천원)", value=0, step=10)

    st.write("---")
    
    st.subheader("🎯 [2] 코칭 목표 설정")
    t_type = st.selectbox("목표 가맹 타입", ["GS1", "GS2", "GS3"], index=(["GS1", "GS2", "GS3"].index(c_type)))
    t_rent = 0
    if t_type == "GS2":
        t_rent = st.number_input("목표 월 임차료 (천원)", value=0, step=10)
    t_sales = st.number_input("목표 일매출 (천원)", value=c_sales + 200, step=10)
    t_margin = st.slider("목표 매익률 (%)", 20.0, 45.0, c_margin + 1.5, step=0.1)
    t_o4o = st.number_input("목표 O4O 월매출 (천원)", value=500, step=10)

    # 5. 계산 로직
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

    # 6. 결과 출력
    st.write("---")
    st.subheader("💰 수익 분석 결과")
    
    col1, col2 = st.columns(2)
    col1.metric("기존 수익", f"{int(cur_total):,}원")
    col2.metric("목표 수익", f"{int(tar_total):,}원", delta=f"{int(diff):,}원")

    if diff > 0:
        st.success(f"💡 월 {int(diff):,}원의 추가 수익 창출이 가능합니다!")
    else:
        st.warning(f"💡 수익 개선을 위한 추가 코칭이 필요합니다.")

    # 7. 차트
    chart_df = pd.DataFrame({
        "구분": ["현재", "목표"],
        "수익": [cur_total, tar_total],
        "Color": ["#cccccc", "#007aff"]
    })
    chart = alt.Chart(chart_df).mark_bar(size=50, cornerRadiusTopLeft=10, cornerRadiusTopRight=10).encode(
        x=alt.X('구분:N', axis=alt.Axis(labelAngle=0)),
        y=alt.Y('수익:Q', title=None),
        color=alt.Color('Color:N', scale=None)
    ).properties(height=300)
    st.altair_chart(chart, use_container_width=True)

    # 8. 상세 내역 (접기 대신 일반 텍스트로 변경하여 깨짐 방지)
    st.write("---")
    st.subheader("📑 상세 비교 데이터")
    df_data = {
        "항목": ["타입", "임차료", "매익률", "일매출", "월정산금"],
        "현재": [c_type, f"{c_rent:,}", f"{c_margin}%", f"{c_sales:,}", f"{int(cur_total):,}"],
        "목표": [t_type, f"{t_rent:,}", f"{t_margin}%", f"{t_sales:,}", f"{int(tar_total):,}"],
    }
    st.table(pd.DataFrame(df_data))
    st.caption("※ 본 결과는 시뮬레이션이며 실제 정산과 다를 수 있습니다.")
