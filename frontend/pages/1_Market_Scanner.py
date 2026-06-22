"""Market Scanner — rank a universe by trade quality; rejections sink."""
import argus_client as ac
import streamlit as st
import pandas as pd

from dashboard import components as ui

st.set_page_config(page_title="Market Scanner — Argus", page_icon="📡", layout="wide")
ui.inject_theme()
st.markdown("# 📡 Market Scanner")
st.caption("Argus scans the universe and surfaces only what survives its guardian gates.")

argus = ac.get_argus()
default = "BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT"
symbols = st.text_input("Symbols (comma-separated)", default)
syms = [s.strip().upper() for s in symbols.split(",") if s.strip()]

rows = argus.scan(syms)
df = pd.DataFrame(rows)
if not df.empty:
    df = df[["symbol", "direction", "decision", "setup_quality",
             "confidence", "risk", "data_quality", "trade_quality"]]
    df.columns = ["Symbol", "Bias", "Decision", "Setup", "Conf", "Risk", "Data Q", "Trade Q"]

takes = [r for r in rows if r["decision"] == "TAKE TRADE"]
watches = [r for r in rows if r["decision"] == "WATCH"]
rejects = [r for r in rows if r["decision"] in ("REJECT", "NO TRADE")]

c = st.columns(3)
c[0].metric("✅ Tradeable", len(takes))
c[1].metric("👀 Watching", len(watches))
c[2].metric("🛡️ Rejected", len(rejects))

st.dataframe(df, use_container_width=True, hide_index=True)
st.caption("Sort order puts genuine opportunities first; rejected/illiquid names fall to the bottom — by design.")
