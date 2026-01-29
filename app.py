import streamlit as st
import pandas as pd
from datetime import datetime

# --- 1. 页面配置与高级样式 (Page Config & CSS) ---
st.set_page_config(page_title="BrokeDate - Canada", page_icon="💀", layout="centered")

st.markdown("""
    <style>
    /* 1. 强制隐藏默认页眉并修正内容区位移 */
    [data-testid="stHeader"] {display: none;}
    .block-container {
        padding-top: 10rem !important;  /* 增加顶部间距，彻底避开看板 */
        max-width: 500px !important;    /* 限制宽度，更像手机 App 比例 */
    }

    /* 2. 精简版吸顶看板 (Sticky Header) */
    .survival-header {
        position: fixed; top: 0; left: 0; right: 0;
        background: rgba(255, 255, 255, 0.98);
        backdrop-filter: blur(15px);
        padding: 8px 0;
        border-bottom: 1px solid #f1f5f9;
        z-index: 9999; /* 确保最高层级 */
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .conclusion-text { font-size: 1.2rem !important; font-weight: 900; margin: 0; padding: 0 10px; }
    .sub-text { font-size: 0.75rem; color: #94a3b8; margin: 2px 0 0 0; }

    /* 3. 进度条紧贴看板下沿 */
    .stProgress { 
        position: fixed; top: 68px; left: 0; right: 0; 
        z-index: 10000; height: 4px; 
    }
    .stProgress > div > div > div > div { background-color: #ef4444; }
    
    /* 4. 按钮 App 化 */
    .stButton>button {
        width: 100%; border-radius: 12px; height: 3.5rem;
        background-color: #0f172a; color: white; border: none; 
        font-weight: 700; font-size: 1rem; margin-top: 2rem;
    }
    
    /* 5. 输入框标题加深，增加间距 */
    label { font-weight: 600 !important; color: #1e293b !important; margin-bottom: 8px !important; }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心算法 (Core Algorithms) ---

def calc_cdn_monthly_rate(annual_rate):
    return (1 + annual_rate / 2)**(2/12) - 1

def calculate_survival(data):
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
    
    principal = house_price - down_payment
    monthly_rate = calc_cdn_monthly_rate(annual_rate)
    total_months = amort_years * 12
    
    def get_payment(p, r, n):
        if p <= 0 or r <= 0: return 0
        return p * (r * (1 + r)**n) / ((1 + r)**n - 1)

    monthly_payment = get_payment(principal, monthly_rate, total_months)
    
    history = []
    bankrupt_age = None
    
    for m in range(1, 1201):
        if m % 12 == 0:
            income = min(income * 1.03, 6200 * (1.021 ** (m//12))) 
            monthly_expense *= 1.021 
        
        if principal > 0:
            interest_step = principal * monthly_rate
            principal_step = monthly_payment - interest_step
            principal -= principal_step
            if m == prepay_month_idx: principal -= prepay_amt
            if m == 61: 
                monthly_payment = get_payment(principal, monthly_rate, total_months - 60)
        
        cash = cash + income - monthly_payment - monthly_expense
        current_age = age + (m/12)
        history.append({"Age": current_age, "Cash": cash})
        
        if cash <= 0 and bankrupt_age is None:
            bankrupt_age = current_age
            break
            
    return bankrupt_age, history

# --- 3. 状态栏渲染函数 (Status Bar Renderer) ---
def render_status_bar(bankrupt_age, current_age):
    avg_life = 82
    if bankrupt_age:
        color = "#e63946" if bankrupt_age < 60 else "#f59e0b"
        icon = "💀" if bankrupt_age < 82 else "✅"
        status_text = f"{icon} 预计将在 {bankrupt_age:.1f} 岁耗尽现金"
        progress = (bankrupt_age - current_age) / (avg_life - current_age)
        progress = max(0.0, min(1.0, progress))
    else:
        color = "#10b981"
        status_text = "✅ 恭喜！您将平安度过一生"
        progress = 1.0

    st.markdown(f"""
        <div class="survival-header">
            <p class="conclusion-text" style="color:{color};">{status_text}</p>
            <p class="sub-text">🇨🇦 加拿大平均寿命基准: {avg_life} 岁</p>
        </div>
    """, unsafe_allow_html=True)
    st.progress(progress)

# --- 4. 页面流程 (App Flow) ---

if 'step' not in st.session_state: st.session_state.step = 1
if 'data' not in st.session_state:
    st.session_state.data = {
        'age': 30, 'cash': 30000, 'gic': 10000, 'income': 2500,
        'house_price': 0, 'down_payment': 96000, 'rate': 4.5, 'amort': 25,
        'living_cost': 1800, 'house_tax': 400, 'prepay_amt': 0, 'prepay_month_idx': 0
    }

# 每一页都渲染状态栏 (除了第一页)
if st.session_state.step > 1:
    b_age, _ = calculate_survival(st.session_state.data)
    render_status_bar(b_age, st.session_state.data['age'])

# Page 1: 欢迎
if st.session_state.step == 1:
    st.title("🏠 BrokeDate")
    st.markdown("##### Don't just calculate your mortgage, calculate your survival.")
    st.write("---")
    st.info("打破买房幻觉，通过揭示“破产日期”来建立真实的安全感。")
    age_in = st.number_input("您的当前年龄 (Your Current Age)", value=30, step=1)
    if age_in >= 80:
        st.warning("爷爷/奶奶您好，我觉得您这个年纪，真的没必要算这个了，回家安心享清福吧。")
    if st.button("开启生存测算"):
        st.session_state.data['age'] = age_in
        st.session_state.step = 2
        st.rerun()

# Page 2: 资产
elif st.session_state.step == 2:
    st.subheader("💰 第一步：财富底气")
    st.session_state.data['cash'] = st.number_input("现有活钱 (Liquid Cash) (?)", value=30000, help="参考加统计局中位数。高于此数说明你的储备优于平均线。")
    st.session_state.data['gic'] = st.number_input("未来回笼 (Future Cash) (?)", value=10000, help="指目前锁定无法取出，但未来确定的入账。")
    st.session_state.data['income'] = st.number_input("月纯收入-税后 (Net Income) (?)", value=2500, help="按加国最低工资标准设定。")
    if st.button("下一步：压力接入"):
        st.session_state.step = 3
        st.rerun()

# Page 3: 房贷
elif st.session_state.step == 3:
    st.subheader("📉 第二步：债务契约")
    hp = st.number_input("房屋总价 (House Price) (?)", value=480000, help="平均房价减去 30%，入门级住房。")
    st.session_state.data['house_price'] = hp
    st.session_state.data['down_payment'] = st.number_input("首付金额", value=int(hp*0.2))
    st.session_state.data['rate'] = st.number_input("房贷利率 % (?)", value=4.5, format="%.2f", help="加拿大五年期固定利率。")
    if st.button("下一步：细化开支"):
        st.session_state.step = 4
        st.rerun()

# Page 4: 支出
elif st.session_state.step == 4:
    st.subheader("🏠 第三步：生活基准")
    st.session_state.data['living_cost'] = st.number_input("月生活支出/租金 (?)", value=1800, help="参照平均一居室租金。")
    st.session_state.data['house_tax'] = st.number_input("房产持有杂费", value=400)
    if st.button("查看生存真相"):
        st.session_state.step = 5
        st.rerun()

# Page 5: 报告
elif st.session_state.step == 5:
    st.subheader("📊 终极生存报告")
    _, history = calculate_survival(st.session_state.data)
    df = pd.DataFrame(history)
    st.line_chart(df.set_index('Age')['Cash'])
    
    st.markdown("""---""")
    with st.expander("🛠️ 决策干预 (假如我提前还贷...)"):
        st.session_state.data['prepay_amt'] = st.number_input("提前还贷金额 ($)", value=0, step=5000)
        st.session_state.data['prepay_month_idx'] = st.slider("还贷时间点 (第几个月)", 1, 60, 12)
    
    if st.button("重新开始测算"):
        st.session_state.step = 1
        st.rerun()
