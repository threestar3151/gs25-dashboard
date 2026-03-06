import streamlit as st
import pandas as pd

# -----------------------------
# 0) Page
# -----------------------------
st.set_page_config(page_title="GS25 수익 시뮬레이터", layout="centered")

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


# -----------------------------
# 1) Mobile-safe CSS
# -----------------------------
MOBILE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;600;700&display=swap');

html, body, [class*="css"]  {
    font-family: "Noto Sans KR", system-ui, -apple-system, Segoe UI, Roboto, sans-serif !important;
}

h1, h2, h3 {
    line-height: 1.2;
    word-break: keep-all;
}

p, div, label, span {
    line-height: 1.4;
    word-break: keep-all;
}

.block-container {
    padding-top: 1rem;
    padding-bottom: 1.2rem;
    max-width: 760px;
}

/* 모바일에서 컬럼 세로 정렬 */
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

/* metric 크기 */
[data-testid="stMetricLabel"] {
    font-size: 0.95rem !important;
}
[data-testid="stMetricValue"] {
    font-size: 1.9rem !important;
    line-height: 1.15 !important;
}
[data-testid="stMetricDelta"] {
    font-size: 0.95rem !important;
}

/* 표 가로스크롤 */
[data-testid="stDataFrame"] {
    overflow-x: auto !important;
}

/* 입력 라벨 줄바꿈 */
label {
    white-space: normal !important;
}

/* GS2 박스 */
.gs2-box {
    background: #f6f9ff;
    border: 1px solid #2f6fed;
    border-radius: 10px;
    padding: 12px;
    margin-top: 8px;
}
.small-muted {
    color: #6b7280;
    font-size: 12px;
}

