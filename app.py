import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# --- Page Configuration ---
st.set_page_config(page_title="BrokeDate V2", page_icon="🏠")

st.title("🏠 BrokeDate V2: Mortgage Survival Simulator")
st.markdown("**Don't just calculate your mortgage, calculate your survival.**")
st.caption("Core Spirit: Break the illusion of home ownership. Reveal your 'Bankruptcy Date' to build true security.")

# --- 🔒 Privacy Shield (English) ---
st.markdown("""
    <div style="background-color: #ecfdf5; border: 1px solid #10b981; padding: 15px; border-radius: 8px; color: #064e3b; margin: 20px 0;">
        <span style="font-size: 18px;">🔒 <strong>Privacy Guarantee</strong></span><br>
        <span style="font-size: 14px; opacity: 0.9;">
            We <strong>do not store</strong> any of your data. All calculations are performed locally in your browser. No one (including us) can see your financial truth.
            <br>All input data is destroyed immediately upon closing this page.
        </span>
    </div>
""", unsafe_allow_html=True)

# --- 0. Core Algorithms (Helper Functions) ---
def calc_cdn_mortgage(principal, annual_rate, years):
    """Canadian Mortgage Calc (Semi-annual compounding)"""
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
    return f"{diff // 12} Years {diff % 12} Months"

# --- Sidebar: Inputs ---
st.sidebar.header("1. Property & Loan")
house_price = st.sidebar.number_input("House Price ($)", value=0, step=5000)
down_payment = st.sidebar.number_input("Down Payment ($)", value=0, step=5000)
rate_annual = st.sidebar.number_input("Annual Interest Rate (%)", value=0.00, step=0.1, format="%.2f")
amortization_years = st.sidebar.selectbox("Amortization Period (Years)", [25, 30], index=0)

# --- ✨ Real-time Sidebar Calc (Always Visible) ---
sidebar_loan = max(0, house_price - down_payment)
sidebar_payment = calc_cdn_mortgage(sidebar_loan, rate_annual, amortization_years)

st.sidebar.markdown(f"""
<div style="background-color: #f0f2f6; padding: 10px; border-radius: 5px; margin-top: 10px; border-left: 4px solid #e63946;">
    <small style="color: #666;">📉 Loan Principal: ${sidebar_loan:,}</small><br>
    <span style="font-size: 16px; font-weight: bold;">👉 Monthly Payment: </span>
    <span style="font-size: 20px; font-weight: 900; color: #e63946;">${sidebar_payment:,}</span>
</div>
""", unsafe_allow_html=True)
# ----------------------------------------

st.sidebar.header("2. Assets & Savings")
cash_now = st.sidebar.number_input("Current Cash/Savings ($)", value=0)
gic_amount = st.sidebar.number_input("Future Inflows (e.g., GIC) ($)", value=0)

st.sidebar.header("3. Monthly Budget")
start_date_input = st.sidebar.date_input("Simulation Start Date", datetime.today())
start_date = datetime(start_date_input.year, start_date_input.month, 1)

monthly_income = st.sidebar.number_input("Net Monthly Income ($)", value=0)
income_growth_rate = st.sidebar.number_input("Est. Income Growth Rate (%)", value=0.0, step=0.5)
monthly_expense = st.sidebar.number_input("Living Expenses ($)", value=0)
house_expense = st.sidebar.number_input("Property Tax & Insurance/mo ($)", value=0)

st.sidebar.header("4. Prepayment Strategy")
prepay_amount = st.sidebar.number_input("Prepayment Amount ($)", value=0, step=5000)

col_y, col_m = st.sidebar.columns(2)
with col_y:
    prepay_year = st.selectbox("Year", range(start_date.year, start_date.year + 31), index=0)
with col_m:
    prepay_month = st.selectbox("Month", range(1, 13), index=start_date.month - 1)

prepay_date = datetime(prepay_year, prepay_month, 1)
penalty = st.sidebar.number_input("Prepayment Penalty ($)", value=0)


