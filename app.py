import streamlit as st
import pandas as pd

# -----------------------------
# 0) Page
# -----------------------------
st.set_page_config(page_title="GS25 수익 시뮬레이터", layout="centered")

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


# -----------------------------
# 1) Mobile-safe CSS
# -----------------------------
MOBILE_CSS = """
<style>
/* Font: 깨짐 최소화 */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700&display=swap');
html, body, [class*="css"]  { font-family: "Noto Sans KR", system-ui, -apple-system, Segoe UI, Roboto, sans-serif !important; }

/* 제목/설명 줄간격 */
h1, h2, h3 { line-height: 1.2; }
p, div { line-height: 1.35; }

/* Streamlit 기본 padding 모바일 최적화 */
.block-container { padding-top: 1.2rem; padding-bottom: 1.2rem; }

/* "column" 가로배치가 모바일에서 겹치는 문제 방지: 세로 스택 */
@media (max-width: 768px) {
  [data-testid="stHorizontalBlock"] {
    flex-wrap: wrap !important;
    gap: 0.75rem !important;
  }
  [data-testid="stHorizontalBlock"] [data-testid="column"] {
    width: 100% !important;
    flex: 1 1 100% !important;
    min-width: 100% !important;
  }
}

/* metric 글자 크기 */
[data-testid="stMetricValue"] { font-size: 1.55rem !important; }
[data-testid="stMetricLabel"] { font-size: 0.95rem !important; }

/* dataframe 가로 스크롤 허용 (모바일에서 표 깨짐 방지) */
[data-testid="stDataFrame"] { overflow-x: auto !important; }

/* 입력 라벨 과밀 방지 */
label { white-space: normal !important; }

/* GS2 박스 */
.gs2-box {
  background: #f6f9ff;
  border: 1px solid #2f6fed;
  border-radius: 10px;
  padding: 12px;
  margin-top: 8px;
}
.small-muted { color: #6b7280; font-size: 12px; }
</style>
"""

# -----------------------------
# 2) Excel-aligned constants
#    (from uploaded workbook: 손익계산서 리포트 디자인_VER4(O4O).xlsx)
# -----------------------------
DAYS_PER_MONTH = 30.4  # 엑셀과 동일

BASE_RATE = {  # P3,P4,P5
    "GS1": 0.66,
    "GS2": 0.60,
    "GS3": 0.41
}

O4O_RATE = {  # L4,M4
    "배달": 0.16,
    "픽업": 0.23
}

# "영업장려금 外" 평균값 (천원) - 엑셀 시트 참조값
EXTRA_SUPPORT = {
    "GS1": 184.02818221665626,
    "GS2": 205.8701484450923,
    "GS3": 240.4150872507123
}

# 영업비 평균값(천원) - 엑셀 시트 참조값
EXPENSE_AVG = {
    "통신비":     {"GS1": 2.359598361511167,  "GS2": 0.8473468577907353, "GS3": 2.187551282051282},
    "수도광열비": {"GS1": 603.3870146629097,  "GS2": 725.9067742954325, "GS3": 707.027876068376},
    "세금과공과": {"GS1": 9.479086307660197,  "GS2": 10.454355118237773, "GS3": 10.50099715099715},
    "수선비":     {"GS1": 37.77716917136298,  "GS2": 23.58131843213476, "GS3": 22.23017841880342},
    "보험료":     {"GS1": 6.654556407848048,  "GS2": 6.214191367023, "GS3": 6.020477207977208},
    "지급수수료": {"GS1": 261.4183783135045,  "GS2": 292.0885963718821, "GS3": 309.96728810541316},
    "소모품비":   {"GS1": 9.64304936338969,   "GS2": 1.7912170391966311, "GS3": 3.7024309116809113},
    "재고감모손": {"GS1": 859.4883496660406,  "GS2": 865.158667638484, "GS3": 843.2516136039886},
    "잡비":       {"GS1": 14.206635462325192, "GS2": 8.821619371558146, "GS3": 17.877725427350427},
}

