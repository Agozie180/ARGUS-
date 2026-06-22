"""Agent 2 — Risk Guardian.

Capital protection first. Scores risk, monitors drawdown, sizes positions by
volatility and confidence, and reports portfolio health. It can shrink or veto
size even when the setup is valid.
"""
from __future__ import annotations

from typing import List

from core.models import MarketSnapshot, Scores, RiskAssessment, Direction


class RiskGuardianAgent:
    name = "Risk Guardian"

    def __init__(self, max_position_pct: float = 0.10, risk_budget_pct: float = 0.01,
                 max_daily_drawdown_pct: float = 0.05):
        self.max_position_pct = max_position_pct
        self.risk_budget_pct = risk_budget_pct          # risk per trade
        self.max_daily_drawdown_pct = max_daily_drawdown_pct

    def assess(self, s: MarketSnapshot, scores: Scores, capital_usd: float = 10_000.0,
               daily_pnl_pct: float = 0.0, consecutive_losses: int = 0) -> RiskAssessment:
        notes: List[str] = []

        # Distance to invalidation (stop) as a fraction of price.
        if s.direction_bias == Direction.LONG and s.support > 0:
            stop_dist = max((s.price - s.support) / s.price, 0.005)
        elif s.direction_bias == Direction.SHORT and s.resistance > 0:
            stop_dist = max((s.resistance - s.price) / s.price, 0.005)
        else:
            stop_dist = max(s.atr_pct / 100 * 1.5, 0.005)

        # Volatility-targeted sizing: risk_budget / stop distance.
        raw_pct = self.risk_budget_pct / stop_dist
        # Scale by conviction and inverse risk.
        raw_pct *= (scores.confidence / 100.0)
        raw_pct *= (1 - scores.risk / 200.0)

        # Discipline overlays.
        if consecutive_losses >= 2:
            raw_pct *= 0.5
            notes.append("2+ consecutive losses — size halved (revenge-trade guard).")
        if scores.data_quality < 60:
            raw_pct *= 0.5
            notes.append("Low data quality — size halved.")

        position_pct = max(0.0, min(self.max_position_pct, raw_pct))
        position_usd = capital_usd * position_pct
        max_loss = position_usd * stop_dist
        rr = self._risk_reward(s)

        # Portfolio health from drawdown.
        if daily_pnl_pct <= -self.max_daily_drawdown_pct:
            health = "CRITICAL"
            position_pct, position_usd, max_loss = 0.0, 0.0, 0.0
            notes.append(f"Daily drawdown limit ({self.max_daily_drawdown_pct:.0%}) hit — trading halted.")
        elif daily_pnl_pct <= -self.max_daily_drawdown_pct / 2:
            health = "CAUTION"
            notes.append("Approaching daily drawdown limit — defensive sizing.")
        else:
            health = "HEALTHY"

        if not notes:
            notes.append("Within all risk limits.")

        return RiskAssessment(
            risk_score=scores.risk,
            suggested_position_pct=round(position_pct, 4),
            suggested_position_usd=round(position_usd, 2),
            risk_reward=rr,
            max_loss_usd=round(max_loss, 2),
            portfolio_health=health,
            notes=notes,
        )

    @staticmethod
    def _risk_reward(s: MarketSnapshot) -> float:
        if s.direction_bias == Direction.LONG and s.resistance > s.price > s.support > 0:
            reward, risk = s.resistance - s.price, s.price - s.support
        elif s.direction_bias == Direction.SHORT and s.support > 0 and s.resistance > s.price:
            reward, risk = s.price - s.support, s.resistance - s.price
        else:
            atr = max(s.atr_pct, 0.1) / 100 * s.price
            reward, risk = atr * 2, atr
        return round(reward / risk, 2) if risk > 0 else 0.0
