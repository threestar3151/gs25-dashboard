import streamlit as st
import pandas as pd
import altair as alt

# 1. 페이지 설정 및 아이콘 오류 강제 방지
st.set_page_config(page_title="GS25 수익 시뮬레이터", layout="wide")

# 비밀번호 설정
PW = "gs25"

def check_password():
    if "password" not in st.session_state: st.session_state["password"] = ""
    if st.session_state["password"] == PW: return True
    st.title("🔐 GS25 임직원 전용")
    pwd = st.text_input("비밀번호 입력", type="password")
    if st.button("접속하기"):
        if pwd == PW:
            st.session_state["password"] = pwd
            st.rerun()
        else: st.error("비밀번호가 틀렸습니다.")
    return False

if check_password():
    # CSS: 화면 깨짐(아이콘 텍스트 겹침) 방지 및 모바일 가독성 향상
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
        * { font-family: 'Noto Sans KR', sans-serif !important; }
        
        /* 시스템 아이콘 텍스트 강제 숨김 */
        span[data-testid="stWidgetLabel"] div div, .stExpander span {
            font-family: 'Noto Sans KR' !important;
        }
        
        /* 테이블 폰트 및 간격 최적화 */
        .stTable td { font-size: 14px !important; padding: 8px !important; }
        .main-result { background-color: #f8f9fa; padding: 20px; border-radius: 15px; border: 1px solid #e9ecef; }
        </style>
        """, unsafe_allow_html=True)

    st.title("📊 GS25 수익 시뮬레이터")
    st.write("---")

    # 입력 섹션 구성
    def input_group(label):
        st.subheader(f"📍 {label} 상황")
        
        # 기본 정보
        u_type = st.selectbox(f"{label} 타입", ["GS1", "GS2", "GS3"], key=f"{label}_t")
        is_24h = st.radio(f"{label} 24시간", ["Y", "N"], horizontal=True, key=f"{label}_24")
        
        col1, col2 = st.columns(2)
        sales = col1.number_input(f"{label} 일매출(천원)", value=1500, key=f"{label}_s")
        margin = col2.number_input(f"{label} 매익률(%)", value=30.0, step=0.1, key=f"{label}_m")
        
        # O4O 세부 정보
        with st.expander(f"🛵 {label} O4O/지원금 세부설정"):
            o1, o2 = st.columns(2)
            d_sales = o1.number_input(f"{label} 배달매출", value=0, key=f"{label}_ds")
            p_sales = o2.number_input(f"{label} 픽업매출", value=0, key=f"{label}_ps")
            
            s1, s2 = st.columns(2)
            s_fix = s1.number_input(f"{label} 정액지원", value=150, key=f"{label}_sf")
            s_rate = s2.number_input(f"{label} 정률지원(%)", value=0.0, step=0.1, key=f"{label}_sr")
            order = s1.number_input(f"{label} 발주장려금", value=30, key=f"{label}_oi")

        # GS2 투자비 정보
        l_dep, s_dep, prem, rent = 0, 0, 0, 0
        if u_type == "GS2":
            with st.expander(f"🏢 {label} GS2 투자/비용"):
                g1, g2 = st.columns(2)
                l_dep = g1.number_input(f"{label} 임차보증금", value=0, key=f"{label}_ld")
                s_dep = g2.number_input(f"{label} 전대보증금", value=0, key=f"{label}_sd")
                prem = g1.number_input(f"{label} 권리금", value=0, key=f"{label}_pr")
                rent = g2.number_input(f"{label} 월세(임차료)", value=0, key=f"{label}_rt")
        
        return {
            "type": u_type, "24h": is_24h, "sales": sales, "margin": margin,
            "d_sales": d_sales, "p_sales": p_sales, "s_fix": s_fix, 
            "s_rate": s_rate, "order": order, "l_dep": l_dep, 
            "s_dep": s_dep, "prem": prem, "rent": rent
        }

    c_col, t_col = st.columns(2)
    with c_col: cur = input_group("현재")
    with t_col: tar = input_group("목표")

    # 엑셀과 100% 일치시키기 위한 정밀 계산 로직
    def calc_all(d):
        # 1. 월매출 및 매출이익 (30.41일 기준)
        m_sales = d["sales"] * 30.41
        m_profit = m_sales * (d["margin"] / 100)
        
        # 2. 배분율 결정
        r_rates = {"GS1":{"Y":0.71, "N":0.66}, "GS2":{"Y":0.65, "N":0.60}, "GS3":{"Y":0.46, "N":0.41}}
        r_rate = r_rates[d["type"]][d["24h"]]
        
        # 3. 항목별 계산
        owner_share = m_profit * r_rate
        o4o_profit = (d["d_sales"] * 0.16) + (d["p_sales"] * 0.23)
        support = (m_profit * (d["s_rate"]/100)) + d["s_fix"] + d["order"]
        
        # 4. 최종 정산금
        total = owner_share + o4o_profit + support - d["rent"]
        
        return {
            "m_sales": m_sales, "owner_share": owner_share,
            "o4o": o4o_profit, "support": support, "total": total
        }

    res_c = calc_all(cur)
    res_t = calc_all(tar)
    diff = res_t["total"] - res_c["total"]

    # 결과 대시보드
    st.write("---")
    st.markdown('<div class="main-result">', unsafe_allow_html=True)
    m1, m2 = st.columns(2)
    m1.metric("현재 월 예상수익", f"{int(res_c['total']):,}원")
    m2.metric("목표 월 예상수익", f"{int(res_t['total']):,}원", delta=f"{int(diff):,}원")
    st.markdown('</div>', unsafe_allow_html=True)

    # 상세 비교 테이블 (엑셀 항목 전체 동기화)
    st.subheader("📑 상세 비교 데이터 (엑셀 항목 일치)")
    
    table_data = {
        "항목": ["타입/영업시간", "월 매출액", "매출 이익", "배분율", "경영주 배분금", "배달 수익(16%)", "픽업 수익(23%)", "지원금 합계", "임차보증금", "권리금", "월 임차료", "최종 정산금"],
        "현재": [f"{cur['type']}({cur['24h']})", f"{int(res_c['m_sales']):,}원", f"{int(res_c['m_sales']*(cur['margin']/100)):,}원", f"{int(res_c['owner_share']/ (res_c['m_sales']*(cur['margin']/100)) * 100) if res_c['m_sales']!=0 else 0}%", f"{int(res_c['owner_share']):,}원", f"{int(cur['d_sales']*0.16):,}원", f"{int(cur['p_sales']*0.23):,}원", f"{int(res_c['support']):,}원", f"{cur['l_dep']:,}원", f"{cur['prem']:,}원", f"-{cur['rent']:,}원", f"**{int(res_c['total']):,}원**"],
        "목표": [f"{tar['type']}({tar['24h']})", f"{int(res_t['m_sales']):,}원", f"{int(res_t['m_sales']*(tar['margin']/100)):,}원", f"{int(res_t['owner_share']/ (res_t['m_sales']*(tar['margin']/100)) * 100) if res_t['m_sales']!=0 else 0}%", f"{int(res_t['owner_share']):,}원", f"{int(tar['d_sales']*0.16):,}원", f"{int(tar['p_sales']*0.23):,}원", f"{int(res_t['support']):,}원", f"{tar['l_dep']:,}원", f"{tar['prem']:,}원", f"-{tar['rent']:,}원", f"**{int(res_t['total']):,}원**"]
    }
    st.table(pd.DataFrame(table_data))

    st.success(f"✅ 코칭 결과: 월 {int(diff):,}원의 추가 수익 창출이 가능합니다!")
