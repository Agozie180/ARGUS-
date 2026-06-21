"""Journal — decisions logged, lessons learned, capital saved."""
import argus_client as ac
import streamlit as st

from dashboard import components as ui

st.set_page_config(page_title="Journal — Argus", page_icon="📓", layout="wide")
ui.inject_theme()
st.markdown("# 📓 Trade Journal & Learning")
st.caption("Argus journals every decision and reflects on outcomes — continuous learning, not black-box.")

argus = ac.get_argus()
report = argus.learning_report()

m = st.columns(4)
m[0].metric("Decisions", report["total_decisions"])
m[1].metric("Trades taken", report["total_trades"])
m[2].metric("Rejected", report["trades_rejected"], f"{report['rejection_rate_pct']:.0f}% rate")
m[3].metric("Win rate", f"{report['win_rate_pct']:.0f}%")

ui.no_trade_alpha_banner(report["estimated_capital_saved_usd"],
                         "Cumulative capital protected by trades Argus chose NOT to take.")

st.markdown("#### Top lesson")
st.info(report["top_lesson"])

st.caption("Run analyses on the other pages to grow the journal; entries persist to argus_journal.jsonl.")
