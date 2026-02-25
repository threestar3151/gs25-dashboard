import streamlit as st
import pandas as pd
import altair as alt

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="GS25 정밀 수익 시뮬레이터", layout="wide")

# 비밀번호 설정
PW = "gs254"

def check_password():
    if "password" not in st.session_state:
        st.session_state["password"] = ""
    if st.session_state["password"] == PW:
        return True
    st.title("🔐 GS25 임직원 인증")
    pwd = st.text_input("비밀번호를 입력하세요", type="password")
    if st.button("접속하기"):
        if pwd == PW:
            st.session_state["password"] = pwd
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    return False

if check_password():
    # CSS: 모바일 및 웹 겸용 스타일링
    st.markdown("""
        <style>
        .stNumberInput input { font-size: 16px !important; }
        .gs2-box { background-color: #f1f8ff; padding: 15px; border-radius: 10px; border-left: 5px solid #007aff; margin-bottom: 10px; }
        .support-box { background-color: #fff9db; padding: 15px; border-radius: 10px; border-left: 5px solid #fcc419; margin-bottom: 10px; }
        </style>
        """, unsafe_allow_html=True)

    st.title("📊 GS25 정밀 수익 시뮬레이터")
    st.write("---")

    # 데이터 입력 함수
    def input_section(label_prefix):
        st.subheader(f"📍 {label_prefix} 조건 설정")
        
        col1, col2 = st.columns(2)
        with col1:
            u_type = st.selectbox(f"{label_prefix} 타입", ["GS1", "GS2", "GS3"], key=f"{label_prefix}_type")
            is_24h = st.radio(f"{label_prefix} 24시간 영업", ["Y", "N"], key=f"{label_prefix}_24h", horizontal=True)
            sales = st.number_input(f"{label_prefix} 일매출 (천원)", value=1500, step=10, key=f"{label_prefix}_sales")
            margin = st.slider(f"{label_prefix} 매익률 (%)", 20.0, 45.0, 30.0, step=0.1, key=f"{label_prefix}_margin")
        
        # GS2 전용 입력창 (선택 시에만 등장)
        lease_dep, sub_dep, premium, rent = 0, 0, 0, 0
        if u_type == "GS2":
            st.markdown(f'<div class="gs2-box"><b>🏢 GS2 임차 조건 (천원)</b>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            lease_dep = c1.number_input(f"{label_prefix} 임차보증금", value=0, key=f"{label_prefix}_ld")
            sub_dep = c2.number_input(f"{label_prefix} 전대보증금", value=0, key=f"{label_prefix}_sd")
            premium = c1.number_input(f"{label_prefix} 권리금", value=0, key=f"{label_prefix}_pr")
            rent = c2.number_input(f"{label_prefix} 월 임차료", value=0, key=f"{label_prefix}_rt")
            st.markdown('</div>', unsafe_allow_html=True)
        
        # 세부 지원금 입력창
        st.markdown(f'<div class="support-box"><b>💰 세부 지원금 및 인센티브</b>', unsafe_allow_html=True)
        s1, s2 = st.columns(2)
        sup_fix = s1.number_input(f"{label_prefix} 정액지원금 (천원)", value=150, key=f"{label_prefix}_sf")
        sup_rate = s2.number_input(f"{label_prefix} 정률지원금 (%)", value=0.0, step=0.1, key=f"{label_prefix}_sr")
        order_inc = s1.number_input(f"{label_prefix} 발주장려금 (천원)", value=30, key=f"{label_prefix}_oi")
        st.markdown('</div>', unsafe_allow_html=True)

        return {
            "type": u_type, "24h": is_24h, "sales": sales, "margin": margin,
            "lease_dep": lease_dep, "sub_dep": sub_dep, "premium": premium, "rent": rent,
            "sup_fix": sup_fix, "sup_rate": sup_rate, "order_inc": order_inc
        }

    # 2. 메인 화면 - 좌우 비교 레이아웃
    left_col, right_col = st.columns(2)
    with left_col:
        cur_data = input_section("현재")
    with right_col:
        tar_data = input_section("목표")

    # 3. 계산 로직 (수식 적용)
    def calculate_logic(data):
        # 월 매출 및 이익 계산
        m_sales = data["sales"] * 30.41
        m_profit = m_sales * (data["margin"] / 100)
        
        # 타입별 기본 배분율 (24시간 여부 적용)
        royalty_map = {
            "GS1": {"Y": 0.71, "N": 0.66},
            "GS2": {"Y": 0.65, "N": 0.60},
            "GS3": {"Y": 0.46, "N": 0.41}
        }
        r_rate = royalty_map[data["type"]][data["24h"]]
        owner_share = m_profit * r_rate
        
        # 지원금 합계 = (이익 * 정률%) + 정액 + 발주장려금
        total_support = (m_profit * (data["sup_rate"] / 100)) + data["sup_fix"] + data["order_inc"]
        
        # 최종 정산금 = 배분금 + 지원금 - 임차료
        final_income = owner_share + total_support - data["rent"]
        
        return {
            "m_sales": m_sales, "owner_share": owner_share, 
            "total_support": total_support, "final_income": final_income
        }

    cur_res = calculate_logic(cur_data)
    tar_res = calculate_logic(tar_data)
    diff = tar_res["final_income"] - cur_res["final_income"]

    # 4. 결과 리포트
    st.write("---")
    st.subheader("📊 시뮬레이션 결과 리포트")
    
    m1, m2, m3 = st.columns(3)
    m1.metric("현재 월 정산금", f"{int(cur_res['final_income']):,}원")
    m2.metric("목표 월 정산금", f"{int(tar_res['final_income']):,}원", delta=f"{int(diff):,}원")
    m3.metric("수익 개선율", f"{round((diff/cur_res['final_income'])*100, 1) if cur_res['final_income'] != 0 else 0}%")

    # 상세 데이터 테이블
    st.write("### 📑 상세 비교 테이블")
    comparison_df = pd.DataFrame({
        "항목": ["가맹 타입", "24시간 영업", "매익률", "발주장려금", "지원금(정액)", "지원금(정률)", "임차보증금", "권리금", "임차료", "최종 월 수익"],
        "현재": [cur_data["type"], cur_data["24h"], f"{cur_data['margin']}%", f"{cur_data['order_inc']:,}원", f"{cur_data['sup_fix']:,}원", f"{cur_data['sup_rate']}%", f"{cur_data['lease_dep']:,}원", f"{cur_data['premium']:,}원", f"-{cur_data['rent']:,}원", f"**{int(cur_res['final_income']):,}원**"],
        "목표": [tar_data["type"], tar_data["24h"], f"{tar_data['margin']}%", f"{tar_data['order_inc']:,}원", f"{tar_data['sup_fix']:,}원", f"{tar_data['sup_rate']}%", f"{tar_data['lease_dep']:,}원", f"{tar_data['premium']:,}원", f"-{tar_data['rent']:,}원", f"**{int(tar_res['final_income']):,}원**"]
    })
    st.table(comparison_df)

    st.success(f"✅ 코칭 결과: 목표 달성 시 월 **{int(diff):,}원**의 수익 증대가 예상됩니다.")
