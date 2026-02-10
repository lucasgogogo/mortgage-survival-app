import streamlit as st
import pandas as pd
import random
import altair as alt

# --- 1. 页面配置与 CSS (单页版特供) ---
st.set_page_config(page_title="房贷让我破产啦", page_icon="💀", layout="centered")

st.markdown("""
    <style>
    /* 隐藏默认头部 */
    [data-testid="stHeader"], [data-testid="stToolbar"] {display: none !important;}
    
    /* 调整顶部间距，给吸顶栏留位 */
    .main .block-container {
        padding-top: 140px !important; 
        max-width: 700px !important; /* 单页宽一点更好看 */
    }

    /* 吸顶生存状态栏 */
    .survival-header {
        position: fixed; 
        top: 0; left: 0; right: 0;
        background: rgba(255, 255, 255, 0.98); 
        padding: 15px 0 10px 0;
        border-bottom: 1px solid #e2e8f0;
        z-index: 999999; 
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        backdrop-filter: blur(5px);
    }
    .conclusion-text { font-size: 1.5rem !important; font-weight: 800; margin: 0; line-height: 1.2; }
    
    /* 进度条 */
    .stProgress { 
        position: fixed; top: 85px; left: 0; right: 0; 
        z-index: 1000000; height: 5px; 
    }
    
    /* 隐私盾牌 */
    .privacy-shield {
        background-color: #f0fdf4;
        border: 1px solid #bbf7d0;
        color: #166534;
        padding: 12px;
        border-radius: 8px;
        font-size: 0.85rem;
        margin-bottom: 25px;
        display: flex; align-items: center; justify-content: center; gap: 8px;
    }

    /* 分割线 */
    hr { margin: 30px 0; border-color: #f1f5f9; }

    /* 盲盒卡片 */
    .event-card {
        background-color: #fef2f2; border-left: 5px solid #ef4444;
        padding: 15px; margin-top: 20px; border-radius: 6px; color: #991b1b;
    }
    
    /* 按钮样式 */
    .stButton>button {
        width: 100%; border-radius: 8px; height: 3rem; font-weight: 700;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心算法 (保持不变) ---
def calc_cdn_monthly_rate(annual_rate):
    return (1 + annual_rate / 2)**(2/12) - 1

def calculate_survival(data, active_event=None):
    cash = data['cash'] + data['gic']
    income = data['income']
    age = data['age']
    house_price = data['house_price']
    down_payment = data['down_payment']
    monthly_rate = calc_cdn_monthly_rate(data['rate'] / 100)
    total_months = data['amort'] * 12
    monthly_expense = data['living_cost'] + data['house_tax']
    
    principal = house_price - down_payment
    
    def get_payment(p, r, n):
        if p <= 0 or r <= 0: return 0
        return p * (r * (1 + r)**n) / ((1 + r)**n - 1)

    monthly_payment = get_payment(principal, monthly_rate, total_months)
    
    history = []
    bankrupt_age = None
    
    for m in range(1, 1201):
        current_age = age + (m/12)
        if m % 12 == 0:
            max_income = data['income'] * 1.25
            income = min(income * 1.03, max_income)
            monthly_expense *= 1.021
            
        if principal > 0:
            interest_step = principal * monthly_rate
            principal_step = monthly_payment - interest_step
            principal -= principal_step
            
            # 提前还贷
            if m == data['prepay_month_idx']: principal -= data['prepay_amt']
            
            # 5年续约
            if m == 61:
                rem_m = max(0, total_months - 60)
                if rem_m > 0: monthly_payment = get_payment(principal, monthly_rate, rem_m)
        else:
            principal = 0; monthly_payment = 0

        # 随机事件
        if active_event and abs(current_age - active_event['occur_age']) < 0.1:
            if active_event['type'] == 'percent': cash -= cash * active_event['loss_val']
            elif active_event['type'] == 'monthly': monthly_expense *= (1 + active_event['loss_val'])
            else: cash -= active_event['loss_val']
            active_event = None 

        cash = cash + income - monthly_payment - monthly_expense
        history.append({"Age": current_age, "Cash Flow": cash, "Remaining Debt": principal, "Zero Line": 0})
        
        if cash <= 0 and bankrupt_age is None: bankrupt_age = current_age
            
    return bankrupt_age, history

# --- 3. 随机事件池 (保持不变) ---
def get_random_event(current_age):
    pool = [
        {"name": "生病亮红灯", "loss_val": 25000, "type": "fixed", "age_offset": 5},
        {"name": "喜提裁员大礼包", "loss_val": 20000, "type": "fixed", "age_offset": 3},
        {"name": "投资失利/赔钱", "loss_val": 0.40, "type": "percent", "age_offset": 7},
        {"name": "屋顶漏水/暖气报废", "loss_val": 10000, "type": "fixed", "age_offset": 10},
        {"name": "喜提双胞胎", "loss_val": 0.20, "type": "monthly", "age_offset": 2},
        {"name": "车祸/重大修车", "loss_val": 5000, "type": "fixed", "age_offset": 4},
        {"name": "被卷入官司/罚单", "loss_val": 8000, "type": "fixed", "age_offset": 6},
        {"name": "远亲急需借钱", "loss_val": 15000, "type": "fixed", "age_offset": 8},
        {"name": "跨国搬家/大修", "loss_val": 20000, "type": "fixed", "age_offset": 12},
        {"name": "牙医诊所深度消费", "loss_val": 3500, "type": "fixed", "age_offset": 1},
    ]
    evt = random.choice(pool)
    evt['occur_age'] = current_age + evt['age_offset']
    return evt

# --- 4. 辅助渲染 ---
def render_status_bar(bankrupt_age, current_age):
    avg_life = 82
    if bankrupt_age and bankrupt_age < 82:
        color = "#e63946"; text = f"💀 预计将在 {bankrupt_age:.1f} 岁耗尽现金"; progress = (bankrupt_age - current_age) / (avg_life - current_age)
    else:
        color = "#10b981"; text = "✅ 恭喜！您将平安度过一生 (覆盖至82岁)"; progress = 1.0
    
    st.markdown(f"""
        <div class="survival-header">
            <p class="conclusion-text" style="color:{color};">{text}</p>
        </div>
    """, unsafe_allow_html=True)
    st.progress(max(0.0, min(1.0, progress)))

# --- 5. 主程序 (单页逻辑) ---

if 'event' not in st.session_state: st.session_state.event = None

# 标题区
st.title("BrokeDate")
st.markdown("**Don't just calculate your mortgage, calculate your survival.**")
st.caption("核心精神：打破买房幻觉，通过揭示“破产日期”来建立真实的安全感。")

st.markdown("""
    <div class="privacy-shield">
        <span>🔒 我们不要你的数据。所有计算均在您的本地浏览器完成，没有任何人能看到你的财富真相。</span>
    </div>
""", unsafe_allow_html=True)

# 基础信息
col_age, col_empty = st.columns([1, 1])
with col_age:
    age = st.number_input("您的当前年龄", value=30, step=1)
    if age >= 80: st.warning("爷爷/奶奶您好，回家安心享清福吧。")

# 数据收集 (使用 expander 或者 columns 让页面更紧凑)
st.divider()

# 第一行：资产与收入
st.subheader("💰 1. 财富底气")
c1, c2, c3 = st.columns(3)
with c1:
    cash = st.number_input("现有活钱 (?)", value=30000, help="包含 TFSA、RRSP 及储蓄等。参考加国中位数。")
with c2:
    gic = st.number_input("未来定期回笼 (?)", value=10000, help="如 GIC。若无填 0。")
with c3:
    income = st.number_input("月纯收入 (?)", value=2500, help="税后实拿。按加国最低工资设定。")

# 第二行：房产与贷款
st.subheader("📉 2. 债务契约")
c4, c5, c6 = st.columns(3)
with c4:
    hp = st.number_input("房屋总价 (?)", value=480000, help="加国平均房价减 30%。")
with c5:
    dp = st.number_input("首付金额 (?)", value=int(hp*0.2), help="默认 20% 规避保险费。")
with c6:
    rate = st.number_input("房贷利率 (?)", value=4.5, format="%.2f", help="参考 5 年期固定利率平均值。")

# 第三行：生活开支
st.subheader("🏠 3. 生活基准")
c7, c8 = st.columns(2)
with c7:
    living = st.number_input("月总租金/生活支出 (?)", value=1800, help="参照一居室平均租金。")
with c8:
    tax = st.number_input("房产持有杂费 (?)", value=400, help="地税、保险及维护。")

st.divider()

# 决策干预
with st.expander("🛠️ 决策干预 (假如我提前还贷...)"):
    c9, c10 = st.columns(2)
    prepay_amt = c9.number_input("提前还贷金额", value=0, step=5000)
    prepay_idx = c10.slider("还贷时间点 (第几个月)", 1, 60, 12)

# --- 实时计算 ---
data = {
    'age': age, 'cash': cash, 'gic': gic, 'income': income,
    'house_price': hp, 'down_payment': dp, 'rate': rate, 'amort': 25,
    'living_cost': living, 'house_tax': tax,
    'prepay_amt': prepay_amt, 'prepay_month_idx': prepay_idx
}

b_age, history = calculate_survival(data, st.session_state.event)
render_status_bar(b_age, age)

# --- 图表展示 ---
st.subheader("📊 终极生存报告")
df = pd.DataFrame(history)
chart_data = df.melt('Age', value_vars=['Cash Flow', 'Remaining Debt', 'Zero Line'], var_name='Type', value_name='Amount')
color_scale = alt.Scale(domain=['Cash Flow', 'Remaining Debt', 'Zero Line'], range=['#10b981', '#ef4444', '#000000'])
lines = alt.Chart(chart_data).mark_line().encode(
    x='Age', y='Amount', color=alt.Color('Type', scale=color_scale),
    strokeWidth=alt.condition(alt.datum.Type == 'Zero Line', alt.value(3), alt.value(2))
).interactive()
st.altair_chart(lines, use_container_width=True)

# --- 盲盒与按钮 ---
if st.button("🎲 添加随机事件 (试试你的抗压极限)"):
    st.session_state.event = get_random_event(age)
    st.rerun()

evt = st.session_state.event
if evt:
    val_str = f"当前现金 {evt['loss_val']*100:.0f}%" if evt['type']=='percent' else (f"月支出+20%" if evt['type']=='monthly' else f"-${evt['loss_val']:,}")
    st.markdown(f"""<div class="event-card"><h3>⚠️ {evt['name']}</h3><p>发生时间：{evt['occur_age']:.1f} 岁 | 冲击：{val_str}</p></div>""", unsafe_allow_html=True)

if st.button("🔄 重置所有数据"):
    st.session_state.event = None
    st.rerun()
