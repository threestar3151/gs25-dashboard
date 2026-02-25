import streamlit as st
import pandas as pd
import altair as alt

# 1. 페이지 설정 및 모바일 겹침 방지 CSS
st.set_page_config(page_title="GS25 수익 시뮬레이터", layout="centered")

# 비밀번호 설정
PW = "gs25"

def check_password():
    if "password" not in st.session_state: st.session_state["password"] = ""
    if st.session_state["password"] == PW: return True
    st.title("🔐 GS25 임직원 인증")
    pwd = st.text_input("비밀번호", type="password")
    if st.button("접속하기"):
        if pwd == PW:
            st.session_state["password"] = pwd
            st.rerun()
        else: st.error("비밀번호가 틀렸습니다.")
    return False

if check_password():
    # CSS: 모바일 텍스트 겹침 방지 및 지표(Metric) 크기 최적화
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
        * { font-family: 'Noto Sans KR', sans-serif !important; }
        
        /* 모바일에서 Metric 텍스트 겹침 해결 */
        [data-testid="stMetricValue"] { font-size: 20px !important; }
        [data-testid="stMetricLabel"] { font-size: 13px !important; }
        
        /* 아이콘 텍스트 강제 제거 */
        .stExpander span { font-family: 'Noto Sans KR' !important; }
        
        /* 테이블 폰트 조정 */
        .stTable td { font-size: 13px !important; padding: 5px !important; }
        .stTable th { font-size: 13px !important; background-color: #f8f9fa; }
        
        /* 입력창 박스 디자인 */
        .input-card { background-color: #ffffff; padding: 15px; border-radius: 12px; border: 1px solid #eee; margin-bottom: 15px; }
        </style>
        """, unsafe_allow_html=True)

    # 2. 기초 데이터 (엑셀 시트 수치 반영)
    # 24시간 여부에 따른 배분율: GS1(71/66), GS2(65/60), GS3(46/41)
    royalty_rules = {
        "GS1": {"Y": 0.71, "N": 0.66},
        "GS2": {"Y": 0.65, "N": 0.60},
        "GS3": {"Y": 0.46, "N": 0.41}
    }

    st.title("📊 GS25 수익 시뮬레이터")
    st.caption("엑셀 수식 100% 동기화 버전 (O4O 수익 강화)")

    # 3. 입력 섹션
    def input_section(label):
        st.subheader(f"📍 {label} 상황")
        with st.container():
            u_type = st.selectbox(f"{label} 타입", ["GS1", "GS2", "GS3"], key=f"{label}_t")
            is_24h = st.radio(f"{label} 24시간 영업", ["Y", "N"], horizontal=True, key=f"{label}_24")
            
            c1, c2 = st.columns(2)
            sales = c1.number_input(f"{label} 일매출(천원)", value=1500, step=10, key=f"{label}_s")
            margin = c2.number_input(f"{label} 매익률(%)", value=30.0, step=0.1, key=f"{label}_m")
            
            # O4O 매출 (배달/픽업 통합 입력)
            st.markdown("---")
            st.markdown("**🛵 O4O 매출 설정 (천원)**")
            o1, o2 = st.columns(2)
            d_sales = o1.number_input(f"{label} 배달 매출", value=0, key=f"{label}_d")
            p_sales = o2.number_input(f"{label} 픽업 매출", value=0, key=f"{label}_p")
            
            # 지원금 설정
            st.markdown("---")
            st.markdown("**💰 본부 지원금 설정 (천원)**")
            s1, s2 = st.columns(2)
            s_fix = s1.number_input(f"{label} 정액지원(기본/상생)", value=180, key=f"{label}_sf")
            s_rate = s2.number_input(f"{label} 정률지원(%)", value=0.0, step=0.1, key=f"{label}_sr")
            order = s1.number_input(f"{label} 발주장려금", value=30, key=f"{label}_oi")
            
            # 임차료 (GS2 전용)
            rent = 0
            if u_type == "GS2":
                rent = st.number_input(f"{label} 월 임차료(천원)", value=0, key=f"{label}_rent")
            
            return {
                "type": u_type, "24h": is_24h, "sales": sales, "margin": margin,
                "d_sales": d_sales, "p_sales": p_sales, "s_fix": s_fix,
                "s_rate": s_rate, "order": order, "rent": rent
            }

    l_col, r_col = st.columns(2)
    with l_col: cur = input_section("현재")
    with r_col: tar = input_section("목표")

    # 4. 정밀 계산 로직 (엑셀 수식 동기화)
    def calc_profit(d):
        # 월매출 (엑셀 기준 30.41일)
        m_sales = d["sales"] * 30.41
        # 매출이익
        m_profit = m_sales * (d["margin"] / 100)
        # 경영주 배분금 (이익 * 배분율)
        r_rate = royalty_rules[d["type"]][d["24h"]]
        owner_share = m_profit * r_rate
        # O4O 수익 (배달 16%, 픽업 23% 적용)
        o4o_profit = (d["d_sales"] * 0.16) + (d["p_sales"] * 0.23)
        # 지원금 합계 (정률 + 정액 + 발주)
        support_total = (m_profit * (d["s_rate"]/100)) + d["s_fix"] + d["order"]
        # 최종 정산금액 (배분금 + O4O수익 + 지원금 - 임차료)
        total_settlement = owner_share + o4o_profit + support_total - d["rent"]
        
        return {
            "m_sales": m_sales, "m_profit": m_profit, "share": owner_share,
            "o4o": o4o_profit, "support": support_total, "total": total_settlement, "rate": r_rate
        }

    res_c = calc_profit(cur)
    res_t = calc_profit(tar)
    diff = res_t["total"] - res_c["total"]

    # 5. 결과 화면 출력
    st.divider()
    st.subheader("💰 수익 코칭 리포트")
    m1, m2 = st.columns(2)
    m1.metric("현재 월 예상 수익", f"{int(res_c['total']):,}원")
    m2.metric("목표 월 예상 수익", f"{int(res_t['total']):,}원", delta=f"{int(diff):,}원")

    # 6. 상세 비교 테이블 (투자비 삭제 및 엑셀 항목 일치)
    st.subheader("📑 상세 항목 비교 (엑셀 기준)")
    
    df_compare = pd.DataFrame({
        "항목": ["가맹 타입", "영업 시간", "일평균 매출액", "매익률", "월 매출액", "매출 이익", "경영주 배분금", "O4O 추가수익", "본부 지원금 합계", "최종 정산금액"],
        "현재(A)": [
            cur["type"], f"{cur['24h']}시간", f"{cur['sales']:,}원", f"{cur['margin']}%",
            f"{int(res_c['m_sales']):,}원", f"{int(res_c['m_profit']):,}원",
            f"{int(res_c['share']):,}원", f"{int(res_c['o4o']):,}원",
            f"{int(res_c['support']):,}원", f"**{int(res_c['total']):,}원**"
        ],
        "목표(B)": [
            tar["type"], f"{tar['24h']}시간", f"{tar['sales']:,}원", f"{tar['margin']}%",
            f"{int(res_t['m_sales']):,}원", f"{int(res_t['m_profit']):,}원",
            f"{int(res_t['share']):,}원", f"{int(res_t['o4o']):,}원",
            f"{int(res_t['support']):,}원", f"**{int(res_t['total']):,}원**"
        ],
        "증감": [
            "-", "-", f"{tar['sales']-cur['sales']:,}", "-",
            f"{int(res_t['m_sales']-res_c['m_sales']):,}", f"{int(res_t['m_profit']-res_c['m_profit']):,}",
            f"{int(res_t['share']-res_c['share']):,}", f"{int(res_t['o4o']-res_c['o4o']):,}",
            f"{int(res_t['support']-res_c['support']):,}", f"**{int(diff):,}**"
        ]
    })
    
    st.table(df_compare)
    st.success(f"✅ 코칭 결과: 월 {int(diff):,}원의 수익 개선이 예상됩니다!")
    st.caption("※ 본 데이터는 엑셀 계산 수식(일수 30.41일)을 근거로 산출되었습니다.")