EXPENSE_ITEMS_ORDER = ["통신비","수도광열비","세금과공과","수선비","보험료","지급수수료","소모품비","재고감모손","잡비"]


# -----------------------------
# 3) Excel-aligned calculation
# -----------------------------
def calc_excel_like(d: dict) -> dict:
    """
    모든 금액 단위: '천원'
    d["sales_daily"]: 일매출(천원)
    d["margin_pct"]: 매익률(%)
    d["order_incentive"]: 발주장려금(천원)  # 엑셀 D12
    d["support_rate_pct"]: 지원금(정율)(%)  # 엑셀 G12 (비율)
    d["support_fixed"]: 지원금(정액)(천원)  # 엑셀 G13
    d["o4o_delivery"], d["o4o_pickup"]: 주문금액(천원)  # 엑셀 U8/V8 또는 W8/X8
    GS2 임차정보(천원): ldep, sdep, prem, rent
    """

    t = d["type"]
    is24 = (d["is24"] == "Y")

    # 1) 월매출 / 점포 매출총이익(점포분)
    m_sales = d["sales_daily"] * DAYS_PER_MONTH
    store_gp = m_sales * (d["margin_pct"] / 100.0)

    # 2) O4O 수익(엑셀은 주문금액 그대로에 수익률 적용, 월환산 없음)
    o4o_profit = d["o4o_delivery"] * O4O_RATE["배달"] + d["o4o_pickup"] * O4O_RATE["픽업"]

    # 3) 발주장려금
    order_inc = d["order_incentive"]

    # 4) 매출총이익(엑셀: 점포GP + 발주장려금 + O4O수익)
    total_gp = store_gp + order_inc + o4o_profit

    # 5) 가맹수수료율(기본) 및 발주장려금에만 추가율(24h 5% + 정율지원금)
    base_rate = BASE_RATE[t]
    support_rate = d["support_rate_pct"] / 100.0
    inc_rate = base_rate + (0.05 if is24 else 0.0) + support_rate

    # 6) 경영주 수입(엑셀: (매출총이익-발주장려금)*기본 + 발주장려금*추가율)
    owner_income = (total_gp - order_inc) * base_rate + order_inc * inc_rate

    # 7) 본부지원금(엑셀 row23 + row24)
    #   - 정율: store_gp * support_rate
    #   - 24h 추가: store_gp * 5%
    #   - 정액: support_fixed
    #   - 영업장려금 外: 타입별 평균(EXTRA_SUPPORT)
    support_total = store_gp * support_rate + (store_gp * 0.05 if is24 else 0.0) + d["support_fixed"] + EXTRA_SUPPORT[t]

    # 8) 영업비(타입별 평균) + GS2 본부임차료(전대료) 산식
    expense_detail = {k: EXPENSE_AVG[k][t] for k in EXPENSE_ITEMS_ORDER}
    expense_base = sum(expense_detail.values())

    # GS2 전대료(엑셀 계산기!E36 산식)
    # if 24h:
    #   ((임차보증금+권리금)*65% - 전대보증금)*6%/12 + 임차료*65%
    # else:
    #   ((임차보증금+권리금)*60% - 전대보증금)*6%/12 + 임차료*60%
    lease_cost = 0.0
    if t == "GS2":
        ldep = d.get("ldep", 0.0)
        sdep = d.get("sdep", 0.0)
        prem = d.get("prem", 0.0)
        rent = d.get("rent", 0.0)

        ratio = 0.65 if is24 else 0.60
        lease_cost = (((ldep + prem) * ratio - sdep) * 0.06 / 12.0) + (rent * ratio)

    total_expense = expense_base + lease_cost

    # 9) 예상 정산금(영업이익) = 경영주총수입(경영주수입+본부지원금) - 영업비
    owner_total_income = owner_income + support_total
    settlement = owner_total_income - total_expense

    return {
        "m_sales": m_sales,
        "store_gp": store_gp,
        "o4o_profit": o4o_profit,
        "order_inc": order_inc,
        "total_gp": total_gp,
        "base_rate": base_rate,
        "inc_rate": inc_rate,
        "owner_income": owner_income,
        "support_total": support_total,
        "extra_support": EXTRA_SUPPORT[t],
        "expense_base": expense_base,
        "lease_cost": lease_cost,
        "total_expense": total_expense,
        "owner_total_income": owner_total_income,
        "settlement": settlement,
        "expense_detail": expense_detail
    }


