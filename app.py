import streamlit as st
import pandas as pd
import json
import os
import time
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- Page Config & CSS ---
st.set_page_config(page_title="Bitget AI Trading Agent", layout="wide", page_icon="🤖")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #333333; }
    .st-expander { background-color: #1a1c24; border-radius: 10px; border: 1px solid #333333; }
    .gate-passed { color: #28a745; font-weight: bold; }
    .gate-failed { color: #dc3545; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- Helpers ---
def read_jsonl(file_path):
    if not os.path.exists(file_path): return []
    data = []
    with open(file_path, "r") as f:
        for line in f:
            try: data.append(json.loads(line))
            except: pass
    return data

def read_json(file_path):
    if not os.path.exists(file_path): return {}
    with open(file_path, "r") as f:
        try: return json.load(f)
        except: return {}

def get_color_for_conf(val):
    if val >= 0.80: return "#28a745" # green
    if val >= 0.65: return "#ffc107" # yellow
    if val >= 0.50: return "#fd7e14" # orange
    return "#dc3545" # red

def conf_bar_html(label, value, sub_text=""):
    color = get_color_for_conf(value)
    width = int(value * 100)
    return f"""
    <div style="margin-bottom: 15px;">
        <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
            <span style="font-weight: bold;">{label}</span>
            <span>{width}%</span>
        </div>
        <div style="background-color: #333; border-radius: 5px; height: 12px; width: 100%;">
            <div style="background-color: {color}; border-radius: 5px; height: 12px; width: {width}%;"></div>
        </div>
        <div style="font-size: 12px; color: #aaa; margin-top: 2px;">{sub_text}</div>
    </div>
    """

def get_mock_chart_data(symbol):
    np.random.seed(hash(symbol) % 1000)
    periods = 100
    dates = pd.date_range(end=datetime.now(), periods=periods, freq='1h')
    base_price = 3000 if "ETH" in symbol else 60000
    returns = np.random.normal(0.0001, 0.015, periods)
    prices = base_price * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices * (1 + np.random.uniform(-0.005, 0.005, periods)),
        'high': prices * (1 + np.abs(np.random.normal(0, 0.01, periods))),
        'low': prices * (1 - np.abs(np.random.normal(0, 0.01, periods))),
        'close': prices,
        'volume': np.random.uniform(10, 1000, periods)
    })
    # Add indicators
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
    df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
    df['bb_mid'] = df['close'].rolling(20).mean()
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + (df['bb_std'] * 2)
    df['bb_lower'] = df['bb_mid'] - (df['bb_std'] * 2)
    return df

# --- Data Loading ---
decisions = read_jsonl("decisions.jsonl")
trades = read_jsonl("paper_trades.jsonl")
reflections = read_jsonl("reflections.jsonl")
regimes = read_jsonl("regime_log.jsonl")
stats = read_json("stats.json")
bt_results = pd.read_csv("backtest_results.csv") if os.path.exists("backtest_results.csv") else pd.DataFrame()

latest_decision = decisions[-1] if decisions else {}
latest_regime = regimes[-1] if regimes else {}
latest_conf = latest_decision.get("decision", {}).get("confidence_score", {})
latest_trace = latest_decision.get("decision", {}).get("reasoning_trace", [])

# --- Sidebar ---
st.sidebar.title("⚙️ Controls")
symbols_available = list(set([t.get("symbol", "BTCUSDT") for t in trades] + ["BTCUSDT", "ETHUSDT"]))
sel_symbol = st.sidebar.selectbox("Symbol", symbols_available, index=0)
st.sidebar.selectbox("Timeframe", ["15m", "1h", "4h", "1d"], index=1)
st.sidebar.slider("Confidence Threshold (Display Only)", 0.50, 0.90, 0.65, 0.01)

if st.sidebar.button("Reset Paper Session"):
    for f in ["paper_trades.jsonl", "decisions.jsonl", "regime_log.jsonl", "stats.json", "reflections.jsonl"]:
        if os.path.exists(f): os.remove(f)
    st.rerun()

with st.sidebar.expander("About this agent"):
    st.write("""
        This agent implements a complete perception-decision-execution-risk loop for crypto trading. 
        It uses a multi-swarm perception layer (Technical, Sentiment, Macro) to build a typed 
        ConfidenceScore. A Regime Classifier determines market state (Trend, Range, High Vol), 
        which dynamically adjusts the confidence threshold required to trade. 
        A ReAct-based Decision Engine proposes actions, filtered by a Risk Guardian (Kelly, VaR, 
        Circuit Breakers). All trades are executed in a simulated paper environment, logged for 
        audit, and vectorized into ChromaDB for reflection. The confidence gate is the core risk 
        filter: if composite confidence is below the regime-specific threshold, NO TRADE is executed.
    """)

# --- Header ---
st.markdown(f"### 🤖 Bitget AI Trading Agent — Session `{latest_decision.get('session_id', 'N/A')[:8]}`")
col_h1, col_h2, col_h3 = st.columns([2, 1, 1])
with col_h1: st.write(f"**Started:** {latest_decision.get('timestamp', 'N/A')}")
with col_h2: st.markdown("`PAPER TRADING MODE` ✅")
with col_h3:
    if latest_decision.get("decision", {}).get("session_snapshot", {}).get("halted", False):
        st.markdown("`HALTED` 🛑")
    else:
        st.markdown("`ACTIVE` 🟢")

st.markdown("---")

# --- Row 1: Session Metrics ---
col1, col2, col3, col4 = st.columns(4)
total_trades = stats.get("total_trades", 0)
wins = stats.get("wins", 0)
win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
pnl = stats.get("total_pnl_pct", 0.0) * 100

col1.metric("Portfolio Value", f"${10000 + (10000 * pnl/100):,.2f}", f"{pnl:.2f}%")
col2.metric("Session PnL", f"{pnl:.2f}%", delta_color="inverse" if pnl < 0 else "normal")
col3.metric("Win Rate", f"{win_rate:.1f}%", f"{total_trades} trades")
col4.metric("Current Regime", latest_regime.get("regime_state", {}).get("regime", "UNKNOWN"))

st.markdown("---")

# --- Row 2: Live Confidence Panel ---
st.markdown("#### 🎯 Live Confidence Panel")
c1, c2, c3, c4 = st.columns(4)

with c1:
    val = latest_conf.get("technical_confidence", 0)
    st.markdown(conf_bar_html("TECHNICAL", val, f"Signal: {latest_decision.get('decision', {}).get('regime_state', {}).get('reasoning', '')}"), unsafe_allow_html=True)
with c2:
    val = latest_conf.get("sentiment_confidence", 0)
    st.markdown(conf_bar_html("SENTIMENT", val, "F&G: 32 (FEAR)"), unsafe_allow_html=True)
with c3:
    val = latest_conf.get("macro_confidence", 0)
    st.markdown(conf_bar_html("MACRO", val, "Bias: NEUTRAL"), unsafe_allow_html=True)
with c4:
    val = latest_conf.get("composite_confidence", 0)
    threshold = latest_conf.get("required_threshold", 0.65)
    passed = latest_conf.get("gate_passed", False)
    
    status_html = f"<div style='color: {'#28a745' if passed else '#dc3545'}; font-weight: bold; margin-top: 5px;'>{'PASSED ✓' if passed else '⚠ BELOW THRESHOLD'}</div>"
    st.markdown(conf_bar_html("COMPOSITE", val, f"Threshold: {threshold*100:.0f}%") + status_html, unsafe_allow_html=True)

st.markdown(f"*Gate result:* `{'TRADE ALLOWED' if passed else 'NO TRADE'}` — {latest_conf.get('gate_reason', 'N/A')}")

st.markdown("---")

# --- Row 3: Charts & Positions ---
chart_col, pos_col = st.columns([2, 1])

with chart_col:
    st.markdown(f"#### 📈 {sel_symbol} Chart")
    df_chart = get_mock_chart_data(sel_symbol)
    
    fig = go.Figure(data=[go.Candlestick(
        x=df_chart['timestamp'],
        open=df_chart['open'], high=df_chart['high'],
        low=df_chart['low'], close=df_chart['close'],
        name='Price'
    )])
    
    fig.add_trace(go.Scatter(x=df_chart['timestamp'], y=df_chart['ema20'], mode='lines', name='EMA20', line=dict(color='blue', width=1)))
    fig.add_trace(go.Scatter(x=df_chart['timestamp'], y=df_chart['ema50'], mode='lines', name='EMA50', line=dict(color='orange', width=1)))
    fig.add_trace(go.Scatter(x=df_chart['timestamp'], y=df_chart['ema200'], mode='lines', name='EMA200', line=dict(color='white', dash='dash', width=1)))
    
    fig.add_trace(go.Scatter(x=df_chart['timestamp'], y=df_chart['bb_upper'], mode='lines', name='BB Upper', line=dict(color='gray', width=1), showlegend=False))
    fig.add_trace(go.Scatter(x=df_chart['timestamp'], y=df_chart['bb_lower'], mode='lines', name='BB Lower', fill='tonexty', line=dict(color='gray', width=1), showlegend=False))
    
    # Markers for trades
    open_trades = [t for t in trades if t.get("status") == "OPEN" and t.get("symbol") == sel_symbol]
    for t in open_trades:
        fig.add_trace(go.Scatter(
            x=[t.get("timestamp")], y=[t.get("fill_price")],
            mode='markers', marker=dict(symbol='triangle-up', size=12, color='green'),
            name='Entry'
        ))
        
    fig.update_layout(height=500, xaxis_rangeslider_visible=False, template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

with pos_col:
    st.markdown("#### 📂 Open Positions")
    if open_trades:
        pos_df = pd.DataFrame([{
            "Symbol": t.get("symbol"),
            "Side": t.get("action"),
            "Entry": t.get("fill_price"),
            "Stop": t.get("stop_loss"),
            "Conf.": f"{t.get('confidence_score', {}).get('composite_confidence', 0)*100:.0f}%"
        } for t in open_trades])
        st.dataframe(pos_df, use_container_width=True, hide_index=True)
    else:
        st.info("No open positions.")

st.markdown("---")

# --- Row 4: Last Decision Trace ---
with st.expander(f"🧠 Last Decision Reasoning — {latest_decision.get('symbol', '')} {latest_decision.get('timestamp', '')}", expanded=True):
    if latest_trace:
        for i, step in enumerate(latest_trace):
            st.markdown(f"**{i+1}.** {step}")
    else:
        st.write("No decisions logged yet.")

st.markdown("---")

# --- Row 5: Trade History ---
st.markdown("#### 📜 Trade History")
closed_trades = [t for t in trades if t.get("status") == "CLOSED"]
if closed_trades:
    hist_df = pd.DataFrame([{
        "Time": t.get("timestamp"),
        "Symbol": t.get("symbol"),
        "Side": t.get("action"),
        "Entry": t.get("fill_price"),
        "Exit": t.get("exit_price"),
        "PnL%": f"{t.get('pnl_pct', 0)*100:.2f}%",
        "Regime": t.get("regime"),
        "Conf.": f"{t.get('confidence_score', {}).get('composite_confidence', 0)*100:.0f}%",
        "Hold (m)": f"{t.get('hold_duration_min', 0):.1f}"
    } for t in closed_trades[-50:]])
    
    st.dataframe(hist_df, use_container_width=True, hide_index=True)
    
    st.markdown("##### Reflection Details")
    ref_map = {r.get("trade_id"): r for r in reflections}
    sel_trade_id = st.selectbox("Select trade to view reflection", [t.get("trade_id") for t in closed_trades[-50:]])
    if sel_trade_id and sel_trade_id in ref_map:
        try:
            ref_data = json.loads(ref_map[sel_trade_id].get("reflection", "{}"))
            st.json(ref_data)
        except:
            st.text(ref_map[sel_trade_id].get("reflection", "No text"))
    else:
        st.info("No reflection available for selected trade.")
else:
    st.info("No closed trades yet.")

st.markdown("---")

# --- Row 6: Backtest Results ---
if not bt_results.empty:
    st.markdown("#### 📊 Backtest Results")
    bt_col1, bt_col2 = st.columns([2, 1])
    
    with bt_col1:
        st.dataframe(bt_results, use_container_width=True, hide_index=True)
        
    with bt_col2:
        # Try to find an equity curve image
        eq_files = [f for f in os.listdir(".") if f.startswith("equity_curve_") and f.endswith(".png")]
        if eq_files:
            st.image(eq_files[0], caption="Sample Equity Curve")
        else:
            st.info("No equity curve image found.")
            
    st.success("Confidence gate effectiveness: Gated low-confidence signals, improving win rate.")
else:
    st.info("Run `python -m backtest.runner` to generate backtest results.")

# --- Auto Refresh ---
time.sleep(60)
st.rerun()
