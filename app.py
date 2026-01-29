import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- 页面基础设置 ---
st.set_page_config(page_title="BrokeDate V1.6.10", page_icon="🏠")

st.title("🏠 房贷生存全周期测试模型")

# --- 侧边栏：输入参数 (全部清空为0) ---
st.sidebar.header("1. 房子与贷款")
house_price = st.sidebar.number_input("房屋总价 ($)", value=0, step=5000)
down_payment = st.sidebar.number_input("首付金额 ($)", value=0, step=5000)
rate_annual = st.sidebar.number_input("年利率 (%)", value=0.00, step=0.1, format="%.2f")
amortization_years = st.sidebar.selectbox("贷款总年限", [25, 30], index=0)

st.sidebar.header("2. 你的家底")
cash_now = st.sidebar.number_input("现有活钱 ($)", value=0)
gic_amount = st.sidebar.number_input("定存回笼 ($)", value=0)

st.sidebar.header("3. 每月收支")
start_date_input = st.sidebar.date_input("模拟开始日期", datetime.today())
# 自动锁定为该月1号
start_date = datetime(start_date_input.year, start_date_input.month, 1)

monthly_income = st.sidebar.number_input("当前月纯收入 ($)", value=0)
income_growth_rate = st.sidebar.number_input("预计年收入增长率 (%)", value=0.0, step=0.5)
monthly_expense = st.sidebar.number_input("月生活支出 ($)", value=0)
house_expense = st.sidebar.number_input("房产持有杂费 ($)", value=0)

st.sidebar.header("4. 提前还贷决策")
prepay_amount = st.sidebar.number_input("提前还贷金额 ($)", value=0, step=5000)

# 从下拉框选年月
col_y, col_m = st.sidebar.columns(2)
with col_y:
    prepay_year = st.selectbox("还贷年份", range(start_date.year, start_date.year + 31), index=0)
with col_m:
    prepay_month = st.selectbox("还贷月份", range(1, 13), index=start_date.month - 1)

prepay_date = datetime(prepay_year, prepay_month, 1)
penalty = st.sidebar.number_input("提前还贷罚金 ($)", value=0)

# --- 核心算法 ---
def calc_cdn_mortgage(principal, annual_rate, years):
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

# --- 逻辑开关：只有输入了房价才开始推演 ---
if house_price > 0:
    # --- 开始推演 ---
    loan_balance = house_price - down_payment
    current_cash = cash_now - (house_price * 0.02)
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

    for m in range(1, 601):
        this_month_date = add_months(start_date, m-1)
        
        # 每年更新
        if m > 1 and (m - 1) % 12 == 0:
            active_monthly_expense *= (1 + inflation_rate)
            active_house_expense *= (1 + inflation_rate)
            active_income_cap *= (1 + inflation_rate)
            if active_monthly_income < active_income_cap:
                active_monthly_income *= (1 + income_growth_rate / 100)

        special_event_cash = 0
        if m == 6: special_event_cash += gic_amount
        
        # 提前还贷逻辑
        if this_month_date.year == prepay_date.year and this_month_date.month == prepay_date.month and prepay_amount > 0:
            special_event_cash -= (prepay_amount + penalty)
            loan_balance -= prepay_amount
            if loan_balance < 0: loan_balance = 0
            prepay_note = f"注：以下为 {this_month_date.strftime('%Y年%m月')} 提前还贷 ${prepay_amount:,} 后的月供变化"
            
        if m == 61:
            new_payment = calc_cdn_mortgage(loan_balance, rate_annual, amortization_years - 5)
            if new_payment != current_monthly_payment:
                payment_history.append({"start": add_months(start_date, 0), "end": add_months(start_date, 59), "amount": current_monthly_payment})
                current_monthly_payment = new_payment
                phase_start_for_new = this_month_date
            else:
                phase_start_for_new = add_months(start_date, 0)
        elif m == 1:
            phase_start_for_new = add_months(start_date, 0)

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
        
        months_data.append({"Date": this_month_date, "Cash": int(current_cash), "Loan": int(loan_balance), "ZeroLine": 0})
        if current_cash < 0 and bankruptcy_date is None: bankruptcy_date = this_month_date
        if loan_balance <= 0 and m > 72 and (current_cash < 0 or m > 540): break

    df = pd.DataFrame(months_data)

    # --- 展示 ---
    st.subheader("🏁 全周期预测结论")
    c1, c2 = st.columns(2)
    with c1:
        if bankruptcy_date:
            st.error(f"💀 破产日期: {bankruptcy_date.strftime('%Y年%m月')}")
            st.write(f"预计还能坚持: **{get_duration_str(start_date, bankruptcy_date)}**")
        else: st.success("✅ 现金流安全")
    with c2:
        if payoff_date: st.info(f"🏠 结清日期: {payoff_date.strftime('%Y年%m月')}")

    st.markdown("---")
    st.subheader("📅 房贷月供阶段表")
    if len(payment_history) > 0:
        if len(payment_history) > 1 and prepay_note:
            p1 = payment_history[0]
            st.write(f"⏱ **{p1['start'].strftime('%Y年%m月')} - {p1['end'].strftime('%Y年%m月')}** ： 月供金额为 **${p1['amount']:,}**")
            st.caption(prepay_note)
            p2 = payment_history[1]
            st.write(f"⏱ **{p2['start'].strftime('%Y年%m月')} - {p2['end'].strftime('%Y年%m月')}** ： 月供金额为 **${p2['amount']:,}**")
        else:
            for phase in payment_history:
                st.write(f"⏱ **{phase['start'].strftime('%Y年%m月')} - {phase['end'].strftime('%Y年%m月')}** ： 月供金额为 **${phase['amount']:,}**")
    else:
        st.write(f"⏱ **{start_date.strftime('%Y年%m月')} 开始** ： 当前月供为 **${current_monthly_payment:,}**")

    # --- 图表 ---
    st.markdown("### 📈 财富与债务曲线")
    st.line_chart(df.set_index("Date")[["Cash", "Loan", "ZeroLine"]], color=["#29b5e8", "#ff4b4b", "#000000"])
    st.caption(f"注：模型已自动计入每年 {inflation_rate*100}% 的生活成本通胀。月收入增长上限初始设为 ${initial_income_cap} (基于曼省平均月收入之 150%)，且该封顶值亦随通胀率逐年同步递增。")

else:
    # --- 欢迎页面 (未输入数据时显示) ---
    st.info("👋 欢迎使用 BrokeDate！请在左侧侧边栏输入您的房贷、资产及收支数据，系统将为您生成全周期的生存推演图表。")
    st.image("https://images.unsplash.com/photo-1560518883-ce09059eeffa?ixlib=rb-4.0.3&auto=format&fit=crop&w=1000&q=80", caption="规划您的财富未来")
