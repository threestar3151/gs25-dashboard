import streamlit as st
import pandas as pd
import altair as alt

# 1. 페이지 설정
st.set_page_config(page_title="GS25 정밀 수익 시뮬레이터", layout="wide")

# 비밀번호 설정 (기존 유지)
PW = "gs25"

def check_password():
    if "password" not in st.session_state: st.session_state["password"] = ""
    if st.session_state["password"] == PW: return True
    st.title("🔐 GS25 임직원 인증")
    pwd = st.text_input("비밀번호를 입력하세요", type="password")
    if st.button("접속하기"):
        if pwd == PW:
            st.session_state["password"] = pwd
            st.rerun()
        else: st.error("비밀번호가 틀렸습니다.")
    return False

if check_password():
    # CSS: 모바일 및 웹 겸용 스타일링
    st.markdown("""
        <style>
        .stNumberInput input { font-size: 16px !important; }
        .gs2-box { background-color: #f1f8ff; padding: 10px; border-radius: 10px; border-left: 5px solid #007aff; margin-bottom: 15px; }
        .support-box { background-color: #fff9db; padding: 10px; border-radius: 10px; border-left: 5px solid #fcc419; margin-bottom: 15px; }
        .o4o-box { background-color: #ebfbee; padding: 10px; border-radius: 10px; border-left: 5px solid #40c057; margin-bottom: 15px; }
        </style>
        """, unsafe_allow_html=True)

    st.title("📊 GS25 정밀 수익 시뮬레이터")
    st.info("💡 엑셀 수식과 100% 동일하게 배달(16%) 및 픽업(23%) 수수료가 분리 적용되었습니다.")

    # 입력 함수 정의
    def input_data(label):
        st.subheader(f"📍 {label} 조건")
        u_type = st.selectbox(f"{label} 타입", ["GS1", "GS2", "GS3"], key=f"{label}_t")
        is_24h = st.radio(f"{label} 24시간 영업", ["Y", "N"], horizontal=True, key=f"{label}_24")
        
        col1, col2 = st.columns(2)
        sales = col1.number_input(f"{label} 일매출 (천원)", value=1500, key=f"{label}_s")
        margin = col2.slider(f"{label} 매익률 (%)", 20.0, 45.0, 30.0, key=f"{label}_m")
        
        # O4O 세부 입력
        st.markdown(f'<div class="o4o-box"><b>🛵 O4O 매출 (천원)</b>', unsafe_allow_html=True)
        o1, o2 = st.columns(2)
        deliv = o1.number_input(f"{label} 배달 매출", value=0, key=f"{label}_d")
        pick = o2.number_input(f"{label} 픽업 매출", value=0, key=f"{label}_p")
        st.markdown('</div>', unsafe_allow_html=True)

        # 지원금 세부 입력
        st.markdown(f'<div class="support-box"><b>💰 세부 지원금 (천원/%)</b>', unsafe_allow_html=True)
        s1, s2 = st.columns(2)
        s_fix = s1.number_input(f"{label} 정액지원금", value=150, key=f"{label}_sf")
        s_rate = s2.number_input(f"{label} 정률지원금(%)", value=0.0, step=0.1, key=f"{label}_sr")
        order = s1.number_input(f"{label} 발주장려금", value=30, key=f"{label}_oi")
        st.markdown('</div>', unsafe_allow_html=True)

        # GS2 투자비 세부 입력
        l_dep, s_dep, prem, rent = 0, 0, 0, 0
        if u_type == "GS2":
            st.markdown(f'<div class="gs2-box"><b>🏢 GS2 투자 및 비용 (천원)</b>', unsafe_allow_html=True)
            g1, g2 = st.columns(2)
            l_dep = g1.number_input(f"{label} 임차보증금", value=0, key=f"{label}_ld")
            s_dep = g2.number_input(f"{label} 전대보증금", value=0, key=f"{label}_sd")
            prem = g1.number_input(f"{label} 권리금", value=0, key=f"{label}_pr")
            rent = g2.number_input(f"{label} 월 임차료", value=0, key=f"{label}_rt")
            st.markdown('</div>', unsafe_allow_html=True)
        
        return {
            "type": u_type, "24h": is_24h, "sales": sales, "margin": margin,
            "deliv": deliv, "pick": pick, "s_fix": s_fix, "s_rate": s_rate,
            "order": order, "l_dep": l_dep, "s_dep": s_dep, "prem": prem, "rent": rent
        }

    # 비교 화면 구성
    left, right = st.columns(2)
    with left: cur = input_data("현재")
    with right: tar = input_data("목표")

    # 계산 로직 (엑셀 수식 정밀 반영)
    def calc(d):
        m_sales = d["sales"] * 30.41
        m_profit = m_sales * (d["margin"] / 100)
        
        # 배분율 (24시간 여부)
        r_map = {"GS1":{"Y":0.71,"N":0.66}, "GS2":{"Y":0.65,"N":0.60}, "GS3":{"Y":0.46,"N":0.41}}
        r_rate = r_map[d["type"]][d["24h"]]
        owner_share = m_profit * r_rate
        
        # O4O 수익 (배달 16%, 픽업 23%)
        o4o_profit = (d["deliv"] * 0.16) + (d["pick"] * 0.23)
        
        # 지원금 = (이익 * 정률%) + 정액 + 발주장려금
        total_sup = (m_profit * (d["s_rate"] / 100)) + d["s_fix"] + d["order"]
        
        final = owner_share + total_sup + o4o_profit - d["rent"]
        return {"m_sales": m_sales, "share": owner_share, "o4o": o4o_profit, "sup": total_sup, "final": final}

    res_c = calc(cur)
    res_t = calc(tar)
    diff = res_t["final"] - res_c["final"]

    # 결과 대시보드
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("현재 월 예상수익", f"{int(res_c['final']):,}원")
    c2.metric("목표 월 예상수익", f"{int(res_t['final']):,}원", delta=f"{int(diff):,}원")
    c3.metric("수익 개선율", f"{round((diff/res_c['final'])*100, 1) if res_c['final'] != 0 else 0}%")

    # 상세 비교 테이블 (엑셀 항목 모두 포함)
    st.subheader("📑 상세 비교 테이블 (엑셀 항목 동기화)")
    table_data = {
        "항목": ["가맹 타입", "24시간 영업", "일매출액", "매익률 (%)", "배달 매출", "픽업 매출", "O4O 추가수익", "발주장려금", "지원금(정액)", "지원금(정률)", "임차보증금", "전대보증금", "권리금", "월 임차료", "최종 월 정산금"],
        "현재(A)": [cur["type"], cur["24h"], f"{cur['sales']:,}원", f"{cur['margin']}%", f"{cur['deliv']:,}원", f"{cur['pick']:,}원", f"{int(res_c['o4o']):,}원", f"{cur['order']:,}원", f"{cur['s_fix']:,}원", f"{cur['s_rate']}%", f"{cur['l_dep']:,}원", f"{cur['s_dep']:,}원", f"{cur['prem']:,}원", f"-{cur['rent']:,}원", f"**{int(res_c['final']):,}원**"],
        "목표(B)": [tar["type"], tar["24h"], f"{tar['sales']:,}원", f"{tar['margin']}%", f"{tar['deliv']:,}원", f"{tar['pick']:,}원", f"{int(res_t['o4o']):,}원", f"{tar['order']:,}원", f"{tar['s_fix']:,}원", f"{tar['s_rate']}%", f"{tar['l_dep']:,}원", f"{tar['s_dep']:,}원", f"{tar['prem']:,}원", f"-{tar['rent']:,}원", f"**{int(res_t['final']):,}원**"],
        "증감(B-A)": ["-", "-", f"{tar['sales']-cur['sales']:,}", "-", f"{tar['deliv']-cur['deliv']:,}", f"{tar['pick']-cur['pick']:,}", f"{int(res_t['o4o']-res_c['o4o']):,}", f"{tar['order']-cur['order']:,}", f"{tar['sup']-res_c['sup']:,}", "-", f"{tar['l_dep']-cur['l_dep']:,}", "-", "-", f"{-(tar['rent']-cur['rent']):,}", f"**{int(diff):,}**"]
    }
    st.table(pd.DataFrame(table_data))
