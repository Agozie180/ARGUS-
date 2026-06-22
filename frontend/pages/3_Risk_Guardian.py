"""Risk Guardian — sizing, drawdown and portfolio health."""
import argus_client as ac
import streamlit as st

from dashboard import components as ui

st.set_page_config(page_title="Risk Guardian — Argus", page_icon="🛡️", layout="wide")
ui.inject_theme()
st.markdown("# 🛡️ Risk Guardian")
st.caption("Capital protection first. Argus sizes by volatility and conviction, and halts on drawdown.")

argus = ac.get_argus()
col = st.columns([2, 1, 1])
symbol = col[0].text_input("Symbol", "BTCUSDT")
capital = col[1].number_input("Capital (USD)", value=10_000.0, step=1000.0)
daily_pnl = col[2].slider("Today's PnL %", -8.0, 8.0, 0.0, 0.5) / 100.0

from core.scoring import compute_scores
snap = argus.data.get_snapshot(symbol.upper())
scores = compute_scores(snap)
risk = argus.risk.assess(snap, scores, capital_usd=capital, daily_pnl_pct=daily_pnl)

health_color = {"HEALTHY": "🟢", "CAUTION": "🟡", "CRITICAL": "🔴"}[risk.portfolio_health]
st.markdown(f"### Portfolio health: {health_color} **{risk.portfolio_health}**")

ui.meter("Risk", scores.risk, "higher = more dangerous", invert=True)

m = st.columns(4)
m[0].metric("Suggested size", f"${risk.suggested_position_usd:,.0f}", f"{risk.suggested_position_pct*100:.1f}% of capital")
m[1].metric("Max loss at stop", f"${risk.max_loss_usd:,.0f}")
m[2].metric("Reward : Risk", f"{risk.risk_reward:.2f}")
m[3].metric("Risk score", f"{risk.risk_score:.0f}/100")

st.markdown("#### Guardian notes")
for n in risk.notes:
    st.markdown(f"- {n}")

# --- Paper portfolio ---------------------------------------------------------
st.divider()
st.markdown("### 📂 Paper portfolio")
pf = argus.portfolio()
p = st.columns(4)
p[0].metric("Open positions", pf["open_count"])
p[1].metric("Closed", pf["closed_count"])
p[2].metric("Realized P&L", f"${pf['realized_pnl_usd']:,.2f}")
p[3].metric("Win / loss", f"{pf['wins']} / {pf['losses']}")

if pf["open_positions"]:
    st.markdown("#### Open positions")
    for pos in pf["open_positions"]:
        c = st.columns([3, 2, 2, 2])
        c[0].markdown(f"**{pos['symbol']}** {pos['direction']} · `{pos['trade_id']}`")
        c[1].caption(f"size ${pos['size_usd']:,.0f}")
        c[2].caption(f"fill {pos['fill_price']:,} · stop {pos['stop_loss']:,}")
        exit_price = c[3].number_input("Exit price", value=float(pos["take_profit"][0]),
                                       key=f"exit_{pos['trade_id']}", label_visibility="collapsed")
        if c[3].button("Close", key=f"close_{pos['trade_id']}"):
            done = argus.close_position(pos["trade_id"], exit_price)
            cp = done["position"]
            st.success(f"Closed {cp['symbol']} — P&L ${cp['pnl_usd']:,.2f} ({cp['pnl_pct']*100:.2f}%). "
                       f"{done['review']['outcome']}: {done['review']['lesson']}")
            st.rerun()
else:
    st.caption("No open paper positions. Approve a TAKE TRADE on the Trade Analysis page to open one.")

if pf["closed_positions"]:
    import pandas as pd
    st.markdown("#### Closed positions")
    cols = ["symbol", "direction", "fill_price", "exit_price", "pnl_usd", "pnl_pct", "size_usd"]
    df = pd.DataFrame(pf["closed_positions"])[cols]
    st.dataframe(df, use_container_width=True, hide_index=True)
