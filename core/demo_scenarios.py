"""Phase 8 & 9 — built-in demo scenarios and the signature WOW moment.

Each scenario is a hand-crafted MarketSnapshot that exercises a different facet
of the Signal Honesty Engine. They are deterministic, so a judge gets the same
unforgettable result every time.
"""
from __future__ import annotations

from typing import Dict

from core.models import MarketSnapshot, Direction


def _excellent_trade() -> MarketSnapshot:
    """Scenario A — everything aligns. Argus takes it."""
    return MarketSnapshot(
        symbol="BTCUSDT",
        price=64_000,
        direction_bias=Direction.LONG,
        timeframe_signals={"15m": 0.6, "1h": 0.7, "4h": 0.8, "1d": 0.7},
        adx=34, ema_stack="BULL", rsi=58, momentum=0.55, structure="UPTREND",
        atr_pct=1.4, volatility_score=42, liquidity_score=92, spread_bps=1.2,
        volume_score=0.85, indicator_completeness=1.0, data_freshness=1.0,
        support=62_400, resistance=68_500,
    )


def _weak_trade() -> MarketSnapshot:
    """Scenario B — looks ok, but the edge is thin. Argus watches."""
    return MarketSnapshot(
        symbol="ETHUSDT",
        price=3_100,
        direction_bias=Direction.LONG,
        timeframe_signals={"15m": 0.3, "1h": 0.1, "4h": 0.25, "1d": -0.1},
        adx=18, ema_stack="MIXED", rsi=54, momentum=0.15, structure="RANGE",
        atr_pct=1.1, volatility_score=48, liquidity_score=80, spread_bps=2.0,
        volume_score=0.5, indicator_completeness=1.0, data_freshness=1.0,
        support=3_050, resistance=3_180,
    )


def _low_liquidity_trap() -> MarketSnapshot:
    """Scenario C — attractive chart, but a slippage trap. Argus rejects."""
    return MarketSnapshot(
        symbol="PEPEUSDT",
        price=0.0000118,
        direction_bias=Direction.LONG,
        timeframe_signals={"15m": 0.7, "1h": 0.6, "4h": 0.55, "1d": 0.5},
        adx=31, ema_stack="BULL", rsi=63, momentum=0.6, structure="UPTREND",
        atr_pct=3.8, volatility_score=72, liquidity_score=28, spread_bps=14.0,
        volume_score=0.4, indicator_completeness=0.9, data_freshness=1.0,
        support=0.0000112, resistance=0.0000135,
    )


def _fomo_setup() -> MarketSnapshot:
    """Scenario D — parabolic, overbought, late. Argus refuses to chase."""
    return MarketSnapshot(
        symbol="SOLUSDT",
        price=210,
        direction_bias=Direction.LONG,
        timeframe_signals={"15m": 0.9, "1h": 0.85, "4h": 0.8, "1d": 0.7},
        adx=41, ema_stack="BULL", rsi=86, momentum=0.95, structure="UPTREND",
        atr_pct=4.6, volatility_score=83, liquidity_score=70, spread_bps=3.5,
        volume_score=0.95, indicator_completeness=1.0, data_freshness=1.0,
        support=183, resistance=214,
    )


def _missing_data() -> MarketSnapshot:
    """Scenario E — feeds are incomplete/stale. Argus refuses to guess."""
    return MarketSnapshot(
        symbol="BTCUSDT",
        price=64_000,
        direction_bias=Direction.LONG,
        timeframe_signals={"1h": 0.4},
        adx=22, ema_stack="MIXED", rsi=55, momentum=0.2, structure="RANGE",
        atr_pct=1.5, volatility_score=50, liquidity_score=60, spread_bps=2.5,
        volume_score=0.5, indicator_completeness=0.35, data_freshness=0.4,
        support=0.0, resistance=0.0,
    )


def _trend_exhaustion() -> MarketSnapshot:
    """Scenario F — strong trend but momentum diverging. Argus de-risks to WATCH."""
    return MarketSnapshot(
        symbol="BTCUSDT",
        price=71_000,
        direction_bias=Direction.LONG,
        timeframe_signals={"15m": -0.2, "1h": 0.2, "4h": 0.6, "1d": 0.7},
        adx=28, ema_stack="BULL", rsi=77, momentum=-0.1, structure="UPTREND",
        atr_pct=2.6, volatility_score=64, liquidity_score=85, spread_bps=1.8,
        volume_score=0.45, indicator_completeness=1.0, data_freshness=1.0,
        support=67_500, resistance=72_000,
    )


SCENARIOS: Dict[str, dict] = {
    "A": {"name": "Excellent trade", "factory": _excellent_trade,
          "teaches": "What a genuinely high-quality setup looks like."},
    "B": {"name": "Weak trade", "factory": _weak_trade,
          "teaches": "Mediocre signals are not opportunities — patience pays."},
    "C": {"name": "Low-liquidity trap", "factory": _low_liquidity_trap,
          "teaches": "A pretty chart on a thin book is a slippage trap."},
    "D": {"name": "FOMO setup", "factory": _fomo_setup,
          "teaches": "Chasing an overbought parabola is how accounts die."},
    "E": {"name": "Missing data", "factory": _missing_data,
          "teaches": "If you can't trust the inputs, you can't trust the trade."},
    "F": {"name": "Trend exhaustion", "factory": _trend_exhaustion,
          "teaches": "Strong trends end — momentum divergence is the tell."},
}


def get_scenario(key: str) -> MarketSnapshot:
    key = key.strip().upper()
    if key not in SCENARIOS:
        raise KeyError(f"Unknown scenario '{key}'. Choose one of {list(SCENARIOS)}.")
    return SCENARIOS[key]["factory"]()


# Phase 9 — the WOW moment: the FOMO setup most bots scream BUY on.
WOW_SCENARIO = "D"
WOW_NARRATIVE = (
    "A setup most bots would flash BUY on: +40% in a week, momentum screaming, "
    "every short-term signal green. Argus says NO TRADE — RSI 86 is exhausted, "
    "ATR 4.6% means a normal wiggle stops you out, and reward:risk is upside-down "
    "this late. Standing aside here is the trade."
)
