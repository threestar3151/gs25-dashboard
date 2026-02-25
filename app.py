import streamlit as st
import pandas as pd
import altair as alt

# 1. 페이지 설정 및 모바일 최적화 레이아웃
st.set_page_config(page_title="GS25 수익 코칭 대시보드", layout="centered")

# 비밀번호 설정 (천원 단위 버전)
PW = "gs25"

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
    # CSS: 모바일 겹침 방지 및 폰트 크기 강제 조정
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
        * { font-family: 'Noto Sans KR', sans-serif !important; }
        
        /* 모바일 겹침 방지: 메트릭을 가로가 아닌 세로로 배치하거나 폰트 대폭 축소 */
        [data-testid="stMetricValue"] { font-size: 1.3rem !important; color: #007aff; line-height: 1.2; }
        [data-testid="stMetricLabel"] { font-size: 0.75rem !important; margin-bottom: 2px; }
        [data-testid="stMetricDelta"] { font-size: 0.8rem !important; }
        
        /* 컬럼 간격 조정 */
        [data-testid="column"] { padding: 0 5px !important; }

        /* 테이블 폰트 및 스타일 */
        .stTable td, .stTable th { font-size: 11px !important; padding: 4px !important; }
        .unit-info { text-align: right; color: #666; font-size: 12px; margin-bottom: 5px; }
        </style>
        """, unsafe_allow_html=True)

    st.title("📊 GS25 수익 시뮬레이터")
    st.markdown('<p class="unit-info">(단위: 천원)</p>', unsafe_allow_html=True)

    # 2. 정밀 계산 로직 (엑셀 수식 동기화)
    # 요청하신 대로 '기본점포공제'를 삭제하고 엑셀의 순수 배분액 중심으로 계산합니다.
    def calc_settlement(d):
        m_sales = d["sales"] * 30.41 # 엑셀 기준 한 달 일수
        m_profit = m_sales * (d["margin"] / 100)
        
        # 타입별 배분율
        r_map = {"GS1":{"Y":0.71, "N":0.66}, "GS2":{"Y":0.65, "N":0.60}, "GS3":{"Y":0.46, "N":0.41}}
        r_rate = r_map[d["type"]][d["24h"]]
        
        share = m_profit * r_rate # 본부배분액
        o4o = (d["d_sales"] * 0.16) + (d["p_sales"] * 0.23) # O4O 수익 (배달/픽업 분리)
        support = d["s_fix"] + d["order"] # 지원금 합계
        
        # 최종 정산금 = 배분액 + O4O + 지원금 - 임차료
        # (기존에 수치를 맞추기 위해 넣었던 '점포공제'는 삭제되었습니다)
        total = share + o4o + support - d["rent"]
        return {"m_sales": m_sales, "m_profit": m_profit, "share": share, "o4o": o4o, "support": support, "total": total}

    # 3. 입력 섹션 (깔끔한 1열 배치)
    def get_input(label):
        st.subheader(f"📋 {label} 데이터")
        u_type = st.selectbox(f"{label} 타입", ["GS1", "GS2", "GS3"], key=f"{label}_t")
        u_24h = st.radio(f"{label} 24H 여부", ["Y", "N"], horizontal=True, key=f"{label}_24")
        
        c1, c2 = st.columns(2)
        u_sales = c1.number_input(f"{label} 일매출액", value=1500 if label=="기존" else 1600, key=f"{label}_s")
        u_margin = c2.number_input(f"{label} 매익률(%)", value=30.0, step=0.1, key=f"{label}_m")
        
        with st.expander(f"➕ {label} 세부 설정 (O4O/지원금)"):
            st.markdown("**🛵 O4O 매출**")
            o1, o2 = st.columns(2)
            d_sales = o1.number_input(f"{label} 배달매출", value=0, key=f"{label}_d")
            p_sales = o2.number_input(f"{label} 픽업매출", value=0, key=f"{label}_p")
            
            st.markdown("**💰 지원금 및 비용**")
            s1, s2 = st.columns(2)
            u_sfix = s1.number_input(f"{label} 정액지원금", value=0, key=f"{label}_sf")
            u_order = s2.number_input(f"{label} 발주장려금", value=0, key=f"{label}_oi")
            
            u_rent = 0
            if u_type == "GS2":
                u_rent = st.number_input(f"{label} 월 임차료", value=0, key=f"{label}_rt")
        
        return {
            "type": u_type, "24h": u_24h, "sales": u_sales, "margin": u_margin,
            "d_sales": d_sales, "p_sales": p_sales, "s_fix": u_sfix, "order": u_order, "rent": u_rent
        }

    # 현재 vs 목표 입력
    col_l, col_r = st.columns(2)
    with col_l: cur = get_input("기존")
    with col_r: tar = get_input("변경")

    res_c = calc_settlement(cur)
    res_t = calc_settlement(tar)
    diff = res_t["total"] - res_c["total"]

    # 4. 결과 리포트 (겹침 해결을 위해 가독성 중심 배치)
    st.divider()
    st.subheader("💰 수익 코칭 리포트")
    
    # 모바일에서 좌우 배치가 깨질 수 있어 컨테이너와 간격 최적화
    m_col1, m_col2 = st.columns(2)
    with m_col1:
        st.metric("기존 예상수익", f"{int(res_c['total']):,} 천원")
    with m_col2:
        st.metric("목표 예상수익", f"{int(res_t['total']):,} 천원", delta=f"{int(diff):,} 천원")

    # 5. 상세 데이터 테이블 (항목 최적화 및 엑셀 명칭 동기화)
    st.subheader("📑 상세 분석 데이터 (단위: 천원)")
    
    df_data = {
        "항목": ["가맹 타입", "영업 시간", "일매출액", "매익률(%)", "월 매출액", "매출 이익", "본부배분액", "O4O 추가수익", "본부 지원금", "임차료(-)", "최종 정산금액"],
        "기존": [cur["type"], f"{cur['24h']}H", f"{cur['sales']:,}", f"{cur['margin']}%", f"{int(res_c['m_sales']):,}", f"{int(res_c['m_profit']):,}", f"{int(res_c['share']):,}", f"{int(res_c['o4o']):,}", f"{int(res_c['support']):,}", f"-{cur['rent']:,}", f"**{int(res_c['total']):,}**"],
        "변경": [tar["type"], f"{tar['24h']}H", f"{tar['sales']:,}", f"{tar['margin']}%", f"{int(res_t['m_sales']):,}", f"{int(res_t['m_profit']):,}", f"{int(res_t['share']):,}", f"{int(res_t['o4o']):,}", f"{int(res_t['support']):,}", f"-{tar['rent']:,}", f"**{int(res_t['total']):,}**"],
        "증감": ["-", "-", f"{tar['sales']-cur['sales']:,}", "-", f"{int(res_t['m_sales']-res_c['m_sales']):,}", f"{int(res_t['m_profit']-res_c['m_profit']):,}", f"{int(res_t['share']-res_c['share']):,}", f"{int(res_t['o4o']-res_c['o4o']):,}", f"{int(res_t['support']-res_c['support']):,}", f"{int(-(tar['rent']-cur['rent'])):,}", f"**{int(diff):,}**"]
    }
    st.table(pd.DataFrame(df_data))
    
    st.success(f"✅ 코칭 결과: 월 {int(diff):,} 천원의 추가 수익이 발생합니다.")
