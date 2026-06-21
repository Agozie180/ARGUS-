"""Argus web app — Home.

Launch:  streamlit run frontend/Home.py
"""
import argus_client as ac  # noqa: F401  (bootstraps sys.path)
import streamlit as st

from dashboard import components as ui
from core.models import Mode

st.set_page_config(page_title="Argus — AI Trading Guardian", page_icon="🛡️", layout="wide")
ui.inject_theme()

st.markdown("# 🛡️ Argus")
st.markdown("### *Most bots help you enter trades. Argus helps you survive them.*")
st.write(
    "Argus is an **AI Trading Guardian**. It does not chase signals — it protects "
    "capital, rejects bad trades, explains risk, and helps you make disciplined "
    "decisions. It never fabricates confidence and is proud to say **NO TRADE**."
)

argus = ac.get_argus()

# --- Live capital-protection summary -----------------------------------------
report = argus.learning_report()
m = st.columns(4)
m[0].metric("Decisions made", report["total_decisions"])
m[1].metric("Trades rejected", report["trades_rejected"])
m[2].metric("Rejection rate", f"{report['rejection_rate_pct']:.0f}%")
m[3].metric("Capital saved", f"${report['estimated_capital_saved_usd']:,.0f}")

st.divider()

# --- Quick analyze -----------------------------------------------------------
st.markdown("#### Quick analysis")
col = st.columns([2, 1, 1])
symbol = col[0].text_input("Symbol", "BTCUSDT")
mode_label = col[1].selectbox("Mode", ["Professional", "Beginner"])
go = col[2].button("Analyze", type="primary", use_container_width=True)

if go:
    from render import render_analysis
    res = argus.analyze(symbol.upper(), mode=ac.mode_from_label(mode_label))
    render_analysis(res)
else:
    st.info("Enter a symbol and hit **Analyze**, or explore the pages in the sidebar: "
            "Market Scanner, Trade Analysis, Risk Guardian, Journal, Analytics, Demo Mode.")

st.divider()
st.caption("Argus is a guardian, not an oracle. It helps traders avoid bad trades, "
           "understand risk, and preserve capital. Paper / read-only by design.")
