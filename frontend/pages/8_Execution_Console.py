"""Execution Console — mode indicator, safety arming, and the order log.

This is where Argus proves it is **execution-ready without requiring real funds**:
judges can see the PAPER/LIVE indicator, the exact safety gates between Argus and
a real order, simulate and record paper orders, and (only on a deployment that
explicitly permits it) arm live trading behind a typed confirmation.
"""
import argus_client as ac
import streamlit as st

from dashboard import components as ui

st.set_page_config(page_title="Execution Console — Argus", page_icon="🎛️", layout="wide")
ui.inject_theme()
st.markdown("# 🎛️ Execution Console")
st.caption("Argus is execution-ready but paper by default. Live orders require every "
           "safety gate below to be cleared — so no real trade can happen by accident.")

argus = ac.get_argus()
status = argus.execution_status()

# --- prominent mode indicator ------------------------------------------------
ui.execution_mode_banner(status)

# --- safety gate checklist ---------------------------------------------------
st.markdown("### 🔐 Live-trading safety gates")
b = status.get("blockers", {})
checklist = [
    ("PAPER_TRADING is disabled", b.get("paper_trading_disabled", False)),
    ("Deployment master switch ARGUS_ALLOW_LIVE_TRADING=true", b.get("live_master_switch_on", False)),
    ("Bitget trading credentials present", b.get("credentials_present", False)),
    ("Live trading armed in this session", status.get("armed", False)),
]
for label, ok in checklist:
    st.markdown(f"- {'✅' if ok else '⛔'} {label}")

allowed = status.get("live_allowed_by_deployment", False)
st.info(status.get("detail", ""))

# --- arming / disarming ------------------------------------------------------
st.markdown("### 🚦 Live trading control")
if not allowed:
    st.warning("**Live trading is disabled by deployment configuration.** This build is "
               "hard-locked to PAPER mode — orders are simulated and recorded, never sent "
               "to Bitget. To enable live trading, an operator must set `PAPER_TRADING=False` "
               "and `ARGUS_ALLOW_LIVE_TRADING=true` with valid credentials, then arm it here.")
else:
    if status.get("armed"):
        st.error("🔴 LIVE trading is ARMED. Real orders will be routed to Bitget.")
        if st.button("Disarm live trading (return to paper)", type="primary"):
            argus.disarm_live()
            st.rerun()
    else:
        st.markdown(f"Type the confirmation phrase **`{status.get('confirm_phrase','')}`** to arm "
                    "live trading for this session. Each order still requires its own confirm.")
        phrase = st.text_input("Confirmation phrase", "", placeholder=status.get("confirm_phrase", ""))
        ack = st.checkbox("I understand this will place REAL orders with REAL capital on Bitget.")
        if st.button("Arm live trading", type="primary", disabled=not ack):
            res = argus.arm_live(phrase)
            if res.get("armed"):
                st.success("Live trading armed.")
                st.rerun()
            else:
                st.error(f"Could not arm: {res.get('reason','unknown')}")

# --- simulate / record an order (works in any mode, no real funds in paper) --
st.divider()
st.markdown("### 🧪 Run an execution through the guardian")
st.caption("Argus only deploys capital on a TAKE TRADE verdict. In PAPER mode the fill is "
           "simulated and recorded; in armed LIVE mode it routes a real Bitget order.")
col = st.columns([2, 1, 1])
symbol = col[0].text_input("Symbol", "BTCUSDT")
product = col[1].selectbox("Product", ["futures", "spot"])
go = col[2].button("Analyze & execute", use_container_width=True)
if go:
    ex = argus.execute(symbol.upper(), product=product)
    e = ex["execution"]
    if e["executed"]:
        p = e["position"]
        st.success(f"[{p.get('mode','PAPER')}] Opened {p['direction']} {p['symbol']} — "
                   f"size ${p['size_usd']:,.0f} @ {p['fill_price']:,}. Trade `{p['trade_id']}`.")
    else:
        st.info(f"[{e.get('mode','PAPER')}] No position opened — {e['reason']}")

# --- order log ---------------------------------------------------------------
st.divider()
st.markdown("### 📜 Order log (recorded)")
orders = argus.execution_status().get("recent_orders", [])
if orders:
    import pandas as pd
    df = pd.DataFrame(orders)
    df["mode"] = df["mode"].map(lambda m: "🔴 LIVE" if m == "LIVE" else "📝 PAPER")
    st.dataframe(df[["ts", "symbol", "side", "size_usd", "fill_price", "mode", "order_ref"]],
                 use_container_width=True, hide_index=True)
else:
    st.caption("No orders recorded yet. Run an execution above to populate the log.")