/* 결과 카드 */
.result-card {
    background: #f8fafc;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 14px 16px;
    margin-bottom: 10px;
}
.result-title {
    font-size: 0.92rem;
    color: #475569;
    margin-bottom: 6px;
}
.result-value {
    font-size: 1.8rem;
    font-weight: 700;
    color: #0f172a;
    line-height: 1.2;
}
.result-sub {
    font-size: 0.92rem;
    color: #16a34a;
    margin-top: 6px;
    font-weight: 600;
}
.result-sub.minus {
    color: #dc2626;
}
</style>
"""

# -----------------------------
# 2) Excel-aligned constants
# -----------------------------
DAYS_PER_MONTH = 30.4

BASE_RATE = {
    "GS1": 0.66,
    "GS2": 0.60,
    "GS3": 0.41
}

O4O_RATE = {
    "배달": 0.16,
    "픽업": 0.23
}

EXTRA_SUPPORT = {
    "GS1": 184.02818221665626,
    "GS2": 205.8701484450923,
    "GS3": 240.4150872507123
}

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
    t = d["type"]
    is24 = (d["is24"] == "Y")

    m_sales = d["sales_daily"] * DAYS_PER_MONTH
    store_gp = m_sales * (d["margin_pct"] / 100.0)

    delivery_profit = d["o4o_delivery"] * O4O_RATE["배달"]
    pickup_profit = d["o4o_pickup"] * O4O_RATE["픽업"]
    o4o_profit = delivery_profit + pickup_profit

    order_inc = d["order_incentive"]
    total_gp = store_gp + order_inc + o4o_profit

    base_rate = BASE_RATE[t]
    support_rate = d["support_rate_pct"] / 100.0
    inc_rate = base_rate + (0.05 if is24 else 0.0) + support_rate

    owner_income = (total_gp - order_inc) * base_rate + order_inc * inc_rate

    support_total = (
        store_gp * support_rate
        + (store_gp * 0.05 if is24 else 0.0)
        + d["support_fixed"]
        + EXTRA_SUPPORT[t]
    )

    expense_detail = {k: EXPENSE_AVG[k][t] for k in EXPENSE_ITEMS_ORDER}
    expense_base = sum(expense_detail.values())

    lease_cost = 0.0
    if t == "GS2":
        ldep = d.get("ldep", 0.0)
        sdep = d.get("sdep", 0.0)
        prem = d.get("prem", 0.0)
        rent = d.get("rent", 0.0)

        ratio = 0.65 if is24 else 0.60
        lease_cost = (((ldep + prem) * ratio - sdep) * 0.06 / 12.0) + (rent * ratio)

    total_expense = expense_base + lease_cost
    owner_total_income = owner_income + support_total
    settlement = owner_total_income - total_expense

    return {
        "m_sales": m_sales,
        "store_gp": store_gp,
        "delivery_profit": delivery_profit,
        "pickup_profit": pickup_profit,
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

    sales_daily = st.number_input(
        f"{prefix} 일매출",
        min_value=0.0,
        value=float(default_daily_sales),
        step=10.0,
        key=f"{prefix}_sales"
    )
    margin_pct = st.number_input(
        f"{prefix} 매익률(%)",
        min_value=0.0,
        max_value=100.0,
        value=30.0,
        step=0.1,
        key=f"{prefix}_margin"
    )

    with st.expander(f"➕ {prefix} 지원금 / 발주 / O4O", expanded=True):
        c1, c2 = st.columns(2)

        order_incentive = c1.number_input(
            f"{prefix} 발주장려금",
            min_value=0.0,
            value=0.0,
            step=10.0,
            key=f"{prefix}_order"
        )

        support_rate_pct = c2.number_input(
            f"{prefix} 지원금(정율, %)",
            min_value=0.0,
            max_value=100.0,
            value=0.0,
            step=0.1,
            key=f"{prefix}_sr"
        )

        support_fixed = c1.number_input(
            f"{prefix} 지원금(정액)",
            min_value=0.0,
            value=0.0,
            step=10.0,
            key=f"{prefix}_sf"
        )

        o4o_pickup = c2.number_input(
            f"{prefix} 픽업 주문금액",
            min_value=0.0,
            value=0.0,
            step=10.0,
            key=f"{prefix}_p"
        )

        o4o_delivery = c1.number_input(
            f"{prefix} 배달 주문금액",
            min_value=0.0,
            value=0.0,
            step=10.0,
            key=f"{prefix}_d"
        )

    ldep = sdep = prem = rent = 0.0
    if t == "GS2":
        st.markdown(
            '<div class="gs2-box"><b>🏢 GS2 임차조건(본부임차) 입력</b><div class="small-muted">엑셀 전대료 산식과 동일 반영</div>',
            unsafe_allow_html=True
        )
        c1, c2 = st.columns(2)
        ldep = c1.number_input(f"{prefix} 임차보증금", min_value=0.0, value=0.0, step=100.0, key=f"{prefix}_ldep")
        sdep = c2.number_input(f"{prefix} 전대보증금", min_value=0.0, value=0.0, step=100.0, key=f"{prefix}_sdep")
        prem = c1.number_input(f"{prefix} 권리금", min_value=0.0, value=0.0, step=100.0, key=f"{prefix}_prem")
        rent = c2.number_input(f"{prefix} 월 임차료", min_value=0.0, value=0.0, step=10.0, key=f"{prefix}_rent")
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
        "ldep": ldep,
        "sdep": sdep,
        "prem": prem,
        "rent": rent,
    }


def render_result_card(title, value, delta=None):
    delta_html = ""
    if delta is not None:
        css_class = "result-sub" if delta >= 0 else "result-sub minus"
        arrow = "↑" if delta >= 0 else "↓"
        delta_html = f'<div class="{css_class}">{arrow} {abs(int(delta)):,} 천원</div>'

    st.markdown(
        f"""
        <div class="result-card">
            <div class="result-title">{title}</div>
            <div class="result-value">{int(value):,} 천원</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True
    )


