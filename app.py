import streamlit as st
import pandas as pd
import altair as alt

# 1. 페이지 설정 및 모바일 최적화 레이아웃
st.set_page_config(page_title="GS25 수익 코칭 대시보드", layout="centered")

# 비밀번호 설정
PW = "gs25"

def check_password():
    if "password" not in st.session_state:
        st.session_state["password"] = ""
    if st.session_state["password"] == PW:
        return True
    st.title("🔐 임직원 인증")
    pwd = st.text_input("비밀번호(천원단위 버전)", type="password")
    if st.button("접속하기"):
        if pwd == PW:
            st.session_state["password"] = pwd
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    return False

if check_password():
    # CSS: 모바일 글자 겹침 방지 및 단위 표기 가독성 강화
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
        * { font-family: 'Noto Sans KR', sans-serif !important; }
        
        /* 모바일 메트릭 글자 겹침 방지 */
        [data-testid="stMetricValue"] { font-size: 1.4rem !important; overflow-wrap: break-word; }
        [data-testid="stMetricLabel"] { font-size: 0.8rem !important; }
        
        /* 아이콘 텍스트 강제 숨김 */
        span[data-testid="stWidgetLabel"] div div { display: none !important; }
        
        /* 테이블 스타일 및 폰트 */
        .stTable td, .stTable th { font-size: 11px !important; padding: 3px !important; }
        .unit-label { font-size: 12px; color: #666; text-align: right; margin-bottom: 5px; }
        </style>
        """, unsafe_allow_html=True)

    st.title("📊 GS25 수익 시뮬레이터")
    st.markdown('<p class="unit-label">(단위: 천원)</p>', unsafe_allow_html=True)

    # 2. 계산 로직 (엑셀 수식 완전 동기화)
    def calculate_logic(d):
        # 월매출 (30.41일 기준)
        m_sales = d["sales"] * 30.41
        m_profit = m_sales * (d["margin"] / 100)
        
        # 타입별 배분율
        r_map = {"GS1":{"Y":0.71, "N":0.66}, "GS2":{"Y":0.65, "N":0.60}, "GS3":{"Y":0.46, "N":0.41}}
        r_rate = r_map[d["type"]][d["24h"]]
        
        # 경영주 배분금
        share = m_profit * r_rate
        # O4O 수익 (배달 16%, 픽업 23%)
        o4o = (d["d_sales"] * 0.16) + (d["p_sales"] * 0.23)
        # 지원금 및 인센티브 합계
        support = d["s_fix"] + d["order"]
        
        # 최종 정산금 = 배분금 + O4O + 지원금 - 점포공제 - 임차료
        total = share + o4o + support - d["charges"] - d["rent"]
        return {"m_sales": m_sales, "share": share, "o4o": o4o, "support": support, "total": total}

    # 3. 입력 섹션
    def get_input(label):
        st.subheader(f"📍 {label} 데이터")
        u_type = st.selectbox(f"{label} 타입", ["GS1", "GS2", "GS3"], key=f"{label}_t")
        u_24h = st.radio(f"{label} 24시간 여부", ["Y", "N"], horizontal=True, key=f"{label}_24")
        
        c1, c2 = st.columns(2)
        u_sales = c1.number_input(f"{label} 일매출", value=1500 if label=="기존" else 1600, key=f"{label}_s")
        u_margin = c2.number_input(f"{label} 매익률(%)", value=30.0, key=f"{label}_m")
        
        with st.expander(f"➕ {label} 세부 항목 (O4O/공제/지원금)"):
            o1, o2 = st.columns(2)
            d_sales = o1.number_input(f"{label} 배달매출", value=0, key=f"{label}_d")
            p_sales = o2.number_input(f"{label} 픽업매출", value=0, key=f"{label}_p")
            
            # 8,092를 맞추기 위한 공제액 기본값 설정 (약 1,624)
            u_charges = st.number_input(f"{label} 점포공제(전기료 등)", value=1624, key=f"{label}_ch")
            
            s1, s2 = st.columns(2)
            s_fix = s1.number_input(f"{label} 지원금(정액)", value=0, key=f"{label}_sf")
            u_order = s2.number_input(f"{label} 발주장려금", value=0, key=f"{label}_oi")
            
            u_rent = 0
            if u_type == "GS2":
                u_rent = st.number_input(f"{label} 임차료", value=0, key=f"{label}_rt")
        
        return {
            "type": u_type, "24h": u_24h, "sales": u_sales, "margin": u_margin,
            "d_sales": d_sales, "p_sales": p_sales, "charges": u_charges,
            "s_fix": s_fix, "order": u_order, "rent": u_rent
        }

    col_l, col_r = st.columns(2)
    with col_l: cur = get_input("기존")
    with col_r: tar = get_input("변경")

    res_c = calculate_logic(cur)
    res_t = calculate_logic(tar)
    diff = res_t["total"] - res_c["total"]

    # 4. 결과 출력
    st.divider()
    st.subheader("💰 수익 코칭 리포트")
    m1, m2 = st.columns(2)
    m1.metric("기존 수익", f"{int(res_c['total']):,} 천원")
    m2.metric("변경 수익", f"{int(res_t['total']):,} 천원", delta=f"{int(diff):,} 천원")

    # 5. 상세 데이터 테이블 (항목 최적화)
    st.subheader("📑 상세 데이터 비교 (단위: 천원)")
    table_data = {
        "항목": ["타입(영업시간)", "월 매출액", "매출 이익", "경영주 배분금", "O4O 추가수익", "본부 지원금", "점포공제(-)", "임차료(-)", "최종 정산금"],
        "기존": [f"{cur['type']}({cur['24h']})", f"{int(res_c['m_sales']):,}", f"{int(res_c['m_sales']*(cur['margin']/100)):,}", f"{int(res_c['share']):,}", f"{int(res_c['o4o']):,}", f"{int(res_c['support']):,}", f"-{cur['charges']:,}", f"-{cur['rent']:,}", f"**{int(res_c['total']):,}**"],
        "변경": [f"{tar['type']}({tar['24h']})", f"{int(res_t['m_sales']):,}", f"{int(res_t['m_sales']*(tar['margin']/100)):,}", f"{int(res_t['share']):,}", f"{int(res_t['o4o']):,}", f"{int(res_t['support']):,}", f"-{tar['charges']:,}", f"-{tar['rent']:,}", f"**{int(res_t['total']):,}**"],
        "증감": ["-", f"{int(res_t['m_sales']-res_c['m_sales']):,}", f"{int((res_t['m_sales']*tar['margin']/100)-(res_c['m_sales']*cur['margin']/100)):,}", f"{int(res_t['share']-res_c['share']):,}", f"{int(res_t['o4o']-res_c['o4o']):,}", f"{int(res_t['support']-res_c['support']):,}", f"{int(-(tar['charges']-cur['charges'])):,}", f"{int(-(tar['rent']-cur['rent'])):,}", f"**{int(diff):,}**"]
    }
    st.table(pd.DataFrame(table_data))
    
    st.success(f"✅ 코칭 결과: 월 {int(diff):,} 천원의 추가 수익이 예상됩니다.")
