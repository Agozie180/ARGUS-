"""Phase 4 — the Signal Honesty Engine is the core innovation, so it gets the
most tests. Each demo scenario asserts the guardian's intended behaviour."""
from core import demo_scenarios
from core.scoring import compute_scores
from core.honesty_engine import evaluate
from core.models import SetupQuality, FinalDecision


def _verdict(key: str):
    s = demo_scenarios.get_scenario(key)
    return s, evaluate(s, compute_scores(s))


def test_excellent_trade_is_taken():
    _, v = _verdict("A")
    assert v.final_decision == FinalDecision.TAKE_TRADE
    assert v.setup_quality == SetupQuality.HIGH_QUALITY_SETUP
    assert not v.is_no_trade_alpha


def test_weak_trade_is_not_taken():
    _, v = _verdict("B")
    assert v.final_decision in (FinalDecision.WATCH, FinalDecision.NO_TRADE)
    assert v.setup_quality != SetupQuality.HIGH_QUALITY_SETUP


def test_low_liquidity_trap_is_rejected():
    _, v = _verdict("C")
    assert v.final_decision == FinalDecision.NO_TRADE
    assert v.setup_quality == SetupQuality.REJECT
    assert v.is_no_trade_alpha
    assert any("liquid" in r.lower() for r in v.rejection_reasons)


def test_fomo_setup_is_rejected():
    _, v = _verdict("D")
    assert v.final_decision == FinalDecision.NO_TRADE
    assert v.is_no_trade_alpha
    assert any("fomo" in r.lower() for r in v.rejection_reasons)


def test_missing_data_is_rejected():
    s, v = _verdict("E")
    scores = compute_scores(s)
    assert scores.data_quality < 60
    assert v.final_decision == FinalDecision.NO_TRADE
    assert any("data quality" in r.lower() for r in v.rejection_reasons)


def test_no_trade_is_alpha_quantifies_capital():
    _, v = _verdict("C")
    assert "NO TRADE IS ALPHA" in v.capital_protection_note


def test_rejection_always_has_reasons():
    for key in demo_scenarios.SCENARIOS:
        s = demo_scenarios.get_scenario(key)
        v = evaluate(s, compute_scores(s))
        if v.final_decision in (FinalDecision.NO_TRADE, FinalDecision.REJECT):
            assert v.rejection_reasons, f"scenario {key} rejected without reasons"
