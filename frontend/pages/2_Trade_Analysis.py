"""Trade Analysis — full Judge Mode verdict for a single symbol."""
import argus_client as ac
import streamlit as st

from dashboard import components as ui
from render import render_analysis

st.set_page_config(page_title="Trade Analysis — Argus", page_icon="🔬", layout="wide")
ui.inject_theme()
st.markdown("# 🔬 Trade Analysis")

argus = ac.get_argus()
ui.execution_mode_banner(argus.execution_status())
col = st.columns([2, 1, 1])
symbol = col[0].text_input("Symbol", "BTCUSDT")
product = col[1].selectbox("Product", ["futures", "spot"])
mode_label = col[2].selectbox("Explain mode", ["Professional", "Beginner"])

res = argus.analyze(symbol.upper(), mode=ac.mode_from_label(mode_label), product=product)
render_analysis(res)

# --- Execution ---------------------------------------------------------------
st.divider()
exec_mode = argus.effective_mode()
st.markdown(f"#### Execute ({'🔴 LIVE' if exec_mode == 'LIVE' else '📝 paper'})")
decision = res["judge"]["final_decision"]
if decision == "TAKE TRADE":
    if exec_mode == "LIVE":
        st.error(f"⚠️ **LIVE MODE** — executing will place a REAL Bitget order for "
                 f"**{symbol.upper()}** with real capital.")
        btn_label = "🔴 Execute LIVE trade"
    else:
        st.success(f"Argus approves **{symbol.upper()}** — a simulated paper position can be opened "
                   "(no real funds).")
        btn_label = "🚀 Execute paper trade"
    if st.button(btn_label, type="primary"):
        ex = argus.execute(symbol.upper(), mode=ac.mode_from_label(mode_label), product=product)
        if ex["execution"]["executed"]:
            p = ex["execution"]["position"]
            st.success(f"[{p.get('mode','PAPER')}] Opened {p['direction']} {p['symbol']} — "
                       f"size ${p['size_usd']:,.0f} @ {p['fill_price']:,} (stop {p['stop_loss']:,}). "
                       f"Trade ID `{p['trade_id']}`.")
            st.caption("Track and close it on the **Risk Guardian** page.")
        else:
            st.warning(ex["execution"]["reason"])
else:
    st.info(f"Argus withholds execution — decision is **{decision}**. "
            "Capital is only deployed on a TAKE TRADE. **NO TRADE IS ALPHA™**")
