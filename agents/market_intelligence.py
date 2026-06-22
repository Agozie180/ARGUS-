"""Agent 1 — Market Intelligence.

Reads a MarketSnapshot and produces a structured market understanding:
multi-timeframe, trend, volatility, liquidity, structure and momentum.
It describes the market; it does not decide whether to trade.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List

from core.models import MarketSnapshot, Direction


@dataclass
class MarketIntelligence:
    symbol: str
    direction_bias: str
    trend: str
    timeframe_alignment: float       # % of timeframes agreeing
    volatility: str
    liquidity: str
    structure: str
    momentum: str
    headline: str
    observations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class MarketIntelligenceAgent:
    name = "Market Intelligence"

    def analyze(self, s: MarketSnapshot) -> MarketIntelligence:
        sigs = list(s.timeframe_signals.values())
        if sigs:
            bull = sum(1 for v in sigs if v > 0.2)
            bear = sum(1 for v in sigs if v < -0.2)
            alignment = round(max(bull, bear) / len(sigs) * 100, 1)
        else:
            alignment = 0.0

        trend = "Strong" if s.adx >= 30 else "Developing" if s.adx >= 20 else "Weak/None"
        volatility = (
            "Extreme" if s.volatility_score >= 75 else
            "Elevated" if s.volatility_score >= 55 else
            "Normal" if s.volatility_score >= 35 else "Calm"
        )
        liquidity = (
            "Deep" if s.liquidity_score >= 75 else
            "Adequate" if s.liquidity_score >= 55 else
            "Thin" if s.liquidity_score >= 40 else "Illiquid"
        )
        momentum = (
            "Accelerating" if s.momentum >= 0.4 else
            "Positive" if s.momentum > 0.1 else
            "Fading" if s.momentum > -0.1 else "Negative"
        )

        obs: List[str] = []
        obs.append(f"{trend.lower()} trend (ADX {s.adx:.0f}), EMA stack {s.ema_stack}.")
        obs.append(f"{volatility.lower()} volatility (ATR {s.atr_pct:.1f}%).")
        obs.append(f"{liquidity.lower()} liquidity (spread {s.spread_bps:.1f}bps).")
        if s.rsi >= 75:
            obs.append(f"RSI {s.rsi:.0f} — overbought.")
        elif s.rsi <= 25:
            obs.append(f"RSI {s.rsi:.0f} — oversold.")
        obs.append(f"{alignment:.0f}% timeframe alignment toward {s.direction_bias.value.lower()}.")

        headline = (
            f"{s.symbol}: {s.direction_bias.value.lower()} bias, {trend.lower()} trend, "
            f"{volatility.lower()} volatility, {liquidity.lower()} liquidity."
        )

        return MarketIntelligence(
            symbol=s.symbol,
            direction_bias=s.direction_bias.value,
            trend=trend,
            timeframe_alignment=alignment,
            volatility=volatility,
            liquidity=liquidity,
            structure=s.structure,
            momentum=momentum,
            headline=headline,
            observations=obs,
        )
