import streamlit as st
import pandas as pd
import altair as alt

# 1. 페이지 설정 및 모바일 최적화 레이아웃
st.set_page_config(page_title="GS25 수익 코칭 대시보드", layout="centered")

# 비밀번호 설정
PW = "gs25"

def check_password():
    if "password" not in st.session_state: st.session_state["password"] = ""
    if st.session_state["password"] == PW: return True
    st.title("🔐 임직원 인증")
    pwd = st.text_input("비밀번호를 입력하세요", type="password")
    if st.button("접속하기"):
        if pwd == PW:
            st.session_state["password"] = pwd
            st.rerun()
        else: st.error("비밀번호가 틀렸습니다.")
    return False

if check_password():
    # CSS: 모바일 텍스트 겹침 방지 및 테이블 가독성 극대화
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
        * { font-family: 'Noto Sans KR', sans-serif !important; }
        
        /* 메트릭 폰트 크기 조정 (모바일 겹침 방지) */
        [data-testid="stMetricValue"] { font-size: 1.5rem !important; color: #007aff; }
        [data-testid="stMetricLabel"] { font-size: 0.8rem !important; }
        
        /* 테이블 스타일 */
        .stTable td { font-size: 12px !important; padding: 4px !important; }
        .stTable th { font-size: 12px !important; background-color: #f1f3f5; }
        
        /* 섹션 구분선 */
        .section-hr { border: none; border-top: 2px solid #007aff; margin: 20px 0; }
        </style>
        """, unsafe_allow_html=True)

    st.title("📊 GS25 수익 코칭 시뮬레이터")
    st.caption("안삿별님 전용 - 엑셀 수식(공제항목 포함) 정밀 동기화 버전")

    # 2. 정밀 계산 로직 (LaTeX 수식)
    # $$정산금 = (매출이익 \times 배분율) + O4O수익 + 지원금 - 운영비 - 임차료$$

    def calculate_settlement(d):
        m_sales = d["sales"] * 30.41 # 엑셀 기준 월 일수
        m_profit = m_sales * (d["margin"] / 100)
        
        # 타입별 배분율
        royalty_map = {"GS1":{"Y":0.71, "N":0.66}, "GS2":{"Y":0.65, "N":0.60}, "GS3":{"Y":0.46, "N":0.41}}
        r_rate = royalty_map[d["type"]][d["24h"]]
        
        owner_share = m_profit * r_rate
        o4o_profit = (d["d_sales"] * 0.16) + (d["p_sales"] * 0.23) # O4O 수익 분리
        support = (m_profit * (d["s_rate"]/100)) + d["s_fix"] + d["order"]
        
        # 최종 정산금 = 배분금 + O4O + 지원금 - 운영비(엑셀 공제항목) - 임차료
        total = owner_share + o4o_profit + support - d["exp"] - d["rent"]
        return {"m_sales": m_sales, "m_profit": m_profit, "share": owner_share, "o4o": o4o_profit, "total": total}

    # 3. 입력 섹션 (모바일 1단 구성)
    def get_user_input(label):
        st.subheader(f"📍 {label} 데이터 입력")
        with st.container():
            u_type = st.selectbox(f"{label} 타입", ["GS1", "GS2", "GS3"], key=f"{label}_t")
            u_24h = st.radio(f"{label} 24시간 여부", ["Y", "N"], horizontal=True, key=f"{label}_24")
            
            c1, c2 = st.columns(2)
            u_sales = c1.number_input(f"{label} 일매출", value=1500 if label=="기존" else 1600, key=f"{label}_s")
            u_margin = c2.number_input(f"{label} 매익률(%)", value=30.0, step=0.1, key=f"{label}_m")
            
            with st.expander(f"➕ {label} 세부 설정 (O4O/지원금/운영비)"):
                st.markdown("**🛵 O4O 매출액 (천원)**")
                o1, o2 = st.columns(2)
                d_sales = o1.number_input(f"{label} 배달매출", value=0, key=f"{label}_d")
                p_sales = o2.number_input(f"{label} 픽업매출", value=0, key=f"{label}_p")
                
                st.markdown("**💰 지원금 및 운영비 (천원)**")
                s1, s2 = st.columns(2)
                s_fix = s1.number_input(f"{label} 정액지원합계", value=180, key=f"{label}_sf")
                s_rate = s2.number_input(f"{label} 정률지원(%)", value=0.0, step=0.1, key=f"{label}_sr")
                u_order = s1.number_input(f"{label} 발주장려금", value=30, key=f"{label}_oi")
                # 엑셀과의 차이를 해결하는 핵심 항목: 점포 운영비(공제항목)
                u_exp = s2.number_input(f"{label} 점포 운영비(공제)", value=1834, key=f"{label}_ex") 
                
                u_rent = 0
                if u_type == "GS2":
                    u_rent = st.number_input(f"{label} 월세(임차료)", value=0, key=f"{label}_rt")
            
            return {
                "type": u_type, "24h": u_24h, "sales": u_sales, "margin": u_margin,
                "d_sales": d_sales, "p_sales": p_sales, "s_fix": s_fix, "s_rate": s_rate,
                "order": u_order, "exp": u_exp, "rent": u_rent
            }

    # 현재 vs 목표 데이터 받기
    cur = get_user_input("기존")
    st.markdown('<div class="section-hr"></div>', unsafe_allow_html=True)
    tar = get_user_input("변경")

    # 계산 결과
    res_c = calculate_settlement(cur)
    res_t = calculate_settlement(tar)
    diff = res_t["total"] - res_c["total"]

    # 4. 결과 리포트
    st.divider()
    st.subheader("💰 수익 코칭 리포트")
    col_a, col_b = st.columns(2)
    col_a.metric("기존 월 수익", f"{int(res_c['total']):,}원")
    col_b.metric("변경 월 수익", f"{int(res_t['total']):,}원", delta=f"{int(diff):,}원")

    # 5. 상세 비교 테이블 (엑셀 항목 동기화)
    st.subheader("📑 상세 분석 데이터 (천원 단위)")
    
    analysis_df = pd.DataFrame({
        "항목": ["가맹 타입", "영업 시간", "일평균 매출", "매익률 (%)", "O4O 추가수익", "본부 지원금", "점포 운영비(-)", "임차료(-)", "최종 월 정산금"],
        "기존(A)": [cur["type"], f"{cur['24h']}H", f"{cur['sales']:,}", f"{cur['margin']}%", f"{int(res_c['o4o']):,}", f"{int(res_c['support']):,}", f"-{cur['exp']:,}", f"-{cur['rent']:,}", f"**{int(res_c['total']):,}**"],
        "변경(B)": [tar["type"], f"{tar['24h']}H", f"{tar['sales']:,}", f"{tar['margin']}%", f"{int(res_t['o4o']):,}", f"{int(res_t['support']):,}", f"-{tar['exp']:,}", f"-{tar['rent']:,}", f"**{int(res_t['total']):,}**"],
        "증감(B-A)": ["-", "-", f"{tar['sales']-cur['sales']:,}", "-", f"{int(res_t['o4o']-res_c['o4o']):,}", f"{int(res_t['support']-res_c['support']):,}", f"{int(-(tar['exp']-cur['exp'])):,}", f"{int(-(tar['rent']-cur['rent'])):,}", f"**{int(diff):,}**"]
    })
    st.table(analysis_df)
    
    st.info(f"✅ 코칭 결과: 일매출 {tar['sales']-cur['sales']:,}원 증대 시, 월 {int(diff):,}원의 추가 수익이 발생합니다.")
