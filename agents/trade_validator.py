"""Agent 3 — Trade Validator.

The gatekeeper. Validates every candidate trade against the Signal Honesty
Engine and surfaces explicit pass/fail checks. Rejecting weak setups is its
primary job — it is proud to say NO.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List

from core.models import MarketSnapshot, Scores, SetupQuality, FinalDecision
from core.honesty_engine import (
    evaluate, DATA_QUALITY_FLOOR, LIQUIDITY_FLOOR, RISK_CEILING, RR_FLOOR,
)


@dataclass
class ValidationResult:
    setup_quality: str
    final_decision: str
    passed: bool
    checks: Dict[str, bool]
    rejection_reasons: List[str] = field(default_factory=list)
    risk_reward: float = 0.0
    is_no_trade_alpha: bool = False
    capital_protection_note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class TradeValidatorAgent:
    name = "Trade Validator"

    def validate(self, s: MarketSnapshot, scores: Scores, capital_usd: float = 10_000.0) -> ValidationResult:
        verdict = evaluate(s, scores, capital_usd=capital_usd)

        sigs = list(s.timeframe_signals.values())
        bull = sum(1 for v in sigs if v > 0.2)
        bear = sum(1 for v in sigs if v < -0.2)
        conflict = bull > 0 and bear > 0 and abs(bull - bear) <= 1

        checks = {
            "data_trustworthy": scores.data_quality >= DATA_QUALITY_FLOOR,
            "liquidity_ok": s.liquidity_score >= LIQUIDITY_FLOOR,
            "risk_acceptable": scores.risk <= RISK_CEILING,
            "risk_reward_ok": verdict.risk_reward >= RR_FLOOR,
            "signals_aligned": not conflict,
            "has_direction": s.direction_bias.value != "NEUTRAL",
        }
        passed = verdict.final_decision == FinalDecision.TAKE_TRADE

        return ValidationResult(
            setup_quality=verdict.setup_quality.value,
            final_decision=verdict.final_decision.value,
            passed=passed,
            checks=checks,
            rejection_reasons=verdict.rejection_reasons,
            risk_reward=verdict.risk_reward,
            is_no_trade_alpha=verdict.is_no_trade_alpha,
            capital_protection_note=verdict.capital_protection_note,
        )
