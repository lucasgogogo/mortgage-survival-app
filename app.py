import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime, timedelta

# --- 页面基础设置 ---
st.set_page_config(page_title="BrokeDate V1.8.0", page_icon="🏠")

st.title("🏠 房贷生存全周期测试模型 (V1.8)")
st.markdown("**别只算月供，算算你能活多久**")
st.caption('核心精神：打破买房幻觉，通过揭示"破产日期"来建立真实的安全感。')

# --- 隐藏 number_input 的加减按钮（保留 help 问号） ---
st.markdown("""
<style>
    [data-testid="stNumberInput-StepUp"],
    [data-testid="stNumberInput-StepDown"],
    [data-testid="stNumberInput"] [data-testid="stBaseButton-stepUp"],
    [data-testid="stNumberInput"] [data-testid="stBaseButton-stepDown"],
    button.step-up, button.step-down {
        display: none !important;
    }
    [data-testid="stNumberInput"] div[data-baseweb="input"] {
        border-radius: 4px !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 🔒 隐私保证文案 ---
st.markdown("""
    <div style="background-color: #ecfdf5; border: 1px solid #10b981; padding: 15px; border-radius: 8px; color: #064e3b; margin: 20px 0;">
        <span style="font-size: 18px;">🔒 <strong>隐私绝对安全承诺</strong></span><br>
        <span style="font-size: 14px; opacity: 0.9;">
            我们<strong>绝不存储</strong>您的任何数据。所有计算均纯粹在您的本地浏览器中即时完成，没有任何人（包括我们）能看到您的财富真相。
            <br>关闭本页面后，所有输入数据将自动销毁。
        </span>
    </div>
""", unsafe_allow_html=True)

# --- 0. 核心算法 ---
def calc_cdn_mortgage(principal, annual_rate, years):
    """计算加拿大半年复利月供"""
    if principal <= 0 or years <= 0 or annual_rate <= 0: return 0
    semi_annual_rate = annual_rate / 100 / 2
    monthly_rate = (1 + semi_annual_rate) ** (2 / 12) - 1
    total_payments = years * 12
    payment = principal * (monthly_rate * (1 + monthly_rate) ** total_payments) / ((1 + monthly_rate) ** total_payments - 1)
    return int(payment)

def add_months(sourcedate, months):
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    return datetime(year, month, 1)

def get_duration_str(start, end):
    diff = end.year * 12 + end.month - (start.year * 12 + start.month)
    return f"{diff // 12} 年 {diff % 12} 个月"

# --- 联动回调：改谁就把值写入对方的 key ---
def _num_changed(k):
    st.session_state[f"{k}_sld"] = st.session_state[f"{k}_num"]

def _sld_changed(k):
    st.session_state[f"{k}_num"] = st.session_state[f"{k}_sld"]

# --- 联动输入组件：number_input + slider ---
def synced_input_int(label, key, min_val, max_val, step, help_text=None):
    if f"{key}_num" not in st.session_state:
        st.session_state[f"{key}_num"] = min_val
    if f"{key}_sld" not in st.session_state:
        st.session_state[f"{key}_sld"] = min_val
    st.sidebar.number_input(label, min_value=min_val, max_value=max_val, step=step,
                            key=f"{key}_num", help=help_text,
                            on_change=_num_changed, args=(key,))
    st.sidebar.slider(label, min_value=min_val, max_value=max_val, step=step,
                      key=f"{key}_sld", label_visibility="collapsed",
                      on_change=_sld_changed, args=(key,))
    return st.session_state[f"{key}_num"]

def synced_input_float(label, key, min_val, max_val, step, fmt="%.2f", help_text=None):
    if f"{key}_num" not in st.session_state:
        st.session_state[f"{key}_num"] = min_val
    if f"{key}_sld" not in st.session_state:
        st.session_state[f"{key}_sld"] = min_val
    st.sidebar.number_input(label, min_value=min_val, max_value=max_val, step=step, format=fmt,
                            key=f"{key}_num", help=help_text,
                            on_change=_num_changed, args=(key,))
    st.sidebar.slider(label, min_value=min_val, max_value=max_val, step=step,
                      key=f"{key}_sld", label_visibility="collapsed",
                      on_change=_sld_changed, args=(key,))
    return st.session_state[f"{key}_num"]

# --- 侧边栏：输入参数 ---
st.sidebar.header("1. 房子与贷款")

house_price = synced_input_int("房屋总价 ($)", "house_price", 0, 2000000, 5000)
down_payment = synced_input_int("首付金额 ($)", "down_payment", 0, 1000000, 5000)
rate_annual = synced_input_float("年利率 (%)", "rate_annual", 0.0, 10.0, 0.05,
                                  help_text="建议填入4%的近年平均利率")
amortization_years = st.sidebar.selectbox("贷款总年限", [25, 30], index=0)

# --- ✨ 侧边栏实时计算并显示月供 ---
sidebar_loan = max(0, house_price - down_payment)
sidebar_payment = calc_cdn_mortgage(sidebar_loan, rate_annual, amortization_years)

st.sidebar.markdown(f"""
<div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-top: 10px; border-left: 4px solid #e63946;">
    <small style="color: #666;">📉 贷款本金: ${sidebar_loan:,}</small><br>
    <span style="font-size: 16px; font-weight: bold;">👉 月供: </span>
    <span style="font-size: 20px; font-weight: 900; color: #e63946;">${sidebar_payment:,}</span>
</div>
""", unsafe_allow_html=True)

st.sidebar.header("2. 你的家底")

cash_now = synced_input_int("现有存款 ($)", "cash_now", 0, 1000000, 1000,
                             help_text="所有你现在能动用的流动资金，包括储蓄，可变现的股票等")
gic_amount = synced_input_int("未来大笔收入 ($)", "gic_amount", 0, 500000, 1000,
                               help_text="如定存到期，默认1年后转换成现有存款计入流动资金")

st.sidebar.header("3. 每月收支")

# 模拟开始日期：直接默认今天，不再显示输入
start_date = datetime(datetime.today().year, datetime.today().month, 1)

monthly_income = synced_input_int("当前家庭月纯收入 ($)", "monthly_income", 0, 20000, 100,
                                   help_text="扣去所有税费，养老等每个月纯到账的收入")
income_growth_rate = synced_input_float("预计年收入增长率 (%)", "income_growth", 0.0, 15.0, 0.5, "%.1f",
                                         help_text="建议3-5%的全国平均值，收入达到$5,700（曼省家庭税后中位线）后停止按此增长，之后仅按2%通胀率缓慢递增")
monthly_expense = synced_input_int("月生活支出 ($)", "monthly_expense", 0, 15000, 100,
                                    help_text="不含月供、房税和房屋保险。包括食品、交通、通讯、水电、娱乐等一切日常开销，曼省家庭参考值约$3,000-$3,500")
house_expense = synced_input_int("房税+房保险 /月 ($)", "house_expense", 0, 3000, 50)

st.sidebar.header("4. 提前还贷决策")
prepay_amount = synced_input_int("提前还贷金额 ($)", "prepay_amount", 0, 500000, 5000)

col_y, col_m = st.sidebar.columns(2)
with col_y:
    prepay_year = st.selectbox("还贷年份", range(start_date.year, start_date.year + 31), index=0)
with col_m:
    prepay_month = st.selectbox("还贷月份", range(1, 13), index=start_date.month - 1)

prepay_date = datetime(prepay_year, prepay_month, 1)
penalty = synced_input_int("提前还贷罚金 ($)", "penalty", 0, 50000, 500)


# --- 逻辑开关：只有输入了房价才开始推演 ---
if house_price > 0:
    # --- 开始推演 ---
    loan_balance = house_price - down_payment
    current_cash = cash_now - (house_price * 0.02) # 假设2%杂费
    initial_payment = calc_cdn_mortgage(loan_balance, rate_annual, amortization_years)
    current_monthly_payment = initial_payment

    initial_income_cap = 5700
    inflation_rate = 0.02

    active_monthly_income = monthly_income
    active_monthly_expense = monthly_expense
    active_house_expense = house_expense
    active_income_cap = initial_income_cap

    months_data = []
    payment_history = []
    prepay_note = None
    bankruptcy_date = None
    payoff_date = None

    phase_start_for_new = start_date

    for m in range(1, 601):
        this_month_date = add_months(start_date, m-1)

        # 每年更新 (通胀与收入)
        if m > 1 and (m - 1) % 12 == 0:
            active_monthly_expense *= (1 + inflation_rate)
            active_house_expense *= (1 + inflation_rate)
            active_income_cap *= (1 + inflation_rate)
            if active_monthly_income < active_income_cap:
                active_monthly_income *= (1 + income_growth_rate / 100)

        special_event_cash = 0
        # ✅ 改为第12个月（1年后）计入未来大笔收入
        if m == 12: special_event_cash += gic_amount

        # 提前还贷逻辑
        if this_month_date.year == prepay_date.year and this_month_date.month == prepay_date.month and prepay_amount > 0:
            special_event_cash -= (prepay_amount + penalty)
            loan_balance -= prepay_amount
            if loan_balance < 0: loan_balance = 0
            prepay_note = f"注：以下为 {this_month_date.strftime('%Y年%m月')} 提前还贷 ${prepay_amount:,} 后的月供变化"

        # 5年自动续约重算月供
        if m == 61:
            new_payment = calc_cdn_mortgage(loan_balance, rate_annual, amortization_years - 5)
            if new_payment != current_monthly_payment:
                payment_history.append({"start": start_date, "end": add_months(start_date, 59), "amount": current_monthly_payment})
                current_monthly_payment = new_payment
                phase_start_for_new = this_month_date
            else:
                phase_start_for_new = start_date
        elif m == 1:
            phase_start_for_new = start_date

        if loan_balance > 0:
            monthly_rate = (1 + (rate_annual/100/2))**(2/12) - 1
            interest_charge = loan_balance * monthly_rate
            principal_paid = current_monthly_payment - interest_charge
            loan_balance -= principal_paid

            if loan_balance <= 0:
                loan_balance = 0
                payoff_date = this_month_date
                payment_history.append({"start": phase_start_for_new, "end": this_month_date, "amount": current_monthly_payment})

        actual_pay = current_monthly_payment if loan_balance > 0 else 0
        monthly_net = active_monthly_income - active_monthly_expense - active_house_expense - actual_pay + special_event_cash
        current_cash += monthly_net

        total_expense = active_monthly_expense + active_house_expense + actual_pay
        months_data.append({
            "Date": this_month_date,
            "Cash": int(current_cash),
            "Loan": int(loan_balance),
            "ZeroLine": 0,
            "Income": int(active_monthly_income),
            "Expense": int(total_expense)
        })

        if current_cash < 0 and bankruptcy_date is None:
            bankruptcy_date = this_month_date

        if loan_balance <= 0 and m > 72 and (current_cash < 0 or m > 540):
            break

    df = pd.DataFrame(months_data)

    # --- 展示结果 ---
    st.subheader("🏁 全周期预测结论")
    c1, c2 = st.columns(2)
    with c1:
        if bankruptcy_date:
            st.error(f"💀 破产日期: {bankruptcy_date.strftime('%Y年%m月')}")
            st.write(f"预计还能坚持: **{get_duration_str(start_date, bankruptcy_date)}**")
        else:
            st.success("✅ 现金流安全")
    with c2:
        if payoff_date:
            st.info(f"🏠 结清日期: {payoff_date.strftime('%Y年%m月')}")

    st.markdown("---")
    st.subheader("📅 房贷月供阶段表")

    if len(payment_history) > 0:
        if len(payment_history) > 1 and prepay_note:
            p1 = payment_history[0]
            st.write(f"⏱ **{p1['start'].strftime('%Y年%m月')} - {p1['end'].strftime('%Y年%m月')}** ： 月供金额为 **${p1['amount']:,}**")
            st.caption(prepay_note)
            if len(payment_history) >= 2:
                p2 = payment_history[1]
                st.write(f"⏱ **{p2['start'].strftime('%Y年%m月')} - {p2['end'].strftime('%Y年%m月')}** ： 月供金额为 **${p2['amount']:,}**")
        else:
            for phase in payment_history:
                st.write(f"⏱ **{phase['start'].strftime('%Y年%m月')} - {phase['end'].strftime('%Y年%m月')}** ： 月供金额为 **${phase['amount']:,}**")
    else:
        st.write(f"⏱ **{start_date.strftime('%Y年%m月')} 开始** ： 当前月供为 **${current_monthly_payment:,}**")

    # --- 图表1：财富与债务曲线 ---
    st.markdown("### 📈 财富与债务曲线")
    st.line_chart(df.set_index("Date")[["Cash", "Loan", "ZeroLine"]], color=["#29b5e8", "#ff4b4b", "#000000"])

    # --- 图表2：月收支平衡表 ---
    st.markdown("### 💰 月收支平衡表")
    df_income_expense = df.melt(id_vars=["Date"], value_vars=["Income", "Expense"],
                                 var_name="类型", value_name="金额")
    ie_chart = alt.Chart(df_income_expense).mark_line(strokeWidth=2.5, interpolate="monotone").encode(
        x=alt.X("Date:T", title="日期"),
        y=alt.Y("金额:Q", title="月金额 ($)"),
        color=alt.Color("类型:N",
                         scale=alt.Scale(domain=["Income", "Expense"],
                                         range=["#22c55e", "#ef4444"]),
                         legend=alt.Legend(title="类型")),
    ).properties(height=300)
    st.altair_chart(ie_chart, use_container_width=True)

    st.caption(f"注：模型已自动计入每年 {inflation_rate*100}% 的生活成本通胀。月收入增长上限初始设为 ${initial_income_cap} (基于曼省平均月收入之 150%)，且该封顶值亦随通胀率逐年同步递增。")

else:
    # --- 欢迎页面 ---
    st.info("👋 欢迎使用 BrokeDate V1.8！*别只算月供，算算你能活多久* 请在左侧侧边栏输入您的房贷、资产及收支数据，系统将为您生成全周期的生存推演图表。")
    st.image("https://images.unsplash.com/photo-1560518883-ce09059eeffa?ixlib=rb-4.0.3&auto=format&fit=crop&w=1000&q=80", caption='打破买房幻觉，通过揭示"破产日期"来建立真实的安全感')
