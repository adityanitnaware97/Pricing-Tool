import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px


st.set_page_config(page_title="Pricing Recommendation Engine", layout="wide")

# ======================
# LOAD DATA
# ======================
@st.cache_data
def load_data():
    try:
        return pd.read_csv("merged_pricing_dataset.csv")
    except:
        uploaded = st.file_uploader("Upload Pricing Dataset CSV", type="csv")
        if uploaded:
            return pd.read_csv(uploaded)
        st.stop()


df = load_data()

st.title("📦 Pricing Recommendation & Decision Support Tool")

# ======================
# DATA PREVIEW
# ======================
with st.expander("Preview Dataset"):
    st.dataframe(df.head(20), use_container_width=True)

# ======================
# SKU SELECTOR
# ======================
sku = st.selectbox("Select SKU", sorted(df["SKU"].dropna().unique()))
sku_df = df[df["SKU"] == sku].copy()

row = sku_df.sort_values("Date").iloc[-1]

# ======================
# COST MODEL
# ======================
total_cost = (
    row.get("Cost", 0)
    + row.get("FBA_Fee", 0)
    + row.get("Storage_Fee", 0)
    + row.get("Handling_Cost", 0)
)

min_margin = row.get("Minimum_Acceptable_Margin_%", 10) / 100
target_margin = row.get("Target_Gross_Margin_%", 25) / 100

current_price = row.get("Current_Price", 0)
current_margin = (current_price - total_cost) / current_price if current_price else 0

days_supply = row.get("days_of_supply", np.nan)

competitor_avg = row.get("Avg_Competitor_Price", np.nan)
competitor_low = row.get("Lowest_Competitor_Price", np.nan)
competitor_high = row.get("Highest_Competitor_Price", np.nan)

units90 = row.get("units_shipped_t90", 0)
returns90 = row.get("returns_t90", 0)
return_risk_load = (returns90 / (units90 + 1)) * total_cost

ads_acos = row.get("acosClicks14d", np.nan)

# ======================
# PRICE TARGETS
# ======================
min_price_allowed = total_cost / (1 - min_margin)
target_price = total_cost / (1 - target_margin)

# ======================
# INVENTORY SIGNAL
# ======================
if pd.isna(days_supply):
    inventory_signal = 0
elif days_supply < 20:
    inventory_signal = +0.05
elif days_supply > 90:
    inventory_signal = -0.05
else:
    inventory_signal = 0

# ======================
# COMPETITOR SIGNAL
# ======================
if not pd.isna(competitor_avg):
    competitor_target = 0.7 * competitor_avg + 0.3 * current_price
else:
    competitor_target = current_price

# ======================
# ADS SIGNAL
# ======================
if pd.isna(ads_acos):
    ads_signal = 0
elif ads_acos > 40:
    ads_signal = +0.05
elif ads_acos < 20:
    ads_signal = -0.05
else:
    ads_signal = 0

# ======================
# RETURN RISK SIGNAL
# ======================
risk_signal = +0.05 if return_risk_load > 0.2 * total_cost else 0

# ======================
# BASE PRICE
# ======================
base = max(target_price, min_price_allowed)

# ======================
# APPLY SIGNALS
# ======================
recommended_price = base
recommended_price *= (1 + inventory_signal)
recommended_price *= (1 + ads_signal)
recommended_price *= (1 + risk_signal)

recommended_price = 0.6 * recommended_price + 0.4 * competitor_target
recommended_price = max(recommended_price, min_price_allowed)

recommended_margin = (recommended_price - total_cost) / recommended_price

# ======================
# RISK LABEL
# ======================
risk_level = "LOW"
if return_risk_load > 0.2 * total_cost or (not pd.isna(ads_acos) and ads_acos > 40):
    risk_level = "HIGH"
elif not pd.isna(days_supply) and days_supply < 20:
    risk_level = "MEDIUM"

# ======================
# KPI CARDS
# ======================
col1, col2, col3, col4 = st.columns(4)

col1.metric("💲 Current Price", f"${current_price:,.2f}")
col2.metric("📦 Days of Supply", f"{days_supply:.0f}" if not pd.isna(days_supply) else "N/A")
col3.metric("📉 Current Gross Margin", f"{current_margin*100:.1f}%")
col4.metric("⚠ Risk Level", risk_level)

col5, col6, col7, col8 = st.columns(4)
col5.metric("🧮 Total Cost", f"${total_cost:,.2f}")
col6.metric("✔ Min Margin", f"{min_margin*100:.1f}%")
col7.metric("🎯 Target Margin", f"{target_margin*100:.1f}%")
col8.metric("🔮 Recommended Price", f"${recommended_price:,.2f}")

st.caption("**Total Cost Includes:** Product Cost + FBA Fee + Storage Fee + Handling Cost")

# ======================
# EXPLANATION
# ======================
st.subheader("🧠 Price Recommendation Rationale")

reason = []
if inventory_signal > 0: reason.append("Low inventory → price increased slightly")
elif inventory_signal < 0: reason.append("High inventory → price reduced slightly")
if ads_signal > 0: reason.append("High ACOS → price increased to protect margin")
elif ads_signal < 0: reason.append("Efficient ads → price optimized for volume")
if risk_signal > 0: reason.append("High returns → risk-adjusted pricing")
if not pd.isna(competitor_avg): reason.append("Price aligned with competitor market")
if len(reason) == 0: reason.append("Price optimized to reach target margin safely")

for r in reason:
    st.write("•", r)

st.success("📌 Final price ensures minimum margin while balancing demand, ads, inventory & risk.")

# ======================
# SALES TREND
# ======================
st.subheader("📈 Historical Sales Trend")
sales_df = sku_df.groupby("Date")["Units Ordered"].sum().reset_index()
fig = px.area(sales_df, x="Date", y="Units Ordered")
st.plotly_chart(fig, use_container_width=True)

# ======================
# COMPETITOR TREND
# ======================
st.subheader("🏷 Price vs Competitors")
comp_df = sku_df[["Date","Current_Price","Avg_Competitor_Price"]]
fig2 = px.line(comp_df, x="Date", y=["Current_Price","Avg_Competitor_Price"])
st.plotly_chart(fig2, use_container_width=True)

# ======================
# ADS PERFORMANCE
# ======================
st.subheader("📢 Ads Performance (ROAS & ACOS)")
ads_df = sku_df[["Date","acosClicks14d","roasClicks14d"]]
fig3 = px.line(ads_df, x="Date", y=["acosClicks14d","roasClicks14d"])
st.plotly_chart(fig3, use_container_width=True)
