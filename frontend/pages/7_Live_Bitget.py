"""Live Bitget Example — one real-data analysis, execution stays disabled.

Pulls **public** Bitget market data (ticker + candlesticks, no API key, no
orders) and runs it through the exact same Argus decision engine the rest of the
app uses. If Bitget is unreachable the page falls back to a deterministic demo
scenario so the judge always sees a working analysis.
"""
from datetime import datetime, timezone

import argus_client as ac
import streamlit as st

from dashboard import components as ui
from render import render_analysis
from services.live_bitget import get_live_market, LiveBitgetError

st.set_page_config(page_title="Live Bitget Example — Argus", page_icon="🛰️", layout="wide")
ui.inject_theme()

st.markdown("# 🛰️ Live Bitget Example")
st.caption(
    "Real Bitget market data → the same guardian decision engine. "
    "Read-only: Argus analyses live prices but **never** places an order."
)

argus = ac.get_argus()

# Offer a broad, live Bitget universe (discovered by volume, majors floated up)
# so judges see real data on many tokens — not a two-symbol demo.
try:
    symbol_options = argus.discover_symbols(limit=20)
except Exception:
    symbol_options = argus.data.DEFAULT_UNIVERSE
for must in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
    if must not in symbol_options:
        symbol_options.insert(0, must)

col = st.columns([2, 1, 1])
symbol = col[0].selectbox("Symbol", symbol_options)
granularity = col[1].selectbox("Candles", ["1h", "15min", "4h"], index=0)
go = col[2].button("Fetch live data", type="primary", use_container_width=True)

st.divider()

# --- fetch (with graceful fallback) ------------------------------------------
live = None
fallback_reason = ""
try:
    live = get_live_market(symbol, granularity=granularity, limit=100)
except LiveBitgetError as e:
    fallback_reason = str(e)

if live is not None:
    ui.live_data_badge(True, f"Bitget public REST • {symbol} • fetched {live.freshness_label}")
    snapshot = live.snapshot
    price = live.price
    change_pct = live.change_24h_pct
    candles = live.candles
    fetched_dt = datetime.fromtimestamp(live.fetched_at, tz=timezone.utc)
    freshness_caption = (
        f"Exchange data age at fetch: {live.data_age_seconds:.0f}s "
        f"(freshness {snapshot.data_freshness:.2f}/1.0)"
    )
else:
    ui.live_data_badge(False)
    st.warning("Live Bitget data unavailable — showing **labelled DEMO data** for "
               f"{symbol} (deterministic synthetic feed). This is never presented as live.")
    # Build a synthetic snapshot for the *actual* requested symbol so the demo
    # fallback is honest and consistent rather than a mismatched canned scenario.
    from services.market_data import build_snapshot
    snapshot = build_snapshot(symbol)
    snapshot.source = "SIMULATED"
    price = snapshot.price
    change_pct = None
    candles = []
    fetched_dt = datetime.now(timezone.utc)
    freshness_caption = "Deterministic synthetic snapshot (Bitget unreachable)."

# --- run the real decision engine on whatever snapshot we have ---------------
result = argus.analyze_snapshot(snapshot, mode=ac.Mode.PROFESSIONAL, journal=False)
judge = result["judge"]
scores = result["scores"]
cps = argus.cps_overview()

# --- market header -----------------------------------------------------------
st.markdown(f"### {snapshot.symbol}")
m = st.columns(4)
m[0].metric("Current price", f"{price:,.2f}")
m[1].metric("24h change", f"{change_pct:+.2f}%" if change_pct is not None else "—")
m[2].metric("Data freshness", fetched_dt.strftime("%H:%M:%S UTC"))
m[3].metric("Source", "Bitget (live)" if live is not None else "Demo")
st.caption(freshness_caption)

# --- recent candles ----------------------------------------------------------
st.markdown("#### Recent candles")
if candles:
    recent = candles[-8:]
    rows = [{
        "time": datetime.fromtimestamp(c["ts"] / 1000.0, tz=timezone.utc).strftime("%m-%d %H:%M"),
        "open": round(c["open"], 2),
        "high": round(c["high"], 2),
        "low": round(c["low"], 2),
        "close": round(c["close"], 2),
        "volume": round(c["volume"], 2),
    } for c in reversed(recent)]
    st.dataframe(rows, use_container_width=True, hide_index=True)
else:
    st.caption("No live candles — demo scenario has no candle history.")

st.divider()

# --- Argus verdict (the required fields, front and centre) -------------------
st.markdown("#### Argus verdict")
ui.decision_badge(judge["final_decision"], judge["setup_quality"])

v = st.columns(4)
v[0].metric("Confidence", f"{scores['confidence']:.0f}/100")
v[1].metric("Risk score", f"{scores['risk']:.0f}/100")
v[2].metric("Capital Protection Score", f"{cps['cps']:.0f}/100", f"Grade {cps['grade']}")
v[3].metric("Trade quality", f"{scores['trade_quality']:.0f}/100")

if judge["final_decision"] in ("NO TRADE", "REJECT"):
    st.error(f"🛡️ **Rejection reason:** {judge['why_trade_should_be_rejected']}")
else:
    st.success(f"✅ **{judge['final_decision']}** — {judge['trade_thesis']}")

st.caption(
    "PAPER_TRADING is on and execution is disabled — this analysis never sends an "
    "order to Bitget. NO TRADE IS ALPHA™."
)

# --- full guardian breakdown -------------------------------------------------
with st.expander("Full Argus analysis", expanded=False):
    render_analysis(result)
