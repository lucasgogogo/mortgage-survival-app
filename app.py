import streamlit as st
import pandas as pd

# --- 页面基础设置 ---
st.set_page_config(page_title="BrokeDate 房贷生存压力测试 V1.6", page_icon="🏠")

st.title("🏠 房贷生存全周期测试模型")
st.markdown("### —— 现金流何时枯竭？贷款何时还清？")

# --- 侧边栏：输入参数 ---
st.sidebar.header("1. 房子与贷款")
house_price = st.sidebar.number_input("房屋总价 ($)", value=420000, step=5000)
down_payment = st.sidebar.number_input("首付金额 ($)", value=110000, step=5000)
rate_annual = st.sidebar.number_input("年利率 (%)", value=3.80, step=0.1, format="%.2f")
amortization_years = st.sidebar.selectbox("总贷款年限", [25, 30], index=0)

st.sidebar.header("2. 你的家底")
cash_now = st.sidebar.number_input("现有活钱 ($)", value=190000)
gic_amount = st.sidebar.number_input("定存回笼 ($)", value=100000, help="第6个月到账")

st.sidebar.header("3. 每月收支")
monthly_income = st.sidebar.number_input("月纯收入 ($)", value=2330)
monthly_expense = st.sidebar.number_input("月生活支出 ($)", value=3302)
house_expense = st.sidebar.number_input("地税保险等 ($)", value=408)

st.sidebar.header("4. 提前还贷决策 (第6个月)")
prepay_amount = st.sidebar.slider("6月提前还贷金额 ($)", 0, 100000, 0, step=5000)
penalty = st.sidebar.number_input("提前还贷罚金 ($)", value=0)

# --- 核心算法：加拿大房贷公式 ---
def calc_cdn_mortgage(principal, annual_rate, years):
    if principal <= 0 or years <= 0: return 0
    semi_annual_rate = annual_rate / 100 / 2
    monthly_rate = (1 + semi_annual_rate) ** (2 / 12) - 1
    total_payments = years * 12
    payment = principal * (monthly_rate * (1 + monthly_rate) ** total_payments) / ((1 + monthly_rate) ** total_payments - 1)
    return payment

# --- 开始推演 ---

# 初始状态
loan_balance = house_price - down_payment
current_cash = cash_now - (house_price * 0.02) # 扣除大约2%杂费
current_monthly_payment = calc_cdn_mortgage(loan_balance, rate_annual, amortization_years)

months_data = []
bankruptcy_month = None
payoff_month = None

# 最多推演40年 (480个月)，除非中途结束
for m in range(1, 481):
    special_event_cash = 0
    
    # --- 事件：第6个月提前还贷 ---
    if m == 6:
        special_event_cash += gic_amount
        special_event_cash -= (prepay_amount + penalty)
        loan_balance -= prepay_amount
        
    # --- 事件：第61个月 续约 (Renew) ---
    if m == 61:
        # 此时剩余年限为 总年限 - 5
        remaining_years = amortization_years - 5
        # 根据剩余本金重算月供
        current_monthly_payment = calc_cdn_mortgage(loan_balance, rate_annual, remaining_years)

    # --- 房贷本金偿付 (粗略估算 PPMT) ---
    # 为了算出贷款何时还完，需要扣除每月还款里的本金部分
    if loan_balance > 0:
        monthly_rate = (1 + (rate_annual/100/2))**(2/12) - 1
        interest_charge = loan_balance * monthly_rate
        principal_paid = current_monthly_payment - interest_charge
        loan_balance -= principal_paid
        if loan_balance < 0: 
            loan_balance = 0
            if payoff_month is None: payoff_month = m
    
    # --- 现金流结算 ---
    # 如果贷款还完了，月供就变0
    actual_pay = current_monthly_payment if loan_balance > 0 else 0
    monthly_net = monthly_income - monthly_expense - house_expense - actual_pay + special_event_cash
    current_cash += monthly_net
    
    # 记录数据
    months_data.append({
        "Month": m,
        "Cash": current_cash,
        "Loan": loan_balance,
        "Payment": actual_pay
    })
    
    # 判定破产
    if current_cash < 0 and bankruptcy_month is None:
        bankruptcy_month = m

    # 停止条件：既没钱了，贷款也算完了，就没必要算下去了
    if (current_cash < -1000000) or (loan_balance <= 0 and m > 72):
        break

df = pd.DataFrame(months_data)

# --- 结果展示 ---
st.subheader("🏁 最终预测结果")
c1, c2, c3 = st.columns(3)

with c1:
    if bankruptcy_month:
        st.error(f"💀 破产日期\n\n第 {bankruptcy_month} 个月")
    else:
        st.success("💰 现金流安全")

with c2:
    if payoff_month:
        st.info(f"🏠 结清日期\n\n第 {payoff_month} 个月")
    else:
        st.write("📈 贷款推演中")

with c3:
    st.metric("续约后新月供", f"${current_monthly_payment:,.0f}")

# --- 图表 ---
st.markdown("### 📈 全周期资金曲线")
# 为了方便看，我们只显示现金和贷款余额
st.line_chart(df.set_index("Month")[["Cash", "Loan"]])

st.caption(f"逻辑说明：前60个月月供固定为初始值。第61个月起，基于剩余本金按 {amortization_years-5} 年重新摊还。")
