import streamlit as st
import pandas as pd
import random
import math
import altair as alt
from datetime import datetime

# --- 1. 页面配置与 CSS 样式 (Page Config & CSS) ---
st.set_page_config(page_title="BrokeDate - Canada", page_icon="💀", layout="centered")

st.markdown("""
    <style>
    /* 彻底隐藏所有默认元素 */
    [data-testid="stHeader"], [data-testid="stToolbar"] {display: none !important;}

    /* 核心修复：给整个页面增加一个巨大的顶部内边距，防止被看板遮挡 */
    .main .block-container {
        padding-top: 180px !important;
        max-width: 550px !important;
    }

    /* 顶部吸顶看板：生存状态栏 */
    .survival-header {
        position: fixed;
        top: 0; left: 0; right: 0;
        background: #ffffff;
        padding: 20px 0 10px 0;
        border-bottom: 2px solid #f8fafc;
        z-index: 999999;
        text-align: center;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05);
    }
    .conclusion-text { font-size: 1.5rem !important; font-weight: 900; margin: 0; line-height: 1.2; }
    .sub-text { font-size: 0.8rem; color: #94a3b8; margin-top: 5px; font-weight: 500; }

    /* 进度条位置 */
    .stProgress {
        position: fixed;
        top: 95px;
        left: 0; right: 0;
        z-index: 1000000;
        height: 6px;
    }

    /* 按钮样式：黑色高级感 */
    .stButton>button {
        width: 100%; border-radius: 15px; height: 3.8rem;
        background-color: #0f172a; color: white; border: none;
        font-weight: 700; font-size: 1.1rem; margin-top: 2.5rem;
        transition: all 0.2s;
    }
    .stButton>button:hover { background-color: #1e293b; transform: translateY(-2px); }

    /* 隐私宣言样式 */
    .privacy-shield {
        background-color: #f0fdf4;
        border: 1px solid #bbf7d0;
        color: #166534;
        padding: 15px;
        border-radius: 10px;
        font-size: 0.9rem;
        margin-bottom: 20px;
        text-align: center;
    }

    /* 盲盒事件卡片样式 */
    .event-card {
        background-color: #fff1f2;
        border-left: 5px solid #e11d48;
        padding: 20px;
        margin: 20px 0;
        border-radius: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. 核心算法 (Core Algorithms) ---

def calc_cdn_monthly_rate(annual_rate):
    """加拿大半年复利转月利率"""
    return (1 + annual_rate / 2)**(2/12) - 1

def calculate_survival(data, random_event=None):
    # 参数解包
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
    bankrupt_month = None

    # 模拟 1200 个月 (100年)
    for m in range(1, 1201):
        current_age = age + (m/12)

        # 收入增长 3%，封顶中位数+25%
        if m % 12 == 0:
            income = min(income * 1.03, 6200 * (1.021 ** (m//12)))
            monthly_expense *= 1.021  # 支出通胀

        # 房贷逻辑
        if principal > 0:
            interest_step = principal * monthly_rate
            principal_step = monthly_payment - interest_step
            principal -= principal_step

            # 提前还贷逻辑
            if m == prepay_month_idx:
                principal -= prepay_amt

            # 5年自动续约
            if m == 61:
                remaining_months = max(0, total_months - 60)
                if remaining_months > 0:
                    monthly_payment = get_payment(principal, monthly_rate, remaining_months)
        else:
            monthly_payment = 0 # 房贷还清

        # 随机事件逻辑
        if random_event and m == random_event['month_idx']:
            if random_event['type'] == 'twins':
                monthly_expense *= 1.2
            elif random_event['type'] == 'invest_loss':
                loss = max(0, cash * random_event['amount'])
                cash -= loss
            else:
                cash -= random_event['amount']

        # 现金流结算
        cash = cash + income - monthly_payment - monthly_expense
        history.append({"Age": round(current_age, 2), "Cash": round(cash, 2), "Month": m})

        if cash <= 0 and bankrupt_age is None:
            bankrupt_age = current_age
            bankrupt_month = m
            break

    return bankrupt_age, history, bankrupt_month

# --- 3. 辅助函数：状态栏、随机事件、图表 ---

def render_status_bar(bankrupt_age, current_age):
    """生存状态栏渲染"""
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

def render_survival_chart(history, bankrupt_age, bankrupt_month):
    """用 Altair 绘制带破产标注的现金流走势图"""
    df = pd.DataFrame(history)

    # 主折线图
    line = alt.Chart(df).mark_line(
        color='#3b82f6',
        strokeWidth=2
    ).encode(
        x=alt.X('Age:Q', title='年龄', scale=alt.Scale(nice=True)),
        y=alt.Y('Cash:Q', title='现金余额 ($)', scale=alt.Scale(nice=True)),
        tooltip=[
            alt.Tooltip('Age:Q', title='年龄', format='.1f'),
            alt.Tooltip('Cash:Q', title='余额', format='$,.0f')
        ]
    )

    # 零线参考
    zero_line = alt.Chart(pd.DataFrame({'y': [0]})).mark_rule(
        color='#94a3b8',
        strokeDash=[4, 4],
        strokeWidth=1
    ).encode(y='y:Q')

    chart = line + zero_line

    # 破产点标注
    if bankrupt_age and bankrupt_month:
        bankrupt_row = [r for r in history if r['Month'] == bankrupt_month]
        if bankrupt_row:
            bp_df = pd.DataFrame(bankrupt_row)

            # 红色圆点
            bankrupt_point = alt.Chart(bp_df).mark_circle(
                size=120,
                color='#e63946',
                strokeWidth=2,
                stroke='#fff'
            ).encode(
                x='Age:Q',
                y='Cash:Q',
            )

            # 文字标签
            bankrupt_label = alt.Chart(bp_df).mark_text(
                align='left',
                dx=10,
                dy=-15,
                fontSize=13,
                fontWeight='bold',
                color='#e63946'
            ).encode(
                x='Age:Q',
                y='Cash:Q',
                text=alt.value(f'💀 破产 ({bankrupt_age:.1f}岁)')
            )

            chart = chart + bankrupt_point + bankrupt_label

    chart = chart.properties(
        width='container',
        height=350,
        title='现金流趋势推演'
    ).configure_title(
        fontSize=16,
        fontWeight='bold',
        anchor='start'
    ).configure_axis(
        grid=True,
        gridColor='#f1f5f9'
    )

    st.altair_chart(chart, use_container_width=True)

def generate_random_event(current_age):
    """生成随机挑战"""
    event_pool = [
        {"name": "生病亮红灯", "min": 10000, "max": 40000, "type": "fixed"},
        {"name": "喜提裁员大礼包", "min": 10000, "max": 30000, "type": "fixed"},
        {"name": "投资失利/赔钱", "min": 0.3, "max": 0.5, "type": "invest_loss"},
        {"name": "屋顶漏水/暖气报废", "min": 5000, "max": 15000, "type": "fixed"},
        {"name": "喜提双胞胎", "min": 0, "max": 0, "type": "twins"},
        {"name": "车祸/重大修车", "min": 3000, "max": 8000, "type": "fixed"},
        {"name": "被卷入官司/罚单", "min": 5000, "max": 12000, "type": "fixed"},
        {"name": "远亲急需借钱", "min": 10000, "max": 20000, "type": "fixed"},
        {"name": "跨国搬家/大修", "min": 15000, "max": 30000, "type": "fixed"},
        {"name": "牙医诊所深度消费", "min": 2000, "max": 5000, "type": "fixed"},
    ]

    selected = random.choice(event_pool)
    month_offset = random.randint(12, 120)
    event_age = current_age + (month_offset / 12)

    amount = 0
    if selected['type'] == 'fixed':
        amount = random.randint(selected['min'], selected['max'])
    elif selected['type'] == 'invest_loss':
        amount = random.uniform(selected['min'], selected['max'])

    return {
        "name": selected['name'],
        "amount": amount,
        "month_idx": month_offset,
        "occur_age": event_age,
        "type": selected['type']
    }

def generate_random_defaults():
    """生成随机的默认参数值，模拟不同的买房场景"""
    house_price = random.choice([380000, 420000, 480000, 520000, 580000, 650000, 720000, 800000])
    down_pct = random.choice([0.05, 0.10, 0.15, 0.20, 0.25])
    down_payment = int(house_price * down_pct)
    rate = round(random.uniform(3.5, 6.5), 2)
    amort = random.choice([20, 25, 30])
    cash = random.randrange(10000, 200001, 5000)
    gic = random.choice([0, 5000, 10000, 20000, 30000, 50000])
    income = random.randrange(2000, 7001, 250)
    living_cost = random.randrange(1200, 3001, 100)
    house_tax = random.randrange(200, 800, 50)
    age = random.randint(24, 45)

    return {
        'age': age, 'cash': cash, 'gic': gic, 'income': income,
        'house_price': house_price, 'down_payment': down_payment,
        'rate': rate, 'amort': amort,
        'living_cost': living_cost, 'house_tax': house_tax,
        'prepay_amt': 0, 'prepay_month_idx': 0
    }

# --- 4. 页面流程 (App Flow) ---

if 'step' not in st.session_state: st.session_state.step = 1
if 'event' not in st.session_state: st.session_state.event = None
if 'data' not in st.session_state:
    # 每次新会话生成随机默认值
    st.session_state.data = generate_random_defaults()

# 全局状态栏渲染 (P2-P6)
if st.session_state.step > 1:
    evt = st.session_state.event if st.session_state.step == 6 else None
    b_age, _, _ = calculate_survival(st.session_state.data, evt)
    render_status_bar(b_age, st.session_state.data['age'])

# --- Page 1: 欢迎与唤醒 ---
if st.session_state.step == 1:
    st.markdown("<h1 style='text-align: center;'>🏠 BrokeDate</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align: center; color: #64748b;'>Don't just calculate your mortgage, calculate your survival.</p>", unsafe_allow_html=True)

    st.write("---")

    st.markdown("""
    <div class="privacy-shield">
        🔒 <b>隐私保证</b><br>
        我们不要你的数据。所有计算均在您的本地浏览器完成，没有任何人能看到你的财富真相。
    </div>
    """, unsafe_allow_html=True)

    st.info('核心精神：打破买房幻觉，通过揭示"破产日期"来建立真实的安全感。')

    age_in = st.number_input("您的当前年龄 (Your Current Age)", value=st.session_state.data['age'], step=1)

    if age_in >= 80:
        st.warning("👴 爷爷/奶奶您好，我觉得您这个年纪，真的没必要算这个了，回家安心享清福吧。")

    if st.button("开启生存测算 (Start Simulation)"):
        st.session_state.data['age'] = age_in
        st.session_state.step = 2
        st.rerun()

# --- Page 2: 财富底气 ---
elif st.session_state.step == 2:
    st.subheader("💰 第一步：财富底气 (Assets)")
    d = st.session_state.data
    st.session_state.data['cash'] = st.number_input("现有活钱 (Liquid Cash) (?)", value=d['cash'], help="包含 TFSA、RRSP 及储蓄账户中可动用的资金。")
    st.session_state.data['gic'] = st.number_input("未来定期回笼 (Future Cash) (?)", value=d['gic'], help="指目前锁定无法取出，但未来确定的入账，如定期存款 GIC。若目前没有此类资产请填 0。")
    st.session_state.data['income'] = st.number_input("月纯收入-税后 (Net Income) (?)", value=d['income'], help="税后实拿金额。")

    if st.button("下一步：压力接入"):
        st.session_state.step = 3
        st.rerun()

# --- Page 3: 债务契约 ---
elif st.session_state.step == 3:
    st.subheader("📉 第二步：债务契约 (Debt)")
    d = st.session_state.data
    hp = st.number_input("房屋总价 (House Price) (?)", value=d['house_price'], help="取加拿大独立屋平均价格减去 30%，模拟一个极具性价比的入门级住房。")
    st.session_state.data['house_price'] = hp
    st.session_state.data['down_payment'] = st.number_input("首付金额 (Down Payment)", value=d['down_payment'], help="默认按房屋总价的 20% 计算。")
    st.session_state.data['rate'] = st.number_input("房贷利率 % (?)", value=d['rate'], format="%.2f", help="参考加拿大当前主流银行 5 年期固定利率的平均水平。")
    st.session_state.data['amort'] = st.selectbox("贷款年限 (Amortization)", options=[15, 20, 25, 30], index=[15, 20, 25, 30].index(d['amort']))

    if st.button("下一步：细化开支"):
        st.session_state.step = 4
        st.rerun()

# --- Page 4: 生活基准 ---
elif st.session_state.step == 4:
    st.subheader("🏠 第三步：生活基准 (Living)")
    d = st.session_state.data
    st.session_state.data['living_cost'] = st.number_input("月总租金/生活支出 (?)", value=d['living_cost'], help="参照加拿大一居室平均月租金。")
    st.session_state.data['house_tax'] = st.number_input("房产持有杂费 (Tax/Ins)", value=d['house_tax'], help="地税、保险及维护费用预估。")

    if st.button("查看生存真相"):
        st.session_state.step = 5
        st.rerun()

# --- Page 5: 终极博弈 ---
elif st.session_state.step == 5:
    st.subheader("📊 终极生存报告")

    b_age, history, b_month = calculate_survival(st.session_state.data)

    # 使用 Altair 绘制带破产标注的图表
    render_survival_chart(history, b_age, b_month)

    st.markdown("""---""")
    # 决策干预：提前还贷时间可选
    with st.expander("🛠️ 决策干预 (假如我提前还贷...)"):
        st.session_state.data['prepay_amt'] = st.number_input("提前还贷金额 ($)", value=st.session_state.data['prepay_amt'], step=5000)

        # 可选择提前还贷的时间点（年份+月份）
        col1, col2 = st.columns(2)
        with col1:
            prepay_year = st.selectbox(
                "还贷年份（第几年）",
                options=list(range(1, 26)),
                index=0,
                help="选择在第几年提前还贷"
            )
        with col2:
            prepay_month_in_year = st.selectbox(
                "还贷月份",
                options=list(range(1, 13)),
                index=0,
                help="选择在那一年的第几个月"
            )

        st.session_state.data['prepay_month_idx'] = (prepay_year - 1) * 12 + prepay_month_in_year

        st.caption(f"即在第 **{st.session_state.data['prepay_month_idx']}** 个月时提前还贷")

        # 立即重算并展示对比
        if st.session_state.data['prepay_amt'] > 0:
            b_age_new, history_new, b_month_new = calculate_survival(st.session_state.data)
            if b_age and b_age_new:
                diff = b_age_new - b_age if b_age_new else None
                if diff and diff > 0:
                    st.success(f"提前还贷后，破产时间推迟了 **{diff:.1f}** 年！")
                elif diff and diff < 0:
                    st.warning(f"提前还贷后，破产时间反而提前了 **{abs(diff):.1f}** 年（现金流吃紧）。")
            elif b_age and not b_age_new:
                st.success("提前还贷后，你将不再破产！")

            render_survival_chart(history_new, b_age_new, b_month_new)

    st.write('> "算出哪天破产，是为了不让那一天真的到来。"')

    if st.button("🎲 试试你的抗压极限 (Random Challenge)"):
        st.session_state.step = 6
        st.session_state.event = generate_random_event(st.session_state.data['age'])
        st.rerun()

    if st.button("🔄 重新开始测算"):
        st.session_state.step = 1
        st.session_state.event = None
        # 重新生成随机默认值
        st.session_state.data = generate_random_defaults()
        st.rerun()

# --- Page 6: 人生盲盒 ---
elif st.session_state.step == 6:
    st.subheader("🎁 人生盲盒 (Sudden Events)")

    evt = st.session_state.event
    if evt:
        impact_text = ""
        if evt['type'] == 'invest_loss':
            impact_text = f"现有现金缩水 {evt['amount']*100:.0f}%"
        elif evt['type'] == 'twins':
            impact_text = "月支出永久增加 20%"
        else:
            impact_text = f"一次性损失 ${evt['amount']:,}"

        st.markdown(f"""
        <div class="event-card">
            <h3>⚠️ 突发挑战：{evt['name']}</h3>
            <p>发生时间：<b>{evt['occur_age']:.1f} 岁</b></p>
            <p>财务冲击：<b>{impact_text}</b></p>
        </div>
        """, unsafe_allow_html=True)

        b_age_new, history_new, b_month_new = calculate_survival(st.session_state.data, evt)
        render_survival_chart(history_new, b_age_new, b_month_new)

        st.caption("注：图表已根据突发事件更新。")

    if st.button("🔄 再抽一次 (重置命运)"):
        st.session_state.event = generate_random_event(st.session_state.data['age'])
        st.rerun()

    if st.button("🔙 返回常规报告"):
        st.session_state.step = 5
        st.session_state.event = None
        st.rerun()