# -----------------------------
# 4) UI Input
# -----------------------------
def input_block(prefix: str, default_daily_sales: int):
    st.subheader(f"📋 {prefix} 입력 (단위: 천원)")
    t = st.selectbox(f"{prefix} 가맹타입", ["GS1", "GS2", "GS3"], key=f"{prefix}_type")
    is24 = st.radio(f"{prefix} 24시간 영업", ["Y", "N"], horizontal=True, key=f"{prefix}_24")

    sales_daily = st.number_input(f"{prefix} 일매출", min_value=0.0, value=float(default_daily_sales), step=10.0, key=f"{prefix}_sales")
    margin_pct = st.number_input(f"{prefix} 매익률(%)", min_value=0.0, max_value=100.0, value=30.0, step=0.1, key=f"{prefix}_margin")

    # 발주장려금 / 지원금(정율, 정액)
    with st.expander(f"➕ {prefix} 지원금 / 발주 / O4O", expanded=True):
        c1, c2 = st.columns(2)
        order_incentive = c1.number_input(f"{prefix} 발주장려금", min_value=0.0, value=0.0, step=10.0, key=f"{prefix}_order")

        support_rate_pct = c2.number_input(
            f"{prefix} 지원금(정율, %)",
            min_value=0.0, max_value=100.0, value=0.0, step=0.1, key=f"{prefix}_sr"
        )
        support_fixed = c1.number_input(f"{prefix} 지원금(정액)", min_value=0.0, value=0.0, step=10.0, key=f"{prefix}_sf")

        o4o_delivery = c1.number_input(f"{prefix} 배달 주문금액", min_value=0.0, value=0.0, step=10.0, key=f"{prefix}_d")
        o4o_pickup   = c2.number_input(f"{prefix} 픽업 주문금액", min_value=0.0, value=0.0, step=10.0, key=f"{prefix}_p")

        st.caption("※ O4O는 엑셀과 동일하게 ‘주문금액(천원)’에 수익률(배달 16% / 픽업 23%)을 곱해 반영합니다(월환산 없음).")

    # GS2 임차조건
    ldep = sdep = prem = rent = 0.0
    if t == "GS2":
        st.markdown('<div class="gs2-box"><b>🏢 GS2 임차조건(본부임차) 입력</b><div class="small-muted">엑셀 전대료 산식과 동일 반영</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        ldep = c1.number_input(f"{prefix} 임차보증금", min_value=0.0, value=0.0, step=100.0, key=f"{prefix}_ldep")
        sdep = c2.number_input(f"{prefix} 전대보증금", min_value=0.0, value=0.0, step=100.0, key=f"{prefix}_sdep")
        prem = c1.number_input(f"{prefix} 권리금",   min_value=0.0, value=0.0, step=100.0, key=f"{prefix}_prem")
        rent = c2.number_input(f"{prefix} 월 임차료", min_value=0.0, value=0.0, step=10.0,  key=f"{prefix}_rent")
        st.markdown("</div>", unsafe_allow_html=True)

    return {
        "type": t,
        "is24": is24,
        "sales_daily": sales_daily,
        "margin_pct": margin_pct,
        "order_incentive": order_incentive,
        "support_rate_pct": support_rate_pct,
        "support_fixed": support_fixed,
        "o4o_delivery": o4o_delivery,
        "o4o_pickup": o4o_pickup,
        "ldep": ldep, "sdep": sdep, "prem": prem, "rent": rent,
    }


# -----------------------------
# 5) Main
# -----------------------------
if check_password():
    st.markdown(MOBILE_CSS, unsafe_allow_html=True)

    st.title("📊 GS25 수익 시뮬레이터 (엑셀 동일 로직)")
    st.caption("단위: 천원  |  엑셀 샘플(VER4 O4O) 산식 기준으로 일치하도록 구현")

    # 입력: 모바일에서도 보기 좋게 (CSS로 자동 세로 스택)
    col1, col2 = st.columns(2)
    with col1:
        cur = input_block("기존", default_daily_sales=1500)
    with col2:
        tar = input_block("변경", default_daily_sales=1600)

    res_c = calc_excel_like(cur)
    res_t = calc_excel_like(tar)
    diff = res_t["settlement"] - res_c["settlement"]

    st.divider()
    st.subheader("💰 결과 요약 (예상 정산금/영업이익)")
    st.metric("기존 예상 정산금", f"{int(res_c['settlement']):,} 천원")
    st.metric("변경 예상 정산금", f"{int(res_t['settlement']):,} 천원", delta=f"{int(diff):,} 천원")

    st.divider()
    st.subheader("📑 상세 비교 (엑셀 항목 구조 기반)")

    def row(label, a, b, fmt="num"):
        if fmt == "num":
            return [label, f"{int(a):,}", f"{int(b):,}", f"{int(b-a):,}"]
        if fmt == "pct":
            return [label, f"{a*100:.1f}%", f"{b*100:.1f}%", f"{(b-a)*100:.1f}%p"]
        return [label, str(a), str(b), "-"]

    rows = []
    rows.append(row("월매출액(=일매출*30.4)", res_c["m_sales"], res_t["m_sales"]))
    rows.append(row("점포 매출총이익(점포분)", res_c["store_gp"], res_t["store_gp"]))
    rows.append(row("O4O 수익(배달16%+픽업23%)", res_c["o4o_profit"], res_t["o4o_profit"]))
    rows.append(row("발주장려금", res_c["order_inc"], res_t["order_inc"]))
    rows.append(row("매출총이익(합계)", res_c["total_gp"], res_t["total_gp"]))

    rows.append(row("기본 수수료율", res_c["base_rate"], res_t["base_rate"], fmt="pct"))
    rows.append(row("발주장려금 적용 수수료율(기본+24H+정율)", res_c["inc_rate"], res_t["inc_rate"], fmt="pct"))

    rows.append(row("경영주 수입(가맹수수료 배분)", res_c["owner_income"], res_t["owner_income"]))
    rows.append(row("본부지원금(정율+24H+정액+외)", res_c["support_total"], res_t["support_total"]))
    rows.append(row("경영주 총수입(경영주수입+지원금)", res_c["owner_total_income"], res_t["owner_total_income"]))
    rows.append(row("영업비(타입 평균)", res_c["expense_base"], res_t["expense_base"]))
    rows.append(row("GS2 전대료(해당 시)", res_c["lease_cost"], res_t["lease_cost"]))
    rows.append(row("총 영업비", res_c["total_expense"], res_t["total_expense"]))
    rows.append(row("예상 정산금(영업이익)", res_c["settlement"], res_t["settlement"]))

    df = pd.DataFrame(rows, columns=["항목", "기존", "변경", "증감"])
    st.dataframe(df, use_container_width=True, hide_index=True)

    if diff >= 0:
        st.success(f"✅ 코칭 결과: 월 {int(diff):,} 천원의 추가 수익이 예상됩니다.")
    else:
        st.warning(f"⚠️ 코칭 결과: 월 {abs(int(diff)):,} 천원 수익 감소가 예상됩니다.")

    with st.expander("🔎 (참고) 영업비 상세(타입 평균값)", expanded=False):
        exp_rows = []
        for k in EXPENSE_ITEMS_ORDER:
            exp_rows.append([k, f"{res_c['expense_detail'][k]:,.2f}", f"{res_t['expense_detail'][k]:,.2f}"])
        st.dataframe(pd.DataFrame(exp_rows, columns=["항목", "기존(천원)", "변경(천원)"]), use_container_width=True, hide_index=True)
