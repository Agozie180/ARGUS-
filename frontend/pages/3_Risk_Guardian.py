"""Risk Guardian — sizing, drawdown and portfolio health."""
import argus_client as ac
import streamlit as st

from dashboard import components as ui

st.set_page_config(page_title="Risk Guardian — Argus", page_icon="🛡️", layout="wide")
ui.inject_theme()
st.markdown("# 🛡️ Risk Guardian")
st.caption("Capital protection first. Argus sizes by volatility and conviction, and halts on drawdown.")

argus = ac.get_argus()
col = st.columns([2, 1, 1])
symbol = col[0].text_input("Symbol", "BTCUSDT")
capital = col[1].number_input("Capital (USD)", value=10_000.0, step=1000.0)
daily_pnl = col[2].slider("Today's PnL %", -8.0, 8.0, 0.0, 0.5) / 100.0

from core.scoring import compute_scores
snap = argus.data.get_snapshot(symbol.upper())
scores = compute_scores(snap)
risk = argus.risk.assess(snap, scores, capital_usd=capital, daily_pnl_pct=daily_pnl)

health_color = {"HEALTHY": "🟢", "CAUTION": "🟡", "CRITICAL": "🔴"}[risk.portfolio_health]
st.markdown(f"### Portfolio health: {health_color} **{risk.portfolio_health}**")

ui.meter("Risk", scores.risk, "higher = more dangerous", invert=True)

m = st.columns(4)
m[0].metric("Suggested size", f"${risk.suggested_position_usd:,.0f}", f"{risk.suggested_position_pct*100:.1f}% of capital")
m[1].metric("Max loss at stop", f"${risk.max_loss_usd:,.0f}")
m[2].metric("Reward : Risk", f"{risk.risk_reward:.2f}")
m[3].metric("Risk score", f"{risk.risk_score:.0f}/100")

st.markdown("#### Guardian notes")
for n in risk.notes:
    st.markdown(f"- {n}")
