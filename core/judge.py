"""Phase 5 — Argus Judge Mode.

Every analysis produces a full, balanced verdict: a thesis, the bull and bear
cases, the scores, the precise levels, and an explicit account of why the trade
exists, why it could fail, and why it might be rejected — then a final decision.

Argus argues *against itself* before it ever argues for a trade.
"""
from __future__ import annotations

from typing import List

from core.models import (
    MarketSnapshot, Scores, Mode, Direction, JudgeReport, FinalDecision,
)
from core.scoring import compute_scores
from core.honesty_engine import evaluate
from core import explain


def _entry_zone(s: MarketSnapshot) -> List[float]:
    band = max(s.atr_pct, 0.2) / 100.0 * s.price * 0.5
    return [round(s.price - band, 2), round(s.price + band, 2)]


def _invalidation(s: MarketSnapshot) -> float:
    if s.direction_bias == Direction.LONG and s.support > 0:
        return round(s.support, 2)
    if s.direction_bias == Direction.SHORT and s.resistance > 0:
        return round(s.resistance, 2)
    atr = max(s.atr_pct, 0.2) / 100.0 * s.price
    return round(s.price - 1.5 * atr if s.direction_bias == Direction.LONG else s.price + 1.5 * atr, 2)


def _take_profit(s: MarketSnapshot) -> List[float]:
    atr = max(s.atr_pct, 0.2) / 100.0 * s.price
    if s.direction_bias == Direction.SHORT:
        return [round(s.price - 1.5 * atr, 2), round(s.price - 3 * atr, 2), round(s.price - 5 * atr, 2)]
    return [round(s.price + 1.5 * atr, 2), round(s.price + 3 * atr, 2), round(s.price + 5 * atr, 2)]


def _bull_case(s: MarketSnapshot, scores: Scores) -> List[str]:
    out = []
    if s.ema_stack == "BULL":
        out.append("EMA stack is bullish (20 > 50 > 200) — trend supports longs.")
    if s.adx >= 25:
        out.append(f"ADX {s.adx:.0f} shows a strong, directional trend.")
    if scores.confidence >= 65:
        out.append(f"Multi-timeframe agreement gives {scores.confidence:.0f}/100 confidence.")
    if s.momentum > 0.3:
        out.append("Positive momentum building.")
    if 40 <= s.rsi <= 65:
        out.append("RSI in a healthy band — room to run without being overbought.")
    if not out:
        out.append("Limited bullish evidence in current data.")
    return out


def _bear_case(s: MarketSnapshot, scores: Scores) -> List[str]:
    out = []
    if s.ema_stack == "BEAR":
        out.append("EMA stack is bearish — trend favours shorts / caution.")
    if s.volatility_score >= 65:
        out.append(f"Volatility {s.volatility_score:.0f}/100 raises the odds of a violent shakeout.")
    if s.liquidity_score < 55:
        out.append(f"Thin liquidity ({s.liquidity_score:.0f}/100) means slippage and trap risk.")
    if s.rsi >= 75:
        out.append("RSI overbought — chasing here is late-cycle.")
    if scores.risk >= 60:
        out.append(f"Overall risk {scores.risk:.0f}/100 is elevated.")
    if not out:
        out.append("No major structural red flags, but markets can always reverse.")
    return out


def judge(s: MarketSnapshot, mode: Mode = Mode.PROFESSIONAL, capital_usd: float = 10_000.0) -> JudgeReport:
    scores = compute_scores(s)
    verdict = evaluate(s, scores, capital_usd=capital_usd)

    thesis = (
        f"{s.symbol} is showing a {s.direction_bias.value.lower()} bias in a {s.structure.lower()} "
        f"structure. Confidence {scores.confidence:.0f}/100, risk {scores.risk:.0f}/100, "
        f"reward:risk {verdict.risk_reward:.2f}. Argus grades this a {verdict.setup_quality.value}."
    )

    why_exists = (
        f"The {s.direction_bias.value.lower()} case rests on "
        f"{'trend + momentum alignment' if scores.confidence >= 60 else 'early/partial signals'} "
        f"with ADX {s.adx:.0f} and an {s.ema_stack} EMA stack."
    )
    why_fail = (
        f"It fails if volatility ({s.volatility_score:.0f}/100) triggers a stop-run, "
        f"liquidity ({s.liquidity_score:.0f}/100) causes slippage, or price loses the "
        f"{_invalidation(s):,.2f} invalidation level."
    )
    if verdict.rejection_reasons:
        why_reject = "; ".join(verdict.rejection_reasons)
    else:
        why_reject = "No disqualifying conditions — the setup clears Argus' guardian gates."

    explanation = explain.render(
        mode, s, scores, verdict.final_decision, verdict.setup_quality,
        verdict.rejection_reasons, verdict.risk_reward,
    )

    return JudgeReport(
        symbol=s.symbol,
        price=s.price,
        direction=s.direction_bias,
        mode=mode,
        trade_thesis=thesis,
        bull_case=_bull_case(s, scores),
        bear_case=_bear_case(s, scores),
        why_trade_exists=why_exists,
        why_trade_could_fail=why_fail,
        why_trade_should_be_rejected=why_reject,
        scores=scores,
        setup_quality=verdict.setup_quality,
        final_decision=verdict.final_decision,
        entry_zone=_entry_zone(s),
        invalidation_zone=_invalidation(s),
        take_profit=_take_profit(s),
        rejection_reasons=verdict.rejection_reasons,
        is_no_trade_alpha=verdict.is_no_trade_alpha,
        capital_protection_note=verdict.capital_protection_note,
        explanation=explanation,
    )
