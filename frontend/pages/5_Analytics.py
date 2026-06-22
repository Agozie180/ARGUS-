"""Analytics — decision distribution and score landscape across the universe."""
import argus_client as ac
import streamlit as st
import pandas as pd
import plotly.express as px

from dashboard import components as ui

st.set_page_config(page_title="Analytics — Argus", page_icon="📈", layout="wide")
ui.inject_theme()
st.markdown("# 📈 Analytics")

argus = ac.get_argus()
universe = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
rows = argus.scan(universe)
df = pd.DataFrame(rows)
report = argus.learning_report()

# --- Dashboard sections: accepted / rejected / capital saved / mistakes avoided
accepted = int((df["decision"] == "TAKE TRADE").sum())
rejected_now = int(df["decision"].isin(["NO TRADE", "REJECT"]).sum())
mistakes_avoided = report["trades_rejected"] + rejected_now
m = st.columns(4)
m[0].metric("✅ Accepted trades", accepted)
m[1].metric("🛡️ Rejected trades", report["trades_rejected"], f"{rejected_now} this scan")
m[2].metric("💰 Capital saved", f"${report['estimated_capital_saved_usd']:,.0f}")
m[3].metric("🚫 Mistakes avoided", mistakes_avoided)
st.divider()

# --- Capital Protection Score ------------------------------------------------
cps = argus.cps_overview()
hc1, hc2 = st.columns([1, 1])
with hc1:
    ui.cps_hero(cps)
with hc2:
    ui.cps_breakdown(cps)
st.divider()

c1, c2 = st.columns(2)
with c1:
    st.markdown("#### Decision distribution")
    dist = df["decision"].value_counts().reset_index()
    dist.columns = ["decision", "count"]
    fig = px.bar(dist, x="decision", y="count", color="decision",
                 color_discrete_map={"TAKE TRADE": "#16c784", "WATCH": "#f3ba2f",
                                     "NO TRADE": "#ea3943", "REJECT": "#ea3943"})
    fig.update_layout(template="plotly_dark", showlegend=False, height=340)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.markdown("#### Confidence vs Risk")
    fig2 = px.scatter(df, x="risk", y="confidence", color="decision", text="symbol",
                      color_discrete_map={"TAKE TRADE": "#16c784", "WATCH": "#f3ba2f",
                                          "NO TRADE": "#ea3943", "REJECT": "#ea3943"},
                      range_x=[0, 100], range_y=[0, 100])
    fig2.update_traces(textposition="top center", marker=dict(size=14))
    fig2.update_layout(template="plotly_dark", height=340)
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("#### Score table")
st.dataframe(df, use_container_width=True, hide_index=True)
