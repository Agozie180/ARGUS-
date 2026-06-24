"""Reusable Streamlit UI components for the Argus web app.

A Bloomberg-terminal-meets-AI-copilot aesthetic: dark, dense, meter-driven.
Each function renders directly into the active Streamlit context.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

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


def cps_hero(cps: Dict) -> None:
    """The signature Capital Protection Score — displayed prominently."""
    score = cps.get("cps", 0)
    grade = cps.get("grade", "–")
    color = _color_for(score)
    st.markdown(
        f"""
        <div class="argus-card" style="border-color:{color};">
          <div style="display:flex;justify-content:space-between;align-items:baseline;">
            <span style="font-size:13px;letter-spacing:.5px;color:{MUTED};">CAPITAL PROTECTION SCORE™</span>
            <span style="font-weight:700;color:{color};">Grade {grade}</span>
          </div>
          <div style="font-size:46px;font-weight:800;color:{color};line-height:1.1;">
            {score:.0f}<span style="font-size:18px;color:{MUTED};">/100</span>
          </div>
          <div class="argus-meter-track" style="margin-top:6px;">
            <div style="background:{color};border-radius:6px;height:14px;width:{max(0,min(100,int(score)))}%;"></div>
          </div>
          <div style="margin-top:8px;font-size:13px;color:#cfd3d8;">{cps.get('headline','')}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def cps_meter(cps: Dict) -> None:
    """Compact CPS meter for sidebars / meter rows."""
    meter("Capital Protection Score", cps.get("cps", 0),
          f"Grade {cps.get('grade','–')} • {cps.get('trades_rejected',0)} rejected")


def cps_breakdown(cps: Dict) -> None:
    """The five tracked guardian behaviours behind the CPS."""
    c = st.columns(4)
    c[0].metric("💰 Losses avoided", f"${cps.get('potential_loss_avoided_usd',0):,.0f}")
    c[1].metric("📉 Exposure avoided", f"${cps.get('risk_exposure_avoided_usd',0):,.0f}")
    c[2].metric("🚀 FOMO blocked", cps.get("fomo_blocked", 0))
    c[3].metric("💧 Liquidity traps", cps.get("liquidity_traps_avoided", 0))


def watchlist(rows: List[Dict]) -> None:
    """Compact watchlist: symbol, decision badge, key meters."""
    st.markdown("#### 👁 Watchlist")
    for r in rows:
        color, icon = DECISION_STYLE.get(r.get("decision", ""), (MUTED, "•"))
        st.markdown(
            f"""
            <div class="argus-card" style="padding:10px 14px;margin-bottom:8px;
                 display:flex;justify-content:space-between;align-items:center;">
              <span style="font-weight:700;font-size:15px;">{r.get('symbol','')}</span>
              <span style="color:{MUTED};font-size:12px;">conf {r.get('confidence',0):.0f} ·
                    risk {r.get('risk',0):.0f} · TQ {r.get('trade_quality',0):.0f}</span>
              <span class="argus-badge" style="background:{color}22;color:{color};">{icon} {r.get('decision','')}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


def live_data_badge(live: bool, detail: str = "") -> None:
    """Green 'Live Bitget Data' badge when real data is flowing, amber on fallback."""
    if live:
        color, icon, label = GREEN, "🟢", "LIVE BITGET DATA"
    else:
        color, icon, label = YELLOW, "🟡", "DEMO MODE (BITGET UNAVAILABLE)"
    extra = f"<span style='color:{MUTED};font-size:12px;margin-left:10px;'>{detail}</span>" if detail else ""
    st.markdown(
        f"<span class='argus-badge' style='background:{color}22;color:{color};'>{icon} {label}</span>{extra}",
        unsafe_allow_html=True,
    )


def _fmt_ts(fetched_at: Optional[float]) -> str:
    if not fetched_at:
        return "—"
    try:
        return datetime.fromtimestamp(float(fetched_at), tz=timezone.utc).strftime("%H:%M:%S UTC")
    except (TypeError, ValueError, OSError):
        return "—"


def data_provenance(source: str, market_type: str = "spot",
                    fetched_at: Optional[float] = None, detail: str = "") -> None:
    """The required data-provenance strip shown on every live analysis.

    Honest by construction: a BITGET_LIVE source renders a green 'Live Bitget
    Market Data' status; anything else renders an amber 'DEMO DATA' status so a
    simulated price is never presented as live.
    """
    live = str(source).upper() == "BITGET_LIVE"
    color = GREEN if live else YELLOW
    status = "🟢 Live Bitget Market Data" if live else "🟡 DEMO DATA"
    src_label = "Bitget" if live else "Simulated (Bitget unavailable)"
    updated = _fmt_ts(fetched_at) if live else "n/a (offline fallback)"
    mtype = (market_type or "spot").capitalize()
    extra = f"<div style='color:{MUTED};font-size:11px;margin-top:6px;'>{detail}</div>" if detail else ""
    st.markdown(
        f"""
        <div class="argus-card" style="border-color:{color};padding:12px 16px;">
          <div style="display:flex;flex-wrap:wrap;gap:18px;align-items:center;font-size:13px;">
            <span style="font-weight:800;color:{color};letter-spacing:.3px;">{status}</span>
            <span style="color:{MUTED};">Source:</span> <span style="font-weight:600;">{src_label}</span>
            <span style="color:{MUTED};">Market:</span> <span style="font-weight:600;">{mtype}</span>
            <span style="color:{MUTED};">Last updated:</span> <span style="font-weight:600;">{updated}</span>
          </div>{extra}
        </div>
        """,
        unsafe_allow_html=True,
    )


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
