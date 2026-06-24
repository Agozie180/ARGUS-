"""Market Scanner — rank a live Bitget universe by trade quality; rejections sink."""
from datetime import datetime, timezone

import argus_client as ac
import streamlit as st
import pandas as pd

from dashboard import components as ui

st.set_page_config(page_title="Market Scanner — Argus", page_icon="📡", layout="wide")
ui.inject_theme()
st.markdown("# 📡 Market Scanner")
st.caption("Argus scans the live Bitget market and surfaces only what survives its guardian gates.")

argus = ac.get_argus()
status = argus.market_status()
ui.data_provenance(
    source="BITGET_LIVE" if status.get("live") else "SIMULATED",
    market_type=status.get("market_type", "spot"),
    fetched_at=status.get("checked_at"),
    detail=status.get("detail", ""),
)

# Dynamic, Bitget-wide universe by default — discovered live from top USDT volume.
mode_col = st.columns([1, 3])
use_dynamic = mode_col[0].toggle("Auto-discover top Bitget symbols", value=True,
                                 help="Pull the most actively traded USDT pairs live from Bitget.")
if use_dynamic:
    universe = argus.discover_symbols(limit=20)
    default = ", ".join(universe)
else:
    default = ", ".join(argus.data.DEFAULT_UNIVERSE)

symbols = st.text_input("Symbols (comma-separated)", default)
syms = [s.strip().upper() for s in symbols.split(",") if s.strip()]

with st.spinner(f"Scanning {len(syms)} Bitget symbols…"):
    rows = argus.scan(syms)

live_count = sum(1 for r in rows if r.get("source") == "BITGET_LIVE")
st.caption(f"📡 {live_count}/{len(rows)} symbols sourced live from Bitget "
           f"· scanned {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}")

takes = [r for r in rows if r["decision"] == "TAKE TRADE"]
watches = [r for r in rows if r["decision"] == "WATCH"]
rejects = [r for r in rows if r["decision"] in ("REJECT", "NO TRADE")]

c = st.columns(4)
c[0].metric("✅ Tradeable", len(takes))
c[1].metric("👀 Watching", len(watches))
c[2].metric("🛡️ Rejected", len(rejects))
c[3].metric("🟢 Live-sourced", f"{live_count}/{len(rows)}")

# --- Opportunities ranked first, rejections ranked separately ----------------
def _table(subset):
    if not subset:
        return None
    df = pd.DataFrame(subset)
    df["src"] = df["source"].map(lambda s: "🟢 Bitget" if s == "BITGET_LIVE" else "🟡 Demo")
    df["chg"] = df["change_24h_pct"].map(lambda v: f"{v:+.2f}%" if v is not None else "—")
    df = df[["symbol", "price", "chg", "direction", "decision", "setup_quality",
             "confidence", "risk", "data_quality", "trade_quality", "cps_impact", "src"]]
    df.columns = ["Symbol", "Price", "24h", "Bias", "Decision", "Setup",
                  "Conf", "Risk", "Data Q", "Trade Q", "CPS Impact", "Source"]
    return df

st.markdown("#### 🎯 Ranked opportunities")
opps = _table(takes + watches)
if opps is not None:
    st.dataframe(opps, use_container_width=True, hide_index=True)
else:
    st.info("No setups cleared the guardian gates right now — patience is a position. NO TRADE IS ALPHA™.")

st.markdown("#### 🛡️ Rejected / stood aside (capital protected)")
rej = _table(rejects)
if rej is not None:
    st.dataframe(rej, use_container_width=True, hide_index=True)
else:
    st.caption("Nothing rejected in this scan.")

st.caption("Genuine opportunities rank first; rejected, illiquid or overbought names "
           "fall to the bottom — by design. Every row shows its data source and the "
           "Capital Protection impact of the verdict.")
