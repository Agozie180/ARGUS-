"""Capital Protection Score (CPS) — Argus' signature proprietary metric.

These tests pin the guardian's protective accounting: categories are emitted,
the aggregate score is bounded and meaningful, and rejections quantify the
downside they avoided.
"""
from core import demo_scenarios
from core.scoring import compute_scores
from core.honesty_engine import evaluate
from core.cps import compute_cps, impact_statement, FOMO, LIQUIDITY_TRAP
from agents.orchestrator import Argus


def _decision_dict(key: str):
    s = demo_scenarios.get_scenario(key)
    v = evaluate(s, compute_scores(s))
    return {
        "final_decision": v.final_decision.value,
        "loss_avoided_usd": v.loss_avoided_usd,
        "exposure_usd": v.exposure_usd,
        "protection_categories": v.protection_categories,
    }


def test_fomo_scenario_emits_fomo_category():
    s = demo_scenarios.get_scenario("D")
    v = evaluate(s, compute_scores(s))
    assert FOMO in v.protection_categories
    assert v.loss_avoided_usd > 0
    assert v.exposure_usd > 0


def test_low_liquidity_emits_trap_category():
    s = demo_scenarios.get_scenario("C")
    v = evaluate(s, compute_scores(s))
    assert LIQUIDITY_TRAP in v.protection_categories


def test_taken_trade_has_no_protection_amounts():
    s = demo_scenarios.get_scenario("A")
    v = evaluate(s, compute_scores(s))
    assert v.protection_categories == []
    assert v.loss_avoided_usd == 0
    assert v.exposure_usd == 0


def test_cps_is_bounded_and_populated():
    decisions = [_decision_dict(k) for k in demo_scenarios.SCENARIOS]
    cps = compute_cps(decisions, capital_usd=10_000.0)
    assert 0 <= cps.cps <= 100
    assert cps.decisions == len(decisions)
    assert cps.trades_rejected >= 3          # C, D, E at least
    assert cps.potential_loss_avoided_usd > 0
    assert cps.fomo_blocked >= 1
    assert cps.liquidity_traps_avoided >= 1
    assert cps.grade in {"A+", "A", "B", "C", "D"}


def test_empty_journal_is_neutral_not_fake():
    cps = compute_cps([], capital_usd=10_000.0)
    assert cps.cps == 50.0
    assert cps.trades_rejected == 0


def test_orchestrator_cps_overview():
    cps = Argus().cps_overview()
    assert cps["cps"] > 0
    assert cps["trades_rejected"] >= 3
    assert "category_breakdown" in cps


def test_impact_statement_quantifies_when_alpha():
    txt = impact_statement(True, [FOMO], 618.0, 1000.0)
    assert "618" in txt and "1,000" in txt
    assert impact_statement(False, [], 0, 0).startswith("Positive expected value")
