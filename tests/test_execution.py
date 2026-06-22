"""Execution agent — paper trades must open only on a TAKE TRADE, track the
position lifecycle, close with correct P&L, and feed the learning loop."""
from agents.orchestrator import Argus
from core import demo_scenarios


def _fresh():
    # Isolate the journal so win-rate assertions are deterministic.
    import os, tempfile, uuid
    a = Argus()
    a.reflection.path = os.path.join(tempfile.gettempdir(), f"argus_test_{uuid.uuid4().hex}.jsonl")
    return a


def test_take_trade_opens_paper_position():
    a = _fresh()
    r = a.execute_snapshot(demo_scenarios.get_scenario("A"), journal=False)
    assert r["judge"]["final_decision"] == "TAKE TRADE"
    assert r["execution"]["executed"] is True
    pos = r["execution"]["position"]
    assert pos["status"] == "OPEN"
    assert pos["size_usd"] > 0
    assert pos["trade_id"].startswith("trade_")


def test_no_trade_is_not_executed():
    a = _fresh()
    for key in ("C", "D", "E"):                       # liquidity trap, FOMO, missing data
        r = a.execute_snapshot(demo_scenarios.get_scenario(key), journal=False)
        assert r["execution"]["executed"] is False
        assert "TAKE TRADE" in r["execution"]["reason"] or "$0" in r["execution"]["reason"]


def test_full_lifecycle_win_and_portfolio():
    a = _fresh()
    r = a.execute_snapshot(demo_scenarios.get_scenario("A"))
    pos = r["execution"]["position"]
    # Close at the first take-profit → a win.
    done = a.close_position(pos["trade_id"], pos["take_profit"][0])
    assert done["position"]["status"] == "CLOSED"
    assert done["position"]["pnl_usd"] > 0
    assert done["review"]["outcome"] == "WIN"

    pf = a.portfolio()
    assert pf["closed_count"] == 1
    assert pf["open_count"] == 0
    assert pf["wins"] == 1
    assert pf["realized_pnl_usd"] > 0


def test_stop_loss_is_a_loss():
    a = _fresh()
    pos = a.execute_snapshot(demo_scenarios.get_scenario("A"))["execution"]["position"]
    done = a.close_position(pos["trade_id"], pos["stop_loss"])
    assert done["position"]["pnl_usd"] < 0
    assert done["review"]["outcome"] == "LOSS"


def test_mark_to_market_closes_on_target():
    a = _fresh()
    pos = a.execute_snapshot(demo_scenarios.get_scenario("A"))["execution"]["position"]
    closed = a.mark_to_market({pos["symbol"]: pos["take_profit"][0] * 1.01})
    assert len(closed) == 1
    assert closed[0]["status"] == "CLOSED"
