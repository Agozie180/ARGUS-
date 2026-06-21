"""Trade Analysis — full Judge Mode verdict for a single symbol."""
import argus_client as ac
import streamlit as st

from dashboard import components as ui
from render import render_analysis

st.set_page_config(page_title="Trade Analysis — Argus", page_icon="🔬", layout="wide")
ui.inject_theme()
st.markdown("# 🔬 Trade Analysis")

argus = ac.get_argus()
col = st.columns([2, 1, 1])
symbol = col[0].text_input("Symbol", "BTCUSDT")
product = col[1].selectbox("Product", ["futures", "spot"])
mode_label = col[2].selectbox("Explain mode", ["Professional", "Beginner"])

res = argus.analyze(symbol.upper(), mode=ac.mode_from_label(mode_label), product=product)
render_analysis(res)