# -----------------------------
# 5) Main
# -----------------------------
if check_password():
    st.markdown(MOBILE_CSS, unsafe_allow_html=True)

    st.title("📊 GS25 수익 시뮬레이터 (엑셀 동일 로직)")
    st.caption("단위: 천원")

    col1, col2 = st.columns(2)
    with col1:
        cur = input_block("기존", default_daily_sales=1500)
    with col2:
        tar = input_block("변경", default_daily_sales=1600)

    res_c = calc_excel_like(cur)
    res_t = calc_excel_like(tar)

    diff_total = res_t["settlement"] - res_c["settlement"]
    diff_o4o = res_t["o4o_profit"] - res_c["o4o_profit"]
    diff_delivery = res_t["delivery_profit"] - res_c["delivery_profit"]
    diff_pickup = res_t["pickup_profit"] - res_c["pickup_profit"]

    st.divider()
    st.subheader("💰 결과 요약 (예상 정산금/영업이익)")

    render_result_card("기존 예상 정산금", res_c["settlement"])
    render_result_card("변경 예상 정산금", res_t["settlement"], diff_total)

    st.subheader("🛵 O4O 수익 요약")
    render_result_card("기존 O4O 수익", res_c["o4o_profit"])
    render_result_card("변경 O4O 수익", res_t["o4o_profit"], diff_o4o)

    with st.expander("배달 / 픽업 수익 상세 보기", expanded=False):
        detail_rows = [
            ["기존 배달 수익", f"{int(res_c['delivery_profit']):,} 천원"],
            ["기존 픽업 수익", f"{int(res_c['pickup_profit']):,} 천원"],
            ["변경 배달 수익", f"{int(res_t['delivery_profit']):,} 천원"],
            ["변경 픽업 수익", f"{int(res_t['pickup_profit']):,} 천원"],
            ["배달 수익 증감", f"{int(diff_delivery):,} 천원"],
            ["픽업 수익 증감", f"{int(diff_pickup):,} 천원"],
        ]
        st.dataframe(
            pd.DataFrame(detail_rows, columns=["항목", "금액"]),
            use_container_width=True,
            hide_index=True
        )

    st.divider()
    st.subheader("📑 상세 비교")

    def row(label, a, b, fmt="num"):
        if fmt == "num":
            return [label, f"{int(a):,}", f"{int(b):,}", f"{int(b-a):,}"]
        if fmt == "pct":
            return [label, f"{a*100:.1f}%", f"{b*100:.1f}%", f"{(b-a)*100:.1f}%p"]
        return [label, str(a), str(b), "-"]

    rows = []
    rows.append(row("월매출액(=일매출×30.4)", res_c["m_sales"], res_t["m_sales"]))
    rows.append(row("점포 매출총이익(점포분)", res_c["store_gp"], res_t["store_gp"]))
    rows.append(row("배달 수익", res_c["delivery_profit"], res_t["delivery_profit"]))
    rows.append(row("픽업 수익", res_c["pickup_profit"], res_t["pickup_profit"]))
    rows.append(row("O4O 수익 합계", res_c["o4o_profit"], res_t["o4o_profit"]))
    rows.append(row("발주장려금", res_c["order_inc"], res_t["order_inc"]))
    rows.append(row("매출총이익(합계)", res_c["total_gp"], res_t["total_gp"]))
    rows.append(row("기본 수수료율", res_c["base_rate"], res_t["base_rate"], fmt="pct"))
    rows.append(row("발주장려금 적용 수수료율", res_c["inc_rate"], res_t["inc_rate"], fmt="pct"))
    rows.append(row("경영주 수입(가맹수수료 배분)", res_c["owner_income"], res_t["owner_income"]))
    rows.append(row("본부지원금(정율+24H+정액+외)", res_c["support_total"], res_t["support_total"]))
    rows.append(row("경영주 총수입", res_c["owner_total_income"], res_t["owner_total_income"]))
    rows.append(row("영업비(타입 평균)", res_c["expense_base"], res_t["expense_base"]))
    rows.append(row("GS2 전대료(해당 시)", res_c["lease_cost"], res_t["lease_cost"]))
    rows.append(row("총 영업비", res_c["total_expense"], res_t["total_expense"]))
    rows.append(row("예상 정산금(영업이익)", res_c["settlement"], res_t["settlement"]))

    df = pd.DataFrame(rows, columns=["항목", "기존", "변경", "증감"])
    st.dataframe(df, use_container_width=True, hide_index=True)

    if diff_total >= 0:
        st.success(f"✅ 코칭 결과: 월 {int(diff_total):,} 천원의 추가 수익이 예상됩니다.")
    else:
        st.warning(f"⚠️ 코칭 결과: 월 {abs(int(diff_total)):,} 천원 수익 감소가 예상됩니다.")

    with st.expander("🔎 영업비 상세(타입 평균값)", expanded=False):
        exp_rows = []
        for k in EXPENSE_ITEMS_ORDER:
            exp_rows.append([k, f"{res_c['expense_detail'][k]:,.2f}", f"{res_t['expense_detail'][k]:,.2f}"])
        st.dataframe(
            pd.DataFrame(exp_rows, columns=["항목", "기존(천원)", "변경(천원)"]),
            use_container_width=True,
            hide_index=True
        )
