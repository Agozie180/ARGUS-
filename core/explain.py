"""Phase 6 — Explainability.

Every Argus decision must be understandable and every analysis should teach.
Two registers:
  - BEGINNER     : plain language, no jargon, focuses on the "so what".
  - PROFESSIONAL : the technical reasoning, scores and levels.
"""
from __future__ import annotations

from typing import List

from core.models import MarketSnapshot, Scores, Mode, FinalDecision, SetupQuality


_DECISION_PLAIN = {
    FinalDecision.TAKE_TRADE: "This looks like a genuinely good opportunity worth taking.",
    FinalDecision.WATCH: "This is interesting but not ready — keep an eye on it, don't act yet.",
    FinalDecision.REJECT: "Avoid this one. The downside outweighs the upside.",
    FinalDecision.NO_TRADE: "Do nothing here. Sitting out IS the smart move right now.",
}


def explain_beginner(s: MarketSnapshot, scores: Scores, decision: FinalDecision,
                     setup: SetupQuality, reasons: List[str]) -> str:
    lines = [
        f"📊 {s.symbol} — Argus says: **{decision.value}**",
        "",
        _DECISION_PLAIN[decision],
        "",
        "In plain English:",
        f"• How sure are we? {_band(scores.confidence)} ({scores.confidence:.0f}/100)",
        f"• How risky is it? {_risk_band(scores.risk)} ({scores.risk:.0f}/100)",
        f"• Can we trust the data? {_band(scores.data_quality)} ({scores.data_quality:.0f}/100)",
    ]
    if reasons:
        lines += ["", "Why:", *[f"• {_simplify(r)}" for r in reasons[:3]]]
    if decision in (FinalDecision.NO_TRADE, FinalDecision.REJECT):
        lines += ["", "💡 Remember: avoiding a bad trade keeps your money safe. That's a win."]
    return "\n".join(lines)


def explain_professional(s: MarketSnapshot, scores: Scores, decision: FinalDecision,
                         setup: SetupQuality, reasons: List[str], rr: float) -> str:
    lines = [
        f"{s.symbol} @ {s.price:,.2f} — bias {s.direction_bias.value} | setup {setup.value} | decision {decision.value}",
        "",
        "Scores:",
        f"  confidence={scores.confidence:.1f}  risk={scores.risk:.1f}  "
        f"data_quality={scores.data_quality:.1f}  trade_quality={scores.trade_quality:.1f}  RR={rr:.2f}",
        "",
        "Market structure:",
        f"  ADX={s.adx:.1f}  EMA_stack={s.ema_stack}  RSI={s.rsi:.1f}  "
        f"ATR%={s.atr_pct:.2f}  vol_score={s.volatility_score:.0f}  liq={s.liquidity_score:.0f}",
        f"  structure={s.structure}  momentum={s.momentum:+.2f}  spread={s.spread_bps:.1f}bps",
    ]
    if s.timeframe_signals:
        tf = "  ".join(f"{k}:{v:+.2f}" for k, v in s.timeframe_signals.items())
        lines.append(f"  timeframes: {tf}")
    if reasons:
        lines += ["", "Reasoning trace:", *[f"  - {r}" for r in reasons]]
    return "\n".join(lines)


def render(mode: Mode, s: MarketSnapshot, scores: Scores, decision: FinalDecision,
           setup: SetupQuality, reasons: List[str], rr: float) -> str:
    if mode == Mode.BEGINNER:
        return explain_beginner(s, scores, decision, setup, reasons)
    return explain_professional(s, scores, decision, setup, reasons, rr)


# --- helpers -----------------------------------------------------------------
def _band(v: float) -> str:
    if v >= 80:
        return "Very high"
    if v >= 65:
        return "Good"
    if v >= 50:
        return "Moderate"
    if v >= 35:
        return "Low"
    return "Very low"


def _risk_band(v: float) -> str:
    if v >= 78:
        return "Dangerous"
    if v >= 60:
        return "Elevated"
    if v >= 40:
        return "Moderate"
    return "Contained"


def _simplify(reason: str) -> str:
    """Strip the numbers/jargon from an engine reason for beginners."""
    table = {
        "Data quality": "We don't have reliable enough information",
        "Liquidity": "This market is too thin to enter safely",
        "Risk": "Conditions are too dangerous right now",
        "Reward:risk": "The potential reward isn't worth the risk",
        "Timeframes conflict": "Different timeframes disagree on direction",
        "No directional bias": "The market hasn't picked a direction",
    }
    for key, plain in table.items():
        if reason.startswith(key):
            return plain
    return reason
