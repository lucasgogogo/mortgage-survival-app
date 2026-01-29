import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- 页面基础设置 (Page Config) ---
st.set_page_config(page_title="BrokeDate - Canada", page_icon="💀", layout="centered")

# --- 样式美化 (CSS) ---
st.markdown("""
    <style>
    .stProgress > div > div > div > div { background-color: #ef4444; }
    .survival-header {
        position: fixed; top: 50px; left: 0; right: 0; background: white;
        padding: 15px; border-bottom: 2px solid #f0f2f6; z-index: 1000;
        text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .main-title { font-size: 2.5rem; font-weight: 800; color: #1e293b; margin-bottom: 0; }
    .slogan { font-size: 1.1rem; color: #64748b; margin-bottom: 2rem; }
    </style>
""", unsafe_allow_html=True)

# --- 核心算法 (Core Algorithms) ---

def calc_cdn_monthly_rate(annual_rate):
    """加拿大半年复利转月利率"""
    return (1 + annual_rate / 2)**(2/12) - 1

def calculate_survival(data):
    # 基础参数解包
    cash = data['cash'] + data['gic']
    income = data['income']
    age = data['age']
    house_price = data['house_price']
    down_payment = data['down_payment']
    annual_rate = data['rate'] / 100
    amort_years = data['amort']
    monthly_expense = data['living_cost'] + data['house_tax']
    prepay_amt = data['prepay_amt']
    prepay_month_idx = data['prepay_month_idx']
    
    # 房贷初始化
    principal = house_price - down_payment
    monthly_rate = calc_cdn_monthly_rate(annual_rate)
    total_months = amort_years * 12
    
    # 计算月供 (P&I)
    def get_payment(p, r, n):
        if p <= 0 or r <= 0: return 0
        return p * (r * (1 + r)**n) / ((1 + r)**n - 1)

    monthly_payment = get_payment(principal, monthly_rate, total_months)
    
    # 推演
    history = []
    current_date = datetime.today()
    max_months = (82 - age) * 12 if age < 82 else 120
    bankrupt_age = None
    
    for m in range(1, 1201): # 最多推演100年
        # 收入增长 (3%) 与天花板逻辑
        if m % 12 == 0:
            income = min(income * 1.03, 6200 * (1.021 ** (m//12))) 
            monthly_expense *= 1.021 # 支出通胀
        
        # 房贷逻辑
        if principal > 0:
            interest_step = principal * monthly_rate
            principal_step = monthly_payment - interest_step
            principal -= principal_step
            # 提前还贷
            if m == prepay_month_idx:
                principal -= prepay_amt
            # 5年重算 (第61个月)
            if m == 61:
                monthly_payment = get_payment(principal, monthly_rate, total_months - 60)
        
        # 现金流结算
        cash = cash + income - monthly_payment - monthly_expense
        
        current_age = age + (m/12)
        history.append({"Month": m, "Cash": cash, "Age": current_age})
        
        if cash <= 0 and bankrupt_age is None:
            bankrupt_age = current_age
            break
            
    return bankrupt_age, history

# --- 侧边栏/状态栏渲染 (Status Bar) ---
def render_status_bar(bankrupt_age, current_age):
    avg_life = 82
    if bankrupt_age:
        color = "#ef4444" if bankrupt_age < 60 else "#f59e0b"
        status_text = f"💀 预计将在 {bankrupt_age:.1f} 岁耗尽现金"
        progress = (bankrupt_age - current_age) / (avg_life - current_age)
        progress = max(0.0, min(1.0, progress))
    else:
        color = "#10b981"
        status_text = "✅ 恭喜！您将平安度过一生 (覆盖至 82 岁)"
        progress = 1.0

    st.markdown(f"""
        <div class="survival-header">
            <h3 style='color:{color}; margin:0;'>{status_text}</h3>
            <p style='margin:0; font-size:0.8rem;'>加拿大平均寿命基准线: 82 岁</p>
        </div>
        <br><br><br>
    """, unsafe_allow_html=True)
    st.progress(progress)

# --- 页面逻辑 (Main UI) ---

if 'step' not in st.session_state:
    st.session_state.step = 1
if 'data' not in st.session_state:
    st.session_state.data = {
        'age': 30, 'cash': 30000, 'gic': 10000, 'income': 2500,
        'house_price': 0, 'down_payment': 96000, 'rate': 4.5, 'amort': 25,
        'living_cost': 1800, 'house_tax': 400, 'prepay_amt': 0, 'prepay_month_idx': 0
    }

# Page 1: 欢迎页
if st.session_state.step == 1:
    st.markdown("<h1 class='main-title'>BrokeDate</h1>", unsafe_allow_html=True)
    st.markdown("<p class='slogan'>Don't just calculate your mortgage, calculate your survival.</p>", unsafe_allow_html=True)
    st.info("打破买房幻觉，通过揭示“破产日期”来建立真实的安全感。")
    
    age_input = st.number_input("您的当前年龄 (Your Current Age)", value=30, step=1)
    if age_input >= 80:
        st.warning("爷爷/奶奶您好，我觉得您这个年纪，真的没必要算这个了，回家安心享清福吧。")
    
    if st.button("开启生存测算 (Start Simulation)"):
        st.session_state.data['age'] = age_input
        st.session_state.step = 2
        st.rerun()

# Page 2: 财富底气
elif st.session_state.step == 2:
    st.header("💰 第一步：财富底气 (My Assets)")
    st.session_state.data['cash'] = st.number_input("现有活钱 (Liquid Cash) (?)", value=30000, help="参考加统计局中位数。高于此数说明你的储备优于平均线。")
    st.session_state.data['gic'] = st.number_input("未来回笼 (Future Cash) (?)", value=10000, help="指目前锁定无法取出，但未来确定的入账（如定期存款 GIC）。")
    st.session_state.data['income'] = st.number_input("月纯收入-税后 (Net Income) (?)", value=2500, help="按最低工资标准设定，若你更高则起点更稳。")
    
    if st.button("下一步：压力接入"):
        st.session_state.step = 3
        st.rerun()

# Page 3: 债务契约
elif st.session_state.step == 3:
    st.header("📉 第二步：债务契约 (My Debt)")
    hp = st.number_input("房屋总价 (House Price) (?)", value=480000, help="全加平均房价减去 30%，代表高性价比入门房。")
    st.session_state.data['house_price'] = hp
    st.session_state.data['down_payment'] = st.number_input("首付金额 (Down Payment)", value=int(hp*0.2))
    st.session_state.data['rate'] = st.number_input("房贷利率 (Rate %) (?)", value=4.5, format="%.2f", help="加拿大五年期固定利率平均水平。")
    
    # 实时渲染状态栏
    b_age, _ = calculate_survival(st.session_state.data)
    render_status_bar(b_age, st.session_state.data['age'])
    
    if st.button("下一步：细化开支"):
        st.session_state.step = 4
        st.rerun()

# Page 4: 生活基准
elif st.session_state.step == 4:
    st.header("🏠 第三步：生活基准 (Daily Living)")
    st.session_state.data['living_cost'] = st.number_input("月生活支出/租金 (Living/Rent) (?)", value=1800, help="参照全加一居室平均租金。用于评估生存成本。")
    st.session_state.data['house_tax'] = st.number_input("房产持有杂费 (Tax/Ins)", value=400)
    
    b_age, _ = calculate_survival(st.session_state.data)
    render_status_bar(b_age, st.session_state.data['age'])
    
    if st.button("查看生存真相"):
        st.session_state.step = 5
        st.rerun()

# Page 5: 终极报告
elif st.session_state.step == 5:
    st.header("📊 终极生存报告 (Survival Report)")
    
    # 突发事件与博弈区
    with st.expander("🛠️ 决策干预与突发挑战 (Strategy & Crisis)"):
        st.session_state.data['prepay_amt'] = st.number_input("提前还贷金额", value=0, step=5000)
        st.session_state.data['prepay_month_idx'] = st.slider("还贷时间点 (第几个月)", 1, 60, 12)
        
    b_age, history = calculate_survival(st.session_state.data)
    render_status_bar(b_age, st.session_state.data['age'])
    
    # 图表绘制
    df = pd.DataFrame(history)
    st.line_chart(df.set_index('Age')['Cash'])
    
    st.write("“算出哪天破产，是为了不让那一天真的到来。”")
    
    if st.button("重新测算"):
        st.session_state.step = 1
        st.rerun()
