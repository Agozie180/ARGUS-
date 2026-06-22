"""Session-aware confidence thresholds: Asian 65 / London 72 / New York 75.

The bar for TAKING a trade rises with the dominant session's efficiency.
"""
from core.sessions import TradingSession, SESSION_CONFIDENCE, session_for_hour
from core.scoring import compute_scores
from core.honesty_engine import evaluate
from core.models import MarketSnapshot, Scores, Direction, FinalDecision


def test_threshold_values():
    assert SESSION_CONFIDENCE[TradingSession.ASIAN] == 65.0
    assert SESSION_CONFIDENCE[TradingSession.LONDON] == 72.0
    assert SESSION_CONFIDENCE[TradingSession.NEW_YORK] == 75.0


def test_hour_mapping_covers_all_24_hours():
    mapped = {h: session_for_hour(h) for h in range(24)}
    assert mapped[3] == TradingSession.ASIAN
    assert mapped[9] == TradingSession.LONDON
    assert mapped[15] == TradingSession.NEW_YORK
    assert mapped[23] == TradingSession.ASIAN
    # every hour resolves to a real session
    assert all(isinstance(v, TradingSession) for v in mapped.values())


def _clean_long() -> MarketSnapshot:
    """A clean long with good levels (R:R 2.0) and no hard/soft-gate failures,
    so the ONLY thing that can block a TAKE is the confidence threshold."""
    return MarketSnapshot(
        symbol="BTCUSDT", price=100.0, direction_bias=Direction.LONG,
        timeframe_signals={"15m": 0.6, "1h": 0.7, "4h": 0.7, "1d": 0.6},
        adx=28, ema_stack="BULL", rsi=58, momentum=0.5, structure="UPTREND",
        atr_pct=1.4, volatility_score=42, liquidity_score=90, spread_bps=1.2,
        volume_score=0.8, indicator_completeness=1.0, data_freshness=1.0,
        support=95.0, resistance=110.0,
    )


# Confidence pinned at 70 — above Asian's 65, below New York's 75.
_BORDERLINE = Scores(confidence=70.0, risk=20.0, data_quality=90.0, trade_quality=72.0)


def test_same_setup_passes_asian_but_not_new_york():
    """A 70-confidence setup clears the Asian bar (65) yet fails the stricter
    New York bar (75) — proving the session gate actually moves the decision."""
    s = _clean_long()
    asian = evaluate(s, _BORDERLINE, session=TradingSession.ASIAN)
    london = evaluate(s, _BORDERLINE, session=TradingSession.LONDON)
    ny = evaluate(s, _BORDERLINE, session=TradingSession.NEW_YORK)

    assert asian.final_decision == FinalDecision.TAKE_TRADE
    assert asian.confidence_threshold == 65.0
    assert ny.final_decision != FinalDecision.TAKE_TRADE   # 70 < 75
    assert ny.confidence_threshold == 75.0
    # London (72) is also above 70, so it should not take either.
    assert london.final_decision != FinalDecision.TAKE_TRADE


def test_verdict_reports_session_and_improvements():
    v = evaluate(_clean_long(), _BORDERLINE, session=TradingSession.LONDON)
    assert v.session == "London"
    assert v.confidence_threshold == 72.0
    assert v.improvement_conditions  # never empty
    # The improvement hint should mention the session threshold it fell short of.
    assert any("72" in c for c in v.improvement_conditions)
