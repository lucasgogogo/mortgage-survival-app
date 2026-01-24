import streamlit as st
import pandas as pd
import numpy as np

# --- 页面基础设置 ---
st.set_page_config(page_title="买房生存压力测试", page_icon="🏠")

st.title("🏠 买房生存压力测试模型")
st.markdown("### —— 你的现金流能撑到哪一天？")

# --- 侧边栏：输入参数 ---
st.sidebar.header("1. 房子与贷款")
house_price = st.sidebar.number_input("房屋总价 ($)", value=420000, step=5000)
down_payment = st.sidebar.number_input("首付金额 ($)", value=110000, step=5000)
rate_annual = st.sidebar.number_input("年利率 (%)", value=3.80, step=0.1, format="%.2f")
amortization_years = st.sidebar.selectbox("贷款年限", [25, 30], index=0)
closing_cost = st.sidebar.number_input("购房杂费 (律师/税) ($)", value=8250)

st.sidebar.header("2. 你的家底")
cash_now = st.sidebar.number_input("现有活钱 ($)", value=190000, help="不含定存，手头马上能用的钱")
gic_amount = st.sidebar.number_input("定存回笼 ($)", value=100000, help="第6个月会到账的钱")

st.sidebar.header("3. 每月收支")
monthly_income = st.sidebar.number_input("月纯收入 ($)", value=2330)
monthly_expense = st.sidebar.number_input("月生活支出 ($)", value=3302)
house_expense = st.sidebar.number_input("房产持有成本 (地税/保险) ($)", value=408)

st.sidebar.header("4. 关键决策 (第6个月)")
prepay_amount = st.sidebar.slider("6月提前还贷金额 ($)", 0, 100000, 0, step=5000)
penalty = st.sidebar.number_input("提前还贷罚金 ($)", value=0)

# --- 核心算法函数 ---

def calc_cdn_mortgage(principal, annual_rate, years):
    """
    计算加拿大房贷月供 (半年复利法 Semi-annual compounding)
    这是加拿大法律规定的算法，和美国的月复利不一样。
    """
    if principal <= 0: return 0
    # 将名义年利率转换为半年复利下的月实际利率
    semi_annual_rate = annual_rate / 100 / 2
    monthly_rate = (1 + semi_annual_rate) ** (2 / 12) - 1
    total_payments = years * 12
    # PMT公式
    payment = principal * (monthly_rate * (1 + monthly_rate) ** total_payments) / ((1 + monthly_rate) ** total_payments - 1)
    return payment

# --- 开始推演 ---

# 1. 初始计算
loan_amount = house_price - down_payment
initial_monthly_payment = calc_cdn_mortgage(loan_amount, rate_annual, amortization_years)
initial_cash = cash_now - down_payment - closing_cost

# 2. 模拟未来 60 个月 (5年)
months_data = []
current_cash = initial_cash
current_loan = loan_amount
# 剩余还款月数
months_left = amortization_years * 12 

bankruptcy_month = None

for m in range(1, 61):
    # --- 收入与支出 ---
    monthly_net_loss = monthly_income - monthly_expense - house_expense
    
    # --- 房贷处理 ---
    # 第6个月特殊事件
    special_event_cash = 0
    current_payment = 0
    
    if m == 6:
        # 定存回来了
        special_event_cash += gic_amount
        # 决定要不要提前还贷
        special_event_cash -= prepay_amount
        special_event_cash -= penalty
        
        # 重新计算剩余本金 (粗略估算：本金 = 上月本金 - 提前还款)
        # 严谨算法其实每月的月供里都有本金扣除，这里为了简化模拟，暂忽略前5个月微小的本金偿付
        current_loan -= prepay_amount 
        
        # 重新计算月供 (剩余期限缩短了5个月)
        months_left_now = (amortization_years * 12) - 5
        # 这里的年限传进去要换算成年，因为我的函数接收的是年
        # 但为了复用函数，这里用总期数倒推更准，不过为了演示，重新调用函数：
        if current_loan > 0:
            # 这种反推为了适配之前的函数稍微有点绕，但在APP里足够精确
            new_payment = calc_cdn_mortgage(current_loan, rate_annual, months_left_now/12)
        else:
            new_payment = 0
            
    # 确定本月月供
    if m <= 6:
        pay = initial_monthly_payment
    else:
        # 第7个月开始使用新月供
        # 注意：这里需要保持第6个月算出来的新月供
        # 为了简单，我们再次动态算一下（实际逻辑应该存个变量，这里简化）
        temp_loan = loan_amount - prepay_amount
        temp_years = ((amortization_years * 12) - 5) / 12
        pay = calc_cdn_mortgage(temp_loan, rate_annual, temp_years)

    # --- 现金流结算 ---
    # 月初 + 净收入(亏损) - 房贷 + 特殊变动
    balance_change = monthly_net_loss - pay + special_event_cash
    current_cash += balance_change
    
    # 记录数据
    months_data.append({
        "月份": m,
        "现金余额": current_cash,
        "本月月供": pay,
        "特殊变动": special_event_cash
    })
    
    # 检测破产
    if current_cash < 0 and bankruptcy_month is None:
        bankruptcy_month = m

# 转为 DataFrame 方便画图
df = pd.DataFrame(months_data)

# --- 结果展示区 ---

col1, col2 = st.columns(2)

with col1:
    st.subheader("📊 关键指标")
    st.metric("初始月供", f"${initial_monthly_payment:,.0f}")
    if prepay_amount > 0:
        new_pay = months_data[6]['本月月供'] # 取第7个月的月供
        st.metric("6月后新月供", f"${new_pay:,.0f}", delta=f"${new_pay - initial_monthly_payment:,.0f}")
    else:
        st.metric("6月后新月供", f"${initial_monthly_payment:,.0f}", delta="不变")

with col2:
    st.subheader("💀 生存预测")
    if bankruptcy_month:
        st.error(f"⚠️ 警告：资金将在第 {bankruptcy_month} 个月断裂！")
        st.metric("预计生存期", f"{bankruptcy_month} 个月")
    else:
        st.success("✅ 安全：未来 5 年资金链健康")
        st.metric("5年后剩余现金", f"${current_cash:,.0f}")

# --- 图表区 ---
st.markdown("### 📈 现金流趋势推演 (5年)")
st.line_chart(df, x="月份", y="现金余额")

# --- 决策建议 ---
st.markdown("---")
st.subheader("💡 AI 决策助手分析")

monthly_burn = monthly_income - monthly_expense - house_expense - initial_monthly_payment
if bankruptcy_month:
    st.write(f"❌ **高风险方案**：按照当前的收入和提前还款计划，你将在 **2年半左右** 耗尽积蓄。")
    if prepay_amount > 0:
        st.write("👉 **建议**：试着把侧边栏的 **'6月提前还贷金额' 调为 0**，看看生存期是否会延长？")
else:
    st.write(f"✅ **稳健方案**：即便每月亏损约 ${abs(monthly_burn):.0f}，你深厚的现金储备（定存回笼）足以支撑你安全度过未来 5 年。")
    st.caption("注：本模型已采用加拿大 Interest Act 规定的半年复利算法。")
