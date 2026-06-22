"""Deterministic, explainable scoring for Argus.

Four meters, all 0–100:
  - data_quality : can we even trust the inputs?
  - confidence   : how aligned is the edge?
  - risk         : how dangerous is this trade right now? (higher = worse)
  - trade_quality: the composite, gated by data quality and risk.

Every score returns its component breakdown so the UI and Judge Mode can
explain *why* — Argus never shows a number it cannot justify.
"""
from __future__ import annotations

from typing import Dict, Tuple

from core.models import MarketSnapshot, Scores, Direction


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def score_data_quality(s: MarketSnapshot) -> Tuple[float, Dict[str, float]]:
    """Are the inputs complete, fresh and liquid enough to reason about?"""
    completeness = _clamp(s.indicator_completeness * 100)
    freshness = _clamp(s.data_freshness * 100)
    liquidity = _clamp(s.liquidity_score)
    # Wide spreads quietly destroy data quality.
    spread_penalty = _clamp(100 - (s.spread_bps * 5))

    components = {
        "indicator_completeness": completeness,
        "data_freshness": freshness,
        "liquidity": liquidity,
        "spread_quality": spread_penalty,
    }
    score = (
        0.30 * completeness
        + 0.25 * freshness
        + 0.30 * liquidity
        + 0.15 * spread_penalty
    )
    return _clamp(score), components


def score_confidence(s: MarketSnapshot) -> Tuple[float, Dict[str, float]]:
    """How much real, aligned edge is there?"""
    signals = list(s.timeframe_signals.values())
    if signals:
        bullish = sum(1 for v in signals if v > 0.2)
        bearish = sum(1 for v in signals if v < -0.2)
        agreement = max(bullish, bearish) / len(signals) * 100
    else:
        agreement = 0.0

    trend_strength = _clamp((s.adx / 40.0) * 100)   # ADX 40+ = very strong
    stack_bonus = 100.0 if s.ema_stack in ("BULL", "BEAR") else 40.0
    momentum_score = _clamp((abs(s.momentum)) * 100)

    # Penalise stretched RSI — chasing extremes is not confidence.
    if s.rsi >= 80 or s.rsi <= 20:
        rsi_quality = 35.0
    elif 40 <= s.rsi <= 60:
        rsi_quality = 90.0
    else:
        rsi_quality = 70.0

    components = {
        "timeframe_agreement": agreement,
        "trend_strength_adx": trend_strength,
        "ema_stack": stack_bonus,
        "momentum": momentum_score,
        "rsi_quality": rsi_quality,
    }
    score = (
        0.35 * agreement
        + 0.25 * trend_strength
        + 0.15 * stack_bonus
        + 0.15 * momentum_score
        + 0.10 * rsi_quality
    )
    return _clamp(score), components


def score_risk(s: MarketSnapshot) -> Tuple[float, Dict[str, float]]:
    """Higher = more dangerous. Volatility, illiquidity and overextension drive it."""
    vol_risk = _clamp(s.volatility_score)
    atr_risk = _clamp((s.atr_pct / 5.0) * 100)        # 5% ATR = max risk
    illiquidity_risk = _clamp(100 - s.liquidity_score)
    spread_risk = _clamp(s.spread_bps * 5)

    # Overextension: stretched RSI in the direction of the bias is dangerous.
    overext = 0.0
    if s.direction_bias == Direction.LONG and s.rsi >= 75:
        overext = (s.rsi - 75) / 25.0 * 100
    elif s.direction_bias == Direction.SHORT and s.rsi <= 25:
        overext = (25 - s.rsi) / 25.0 * 100
    overext = _clamp(overext)

    components = {
        "volatility": vol_risk,
        "atr": atr_risk,
        "illiquidity": illiquidity_risk,
        "spread": spread_risk,
        "overextension": overext,
    }
    score = (
        0.30 * vol_risk
        + 0.20 * atr_risk
        + 0.25 * illiquidity_risk
        + 0.10 * spread_risk
        + 0.15 * overext
    )
    return _clamp(score), components


def score_trade_quality(confidence: float, data_quality: float, risk: float) -> Tuple[float, Dict[str, float]]:
    """Composite. A great-looking signal on untrustworthy data is not a trade."""
    # Data quality acts as a multiplier — you cannot trade what you cannot trust.
    dq_multiplier = data_quality / 100.0
    base = (confidence * 0.7) + ((100 - risk) * 0.3)
    quality = base * dq_multiplier
    components = {
        "edge_component": confidence * 0.7,
        "safety_component": (100 - risk) * 0.3,
        "data_quality_multiplier": dq_multiplier * 100,
    }
    return _clamp(quality), components


def compute_scores(s: MarketSnapshot) -> Scores:
    dq, dq_c = score_data_quality(s)
    conf, conf_c = score_confidence(s)
    risk, risk_c = score_risk(s)
    tq, tq_c = score_trade_quality(conf, dq, risk)

    components: Dict[str, float] = {}
    for prefix, comp in (
        ("data_quality", dq_c),
        ("confidence", conf_c),
        ("risk", risk_c),
        ("trade_quality", tq_c),
    ):
        for k, v in comp.items():
            components[f"{prefix}.{k}"] = round(v, 1)

    return Scores(
        confidence=round(conf, 1),
        risk=round(risk, 1),
        data_quality=round(dq, 1),
        trade_quality=round(tq, 1),
        components=components,
    )
