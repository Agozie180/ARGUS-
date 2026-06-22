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

# --- Paper execution ---------------------------------------------------------
st.divider()
st.markdown("#### Execute (paper)")
decision = res["judge"]["final_decision"]
if decision == "TAKE TRADE":
    st.success(f"Argus approves **{symbol.upper()}** — a paper position can be opened.")
    if st.button("🚀 Execute paper trade", type="primary"):
        ex = argus.execute(symbol.upper(), mode=ac.mode_from_label(mode_label), product=product)
        if ex["execution"]["executed"]:
            p = ex["execution"]["position"]
            st.success(f"Opened {p['direction']} {p['symbol']} — size ${p['size_usd']:,.0f} "
                       f"@ {p['fill_price']:,} (stop {p['stop_loss']:,}). Trade ID `{p['trade_id']}`.")
            st.caption("Track and close it on the **Risk Guardian** page.")
        else:
            st.warning(ex["execution"]["reason"])
else:
    st.info(f"Argus withholds execution — decision is **{decision}**. "
            "Capital is only deployed on a TAKE TRADE. **NO TRADE IS ALPHA™**")
