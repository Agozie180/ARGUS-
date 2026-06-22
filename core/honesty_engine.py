"""Phase 4 — The Signal Honesty Engine.

This is the core innovation. Argus must *never* force a signal. Before any
recommendation it interrogates the setup and is proud to reject it.

Hard gates (any one fails -> the trade cannot be HIGH QUALITY, and usually
becomes NO TRADE):
  - data quality floor      (can't trade what you can't trust)
  - liquidity floor         (illiquid = slippage trap)
  - risk ceiling            (too dangerous regardless of edge)
  - signal conflict check   (timeframes disagree)
  - risk-reward floor       (the math has to pay)

"NO TRADE IS ALPHA™": when Argus rejects, it quantifies the capital it just
protected, because avoiding a bad trade is a positive outcome, not an absence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from core.models import MarketSnapshot, Scores, SetupQuality, FinalDecision, Direction
from core.sessions import (
    TradingSession, current_session, confidence_threshold, SESSION_LABEL,
)


# --- Tunable guardian thresholds ---------------------------------------------
DATA_QUALITY_FLOOR = 55.0      # below this we are blind
LIQUIDITY_FLOOR = 45.0         # below this slippage eats the edge
RISK_CEILING = 78.0            # above this, no edge is worth it
CONFIDENCE_TRADE = 70.0        # default conviction floor (session-aware at runtime)
CONFIDENCE_POSSIBLE = 55.0     # confidence needed to call it a setup
RR_FLOOR = 1.5                 # minimum acceptable reward:risk
TRADE_QUALITY_TAKE = 68.0      # trade-quality needed for HIGH QUALITY SETUP


@dataclass
class HonestyVerdict:
    setup_quality: SetupQuality
    final_decision: FinalDecision
    rejection_reasons: List[str]
    is_no_trade_alpha: bool
    risk_reward: float
    capital_protection_note: str
    # Capital Protection Score inputs — which specific dangers were avoided, and
    # the quantified exposure / downside that standing aside protected.
    protection_categories: List[str] = field(default_factory=list)
    exposure_usd: float = 0.0
    loss_avoided_usd: float = 0.0
    # Session-aware conviction gate + what would turn this into a trade.
    session: str = ""
    confidence_threshold: float = CONFIDENCE_TRADE
    improvement_conditions: List[str] = field(default_factory=list)


def _risk_reward(s: MarketSnapshot) -> float:
    """Reward:risk from entry to nearest target vs invalidation."""
    if s.direction_bias == Direction.LONG and s.resistance > s.price > s.support > 0:
        reward = s.resistance - s.price
        risk = s.price - s.support
    elif s.direction_bias == Direction.SHORT and 0 < s.resistance < s.price < float("inf") and s.support > s.price:
        # short: target below, invalidation above
        reward = s.price - s.support
        risk = s.resistance - s.price
    else:
        # fall back to ATR-based 2R assumption when levels are missing
        atr = max(s.atr_pct, 0.1) / 100.0 * s.price
        reward, risk = atr * 2, atr
    if risk <= 0:
        return 0.0
    return round(reward / risk, 2)


def evaluate(s: MarketSnapshot, scores: Scores, capital_usd: float = 10_000.0,
             session: Optional[TradingSession] = None) -> HonestyVerdict:
    reasons: List[str] = []
    rr = _risk_reward(s)

    # Session-aware conviction gate: Asian 65 / London 72 / New York 75.
    session = session or current_session()
    conf_trade = confidence_threshold(session)

    # --- Hard gates -----------------------------------------------------------
    blind = scores.data_quality < DATA_QUALITY_FLOOR
    illiquid = s.liquidity_score < LIQUIDITY_FLOOR
    too_risky = scores.risk > RISK_CEILING
    bad_rr = rr < RR_FLOOR

    # FOMO chase: stretched RSI into elevated volatility, in the trade direction.
    fomo_chase = False
    if s.direction_bias == Direction.LONG and s.rsi >= 82 and (s.atr_pct >= 3.5 or s.volatility_score >= 78):
        fomo_chase = True
    elif s.direction_bias == Direction.SHORT and s.rsi <= 18 and (s.atr_pct >= 3.5 or s.volatility_score >= 78):
        fomo_chase = True

    # Signal conflict: meaningful disagreement across timeframes.
    sigs = list(s.timeframe_signals.values())
    conflict = False
    if sigs:
        bullish = sum(1 for v in sigs if v > 0.2)
        bearish = sum(1 for v in sigs if v < -0.2)
        conflict = bullish > 0 and bearish > 0 and abs(bullish - bearish) <= 1

    no_direction = s.direction_bias == Direction.NEUTRAL

    if blind:
        reasons.append(f"Data quality {scores.data_quality:.0f}/100 below floor {DATA_QUALITY_FLOOR:.0f} — inputs cannot be trusted.")
    if illiquid:
        reasons.append(f"Liquidity {s.liquidity_score:.0f}/100 below floor {LIQUIDITY_FLOOR:.0f} — high slippage / trap risk.")
    if too_risky:
        reasons.append(f"Risk {scores.risk:.0f}/100 above ceiling {RISK_CEILING:.0f} — conditions too dangerous.")
    if bad_rr:
        reasons.append(f"Reward:risk {rr:.2f} below floor {RR_FLOOR:.2f} — the math does not pay.")
    if conflict:
        reasons.append("Timeframes conflict — no clean directional agreement.")
    if no_direction:
        reasons.append("No directional bias — market is indecisive.")
    if fomo_chase:
        reasons.append(f"FOMO chase — RSI {s.rsi:.0f} into {s.atr_pct:.1f}% ATR. Refusing to buy the top.")

    hard_fail = blind or illiquid or too_risky or fomo_chase
    soft_fail = bad_rr or conflict or no_direction

    # --- Grade the setup ------------------------------------------------------
    if hard_fail:
        setup = SetupQuality.REJECT
        decision = FinalDecision.NO_TRADE
    elif soft_fail:
        # Tradeable inputs but the edge isn't there yet — watch, don't force it.
        setup = SetupQuality.WATCH
        decision = FinalDecision.WATCH
        if not reasons:
            reasons.append("Setup developing but not confirmed — watching.")
    elif (
        scores.trade_quality >= TRADE_QUALITY_TAKE
        and scores.confidence >= conf_trade
        and rr >= RR_FLOOR
    ):
        setup = SetupQuality.HIGH_QUALITY_SETUP
        decision = FinalDecision.TAKE_TRADE
    elif scores.confidence >= CONFIDENCE_POSSIBLE:
        setup = SetupQuality.POSSIBLE_SETUP
        decision = FinalDecision.WATCH
        reasons.append(
            f"Confidence {scores.confidence:.0f} below the {SESSION_LABEL[session]} "
            f"session threshold {conf_trade:.0f}."
        )
    else:
        setup = SetupQuality.WATCH
        decision = FinalDecision.WATCH
        reasons.append("Edge too weak to act on — preserving capital.")

    # --- Capital Protection categories (drive the CPS) ------------------------
    categories: List[str] = []
    if fomo_chase:
        categories.append("FOMO_BLOCKED")
    if illiquid:
        categories.append("LIQUIDITY_TRAP_AVOIDED")
    if blind:
        categories.append("LOW_DATA_QUALITY_AVOIDED")
    if too_risky:
        categories.append("HIGH_RISK_AVOIDED")
    if bad_rr:
        categories.append("POOR_RR_AVOIDED")
    if conflict:
        categories.append("SIGNAL_CONFLICT_AVOIDED")

    # --- What would turn this into a trade? (Core Differentiator) -------------
    improvements: List[str] = []
    if blind:
        improvements.append(f"Data quality up to ≥{DATA_QUALITY_FLOOR:.0f} (complete, fresh feeds).")
    if illiquid:
        improvements.append(f"Liquidity up to ≥{LIQUIDITY_FLOOR:.0f} with tighter spreads.")
    if too_risky:
        improvements.append(f"Risk back below {RISK_CEILING:.0f} — volatility cooling off.")
    if bad_rr:
        improvements.append(f"A better entry / wider target for reward:risk ≥{RR_FLOOR:.2f}.")
    if conflict:
        improvements.append("Timeframes realigning to one clear direction.")
    if no_direction:
        improvements.append("A decisive break that establishes directional bias.")
    if fomo_chase:
        improvements.append("A pullback and RSI reset — wait for a healthy retest, not the top.")
    if decision != FinalDecision.TAKE_TRADE and scores.confidence < conf_trade and not (blind or illiquid or too_risky):
        improvements.append(
            f"Confidence rising to the {SESSION_LABEL[session]} threshold of {conf_trade:.0f} "
            f"(now {scores.confidence:.0f})."
        )
    if not improvements:
        improvements.append("Conditions already meet Argus' bar — maintain discipline on the exit.")

    # --- NO TRADE IS ALPHA ----------------------------------------------------
    is_alpha = decision in (FinalDecision.NO_TRADE, FinalDecision.REJECT)
    exposed = capital_usd * 0.10
    est_loss = round(exposed * (scores.risk / 100.0), 2)
    if is_alpha:
        # Capital that would have been exposed and is now protected.
        note = (
            f"NO TRADE IS ALPHA™ — by standing aside, Argus protected ~${exposed:,.0f} "
            f"of exposure and avoided an estimated ${est_loss:,.0f} of downside risk."
        )
    else:
        note = "Conditions clear — capital deployed within risk limits."
        exposed, est_loss = 0.0, 0.0

    return HonestyVerdict(
        setup_quality=setup,
        final_decision=decision,
        rejection_reasons=reasons,
        is_no_trade_alpha=is_alpha,
        risk_reward=rr,
        capital_protection_note=note,
        protection_categories=categories,
        exposure_usd=round(exposed, 2),
        loss_avoided_usd=est_loss,
        session=SESSION_LABEL[session],
        confidence_threshold=conf_trade,
        improvement_conditions=improvements,
    )
