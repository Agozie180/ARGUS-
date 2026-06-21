"""Reusable Streamlit UI components for the Argus web app.

A Bloomberg-terminal-meets-AI-copilot aesthetic: dark, dense, meter-driven.
Each function renders directly into the active Streamlit context.
"""
from __future__ import annotations

from typing import Dict

import streamlit as st


# --- palette -----------------------------------------------------------------
GREEN = "#16c784"
YELLOW = "#f3ba2f"
ORANGE = "#ff8a00"
RED = "#ea3943"
BLUE = "#2f80ed"
MUTED = "#8a8f98"

DECISION_STYLE = {
    "TAKE TRADE": (GREEN, "✅"),
    "WATCH": (YELLOW, "👀"),
    "REJECT": (RED, "⛔"),
    "NO TRADE": (RED, "🛡️"),
}
SETUP_STYLE = {
    "HIGH QUALITY SETUP": GREEN,
    "POSSIBLE SETUP": YELLOW,
    "WATCH": ORANGE,
    "REJECT": RED,
}


def inject_theme() -> None:
    st.markdown(
        """
        <style>
        .stApp { background-color: #0b0e11; color: #eaecef; }
        .argus-card { background:#161a1e; border:1px solid #2b3139; border-radius:12px;
                      padding:16px 18px; margin-bottom:14px; }
        .argus-meter-track { background:#2b3139; border-radius:6px; height:14px; width:100%; }
        .argus-badge { display:inline-block; padding:6px 14px; border-radius:8px;
                       font-weight:700; letter-spacing:.5px; }
        h1,h2,h3 { color:#eaecef; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _color_for(value: float, invert: bool = False) -> str:
    v = 100 - value if invert else value
    if v >= 75:
        return GREEN
    if v >= 55:
        return YELLOW
    if v >= 40:
        return ORANGE
    return RED


def meter(label: str, value: float, sub: str = "", invert: bool = False) -> None:
    """Horizontal meter. `invert=True` for risk (high = bad = red)."""
    color = _color_for(value, invert=invert)
    width = max(0, min(100, int(value)))
    st.markdown(
        f"""
        <div style="margin-bottom:12px;">
          <div style="display:flex;justify-content:space-between;font-size:13px;">
            <span style="font-weight:600;">{label}</span><span>{value:.0f}/100</span>
          </div>
          <div class="argus-meter-track">
            <div style="background:{color};border-radius:6px;height:14px;width:{width}%;"></div>
          </div>
          <div style="font-size:11px;color:{MUTED};margin-top:2px;">{sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def decision_badge(decision: str, setup: str = "") -> None:
    color, icon = DECISION_STYLE.get(decision, (MUTED, "•"))
    setup_color = SETUP_STYLE.get(setup, MUTED)
    extra = f"<span class='argus-badge' style='background:{setup_color}22;color:{setup_color};margin-left:8px;'>{setup}</span>" if setup else ""
    st.markdown(
        f"<span class='argus-badge' style='background:{color}22;color:{color};font-size:18px;'>{icon} {decision}</span>{extra}",
        unsafe_allow_html=True,
    )


def four_meters(scores: Dict[str, float]) -> None:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        meter("Confidence", scores.get("confidence", 0), "edge alignment")
    with c2:
        meter("Risk", scores.get("risk", 0), "higher = more dangerous", invert=True)
    with c3:
        meter("Data Quality", scores.get("data_quality", 0), "can we trust inputs?")
    with c4:
        meter("Trade Quality", scores.get("trade_quality", 0), "composite verdict")


def no_trade_alpha_banner(capital_protected: float, note: str) -> None:
    st.markdown(
        f"""
        <div class="argus-card" style="border-color:{GREEN};">
          <div style="font-size:20px;font-weight:800;color:{GREEN};">NO TRADE IS ALPHA™</div>
          <div style="margin-top:6px;">{note}</div>
          <div style="margin-top:8px;font-size:28px;font-weight:800;color:{GREEN};">
            ${capital_protected:,.0f} <span style="font-size:13px;color:{MUTED};">capital protected</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
