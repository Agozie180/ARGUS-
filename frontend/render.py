"""Shared rendering for a full Argus analysis result (used across pages)."""
from __future__ import annotations

from typing import Any, Dict

import streamlit as st

from dashboard import components as ui


def render_analysis(result: Dict[str, Any]) -> None:
    judge = result["judge"]
    scores = result["scores"]
    val = result["validation"]

    # Required data-provenance strip — proves Bitget sourcing (or honestly
    # discloses the simulated fallback) on every single analysis.
    ui.data_provenance(
        source=result.get("data_source", "SIMULATED"),
        market_type=result.get("market_type", "spot"),
        fetched_at=result.get("fetched_at"),
    )

    top = st.columns([2, 1])
    with top[0]:
        st.markdown(f"### {judge['symbol']} @ {judge['price']:,}")
        ui.decision_badge(judge["final_decision"], judge["setup_quality"])
    with top[1]:
        st.caption(
            f"Data: {result['data_mode']}  •  Direction: {judge['direction']}  •  "
            f"Session: {judge.get('session','?')} (take ≥{judge.get('confidence_threshold',0):.0f}%)"
        )

    st.markdown("#### Argus Meters")
    ui.four_meters(scores)

    if val.get("is_no_trade_alpha"):
        ui.no_trade_alpha_banner(result.get("capital_protected_usd", 0.0),
                                 judge.get("capital_protection_note", ""))

    st.markdown("#### Trade Thesis")
    st.write(judge["trade_thesis"])

    a1, a2, a3 = st.columns(3)
    a1.markdown(f"**🏗 Market structure**\n\n{judge['market_structure']}")
    a2.markdown(f"**💧 Liquidity**\n\n{judge['liquidity_analysis']}")
    a3.markdown(f"**🌊 Volatility**\n\n{judge['volatility_analysis']}")

    st.markdown(f"**🛡 Capital Protection Impact:** {judge['capital_protection_impact']}")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**🐂 Bull case**")
        for b in judge["bull_case"]:
            st.markdown(f"- {b}")
    with c2:
        st.markdown("**🐻 Bear case**")
        for b in judge["bear_case"]:
            st.markdown(f"- {b}")

    st.markdown("#### Judge Mode")
    jc = st.columns(3)
    jc[0].metric("Entry zone", f"{judge['entry_zone'][0]:,} – {judge['entry_zone'][1]:,}")
    jc[1].metric("Invalidation", f"{judge['invalidation_zone']:,}")
    jc[2].metric("Reward:Risk", f"{val.get('risk_reward', 0):.2f}")
    st.caption("Take-profit ladder: " + ", ".join(f"{t:,}" for t in judge["take_profit"]))

    with st.expander("Why this trade exists / could fail / should be rejected", expanded=True):
        st.markdown(f"**Why it exists:** {judge['why_trade_exists']}")
        st.markdown(f"**Why it could fail:** {judge['why_trade_could_fail']}")
        st.markdown(f"**Why it could be rejected:** {judge['why_trade_should_be_rejected']}")

    st.markdown("**🔧 What would improve this setup**")
    for cond in judge.get("what_would_improve", []):
        st.markdown(f"- {cond}")

    st.markdown("#### Explanation")
    st.code(judge["explanation"], language="text")