# --- Logic Trigger: Only run if House Price > 0 ---
if house_price > 0:
    # --- Simulation Loop ---
    loan_balance = house_price - down_payment
    current_cash = cash_now - (house_price * 0.02) # Assume 2% closing costs
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
        
        # Annual Update (Inflation & Income)
        if m > 1 and (m - 1) % 12 == 0:
            active_monthly_expense *= (1 + inflation_rate)
            active_house_expense *= (1 + inflation_rate)
            active_income_cap *= (1 + inflation_rate)
            if active_monthly_income < active_income_cap:
                active_monthly_income *= (1 + income_growth_rate / 100)

        special_event_cash = 0
        if m == 6: special_event_cash += gic_amount
        
        # Prepayment Logic
        if this_month_date.year == prepay_date.year and this_month_date.month == prepay_date.month and prepay_amount > 0:
            special_event_cash -= (prepay_amount + penalty)
            loan_balance -= prepay_amount
            if loan_balance < 0: loan_balance = 0
            prepay_note = f"Note: Payment adjusted after prepayment of ${prepay_amount:,} in {this_month_date.strftime('%Y-%m')}"
        
        # 5-Year Renewal Logic (Canadian standard)
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

        # Principal & Interest
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
        
        if current_cash < 0 and bankruptcy_date is None: 
            bankruptcy_date = this_month_date
        
        if loan_balance <= 0 and m > 72 and (current_cash < 0 or m > 540): 
            break

    df = pd.DataFrame(months_data)

    # --- Results Display ---
    st.subheader("🏁 Full Cycle Forecast")
    c1, c2 = st.columns(2)
    with c1:
        if bankruptcy_date:
            st.error(f"💀 Bankruptcy Date: {bankruptcy_date.strftime('%Y-%m')}")
            st.write(f"Survival Time: **{get_duration_str(start_date, bankruptcy_date)}**")
        else: 
            st.success("✅ Cash Flow Safe")
    with c2:
        if payoff_date: 
            st.info(f"🏠 Payoff Date: {payoff_date.strftime('%Y-%m')}")

    st.markdown("---")
    st.subheader("📅 Payment Schedule")
    
    if len(payment_history) > 0:
        if len(payment_history) > 1 and prepay_note:
            p1 = payment_history[0]
            st.write(f"⏱ **{p1['start'].strftime('%Y-%m')} - {p1['end'].strftime('%Y-%m')}** : Monthly Payment **${p1['amount']:,}**")
            st.caption(prepay_note)
            if len(payment_history) >= 2:
                p2 = payment_history[1]
                st.write(f"⏱ **{p2['start'].strftime('%Y-%m')} - {p2['end'].strftime('%Y-%m')}** : Monthly Payment **${p2['amount']:,}**")
        else:
            for phase in payment_history:
                st.write(f"⏱ **{phase['start'].strftime('%Y-%m')} - {phase['end'].strftime('%Y-%m')}** : Monthly Payment **${phase['amount']:,}**")
    else:
        st.write(f"⏱ **Starting {start_date.strftime('%Y-%m')}** : Current Payment **${current_monthly_payment:,}**")

    # --- Chart ---
    st.markdown("### 📈 Wealth vs. Debt Curve")
    st.line_chart(df.set_index("Date")[["Cash", "Loan", "ZeroLine"]], color=["#29b5e8", "#ff4b4b", "#000000"])
    
    st.caption(f"Note: Model includes {inflation_rate*100}% annual inflation on living costs. Income growth is capped at an initial ${initial_income_cap} (indexed to inflation).")

else:
    # --- Welcome Screen ---
    st.info("👋 Welcome to BrokeDate V2! Please enter your mortgage, asset, and budget details in the sidebar to generate your survival forecast.")
    
    st.image("https://images.unsplash.com/photo-1560518883-ce09059eeffa?ixlib=rb-4.0.3&auto=format&fit=crop&w=1000&q=80", caption="Plan your financial future before it's too late.")
