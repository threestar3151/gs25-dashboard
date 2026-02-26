import streamlit as st
import pandas as pd
import altair as alt

# 1. 페이지 설정
st.set_page_config(page_title="GS25 수익 코칭 대시보드", layout="centered")

# 비밀번호 설정 (천원 단위 버전)
PW = "gs254"

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
    # CSS: 모바일 겹침 방지 (Metric 세로 배치) 및 폰트 최적화
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
        * { font-family: 'Noto Sans KR', sans-serif !important; }
        
        /* 모바일 겹침 원천 차단: Metric 카드를 세로로 한 줄씩 배치 */
        [data-testid="stHorizontalBlock"] [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
            margin-bottom: 10px;
        }
        
        [data-testid="stMetricValue"] { font-size: 1.5rem !important; color: #007aff; }
        [data-testid="stMetricLabel"] { font-size: 0.9rem !important; }

        /* 테이블 폰트 축소 및 줄바꿈 방지 */
        .stTable td, .stTable th { font-size: 11px !important; padding: 5px !important; white-space: nowrap; }
        .unit-info { text-align: right; color: #666; font-size: 11px; margin-bottom: 5px; }
        
        /* GS2 강조 박스 */
        .gs2-active { background-color: #f1f8ff; padding: 10px; border-radius: 8px; border: 1px solid #007aff; margin: 10px 0; }
        </style>
        """, unsafe_allow_html=True)

    st.title("📊 GS25 수익 시뮬레이터")
    st.markdown('<p class="unit-info">(단위: 천원)</p>', unsafe_allow_html=True)

    # 2. 정밀 계산 로직
    def calc_settlement(d):
        m_sales = d["sales"] * 30.41 
        m_profit = m_sales * (d["margin"] / 100)
        
        r_map = {"GS1":{"Y":0.71, "N":0.66}, "GS2":{"Y":0.65, "N":0.60}, "GS3":{"Y":0.46, "N":0.41}}
        r_rate = r_map[d["type"]][d["24h"]]
        
        share = m_profit * r_rate
        o4o = (d["d_sales"] * 0.16) + (d["p_sales"] * 0.23)
        support = d["s_fix"] + d["order"]
        
        # 정산금 = 배분액 + O4O + 지원금 - 월세(임차료)
        total = share + o4o + support - d["rent"]
        return {"m_sales": m_sales, "m_profit": m_profit, "share": share, "o4o": o4o, "support": support, "total": total}

    # 3. 입력 섹션
    def get_input(label):
        st.subheader(f"📋 {label} 상황")
        u_type = st.selectbox(f"{label} 타입", ["GS1", "GS2", "GS3"], key=f"{label}_t")
        u_24h = st.radio(f"{label} 24H 여부", ["Y", "N"], horizontal=True, key=f"{label}_24")
        
        u_sales = st.number_input(f"{label} 일매출액", value=1500 if label=="기존" else 1600, key=f"{label}_s")
        u_margin = st.number_input(f"{label} 매익률(%)", value=30.0, step=0.1, key=f"{label}_m")
        
        # GS2 선택 시 추가 항목
        u_rent, u_ldep, u_sdep, u_prem = 0, 0, 0, 0
        if u_type == "GS2":
            st.markdown('<div class="gs2-active"><b>🏢 GS2 투자 및 임차 정보</b>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            u_ldep = c1.number_input(f"{label} 임차보증금", value=0, key=f"{label}_ld")
            u_sdep = c2.number_input(f"{label} 전대보증금", value=0, key=f"{label}_sd")
            u_prem = c1.number_input(f"{label} 권리금", value=0, key=f"{label}_pr")
            u_rent = c2.number_input(f"{label} 월 임차료", value=0, key=f"{label}_re")
            st.markdown('</div>', unsafe_allow_html=True)

        with st.expander(f"➕ {label} O4O 및 지원금"):
            o1, o2 = st.columns(2)
            d_sales = o1.number_input(f"{label} 배달매출", value=0, key=f"{label}_d")
            p_sales = o2.number_input(f"{label} 픽업매출", value=0, key=f"{label}_p")
            u_sfix = o1.number_input(f"{label} 정액지원금", value=0, key=f"{label}_sf")
            u_order = o2.number_input(f"{label} 발주장려금", value=0, key=f"{label}_oi")
            
        return {
            "type": u_type, "24h": u_24h, "sales": u_sales, "margin": u_margin,
            "d_sales": d_sales, "p_sales": p_sales, "s_fix": u_sfix, "order": u_order, 
            "rent": u_rent, "ldep": u_ldep, "sdep": u_sdep, "prem": u_prem
        }

    col_l, col_r = st.columns(2)
    with col_l: cur = get_input("기존")
    with col_r: tar = get_input("변경")

    res_c = calc_settlement(cur)
    res_t = calc_settlement(tar)
    diff = res_t["total"] - res_c["total"]

    # 4. 결과 출력
    st.divider()
    st.subheader("💰 수익 코칭 리포트")
    
    # 모바일 겹침 방지를 위해 단일 컬럼으로 순차 배치
    st.metric("기존 예상 수익", f"{int(res_c['total']):,} 천원")
    st.metric("목표 예상 수익", f"{int(res_t['total']):,} 천원", delta=f"{int(diff):,} 천원")

    # 5. 상세 데이터 테이블 (GS2 항목 포함)
    st.subheader("📑 상세 데이터 비교")
    
    table_data = {
        "항목": ["타입", "24시간", "일매출액", "매익률(%)", "월 매출액", "본부배분액", "O4O수익", "본부지원금", "임차보증금", "권리금", "월임차료(-)", "최종정산금"],
        "기존": [cur["type"], cur["24h"], f"{cur['sales']:,}", f"{cur['margin']}%", f"{int(res_c['m_sales']):,}", f"{int(res_c['share']):,}", f"{int(res_c['o4o']):,}", f"{int(res_c['support']):,}", f"{cur['ldep']:,}", f"{cur['prem']:,}", f"-{cur['rent']:,}", f"**{int(res_c['total']):,}**"],
        "변경": [tar["type"], tar["24h"], f"{tar['sales']:,}", f"{tar['margin']}%", f"{int(res_t['m_sales']):,}", f"{int(res_t['share']):,}", f"{int(res_t['o4o']):,}", f"{int(res_t['support']):,}", f"{tar['ldep']:,}", f"{tar['prem']:,}", f"-{tar['rent']:,}", f"**{int(res_t['total']):,}**"],
        "증감": ["-", "-", f"{tar['sales']-cur['sales']:,}", "-", f"{int(res_t['m_sales']-res_c['m_sales']):,}", f"{int(res_t['share']-res_c['share']):,}", f"{int(res_t['o4o']-res_c['o4o']):,}", f"{int(res_t['support']-res_c['support']):,}", f"{tar['ldep']-cur['ldep']:,}", f"{tar['prem']-cur['prem']:,}", f"{int(-(tar['rent']-cur['rent'])):,}", f"**{int(diff):,}**"]
    }
    st.table(pd.DataFrame(table_data))
    
    st.success(f"✅ 코칭 결과: 월 {int(diff):,} 천원의 추가 수익이 발생합니다.")
