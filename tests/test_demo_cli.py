"""Terminal demo (`argus_demo.py`) — smoke + verdict-stability tests.

The CLI is a zero-setup demo surface a judge may run instead of the web app, so
it must never crash and must show the same deterministic verdicts as the rest of
Argus. These tests render every scenario and the WOW moment to an in-memory
console and assert the headline decisions are unchanged.
"""
import argus_demo
from agents.orchestrator import Argus
from core.models import Mode


def test_render_full_runs_for_every_scenario(capsys):
    argus = Argus()
    for key in ("A", "B", "C", "D", "E", "F"):
        res = argus.demo(key, mode=Mode.PROFESSIONAL)
        argus_demo.render_full(res, heading=f"Scenario {key}")
    out = capsys.readouterr().out
    # Each scenario symbol should appear in the rendered output.
    assert "BTCUSDT" in out and "SOLUSDT" in out


def test_wow_moment_renders_no_trade(capsys):
    argus = Argus()
    wow = argus.wow_moment(mode=Mode.PROFESSIONAL)
    argus_demo.render_full(wow)
    out = capsys.readouterr().out
    assert "NO TRADE" in out
    assert "NO TRADE IS ALPHA" in out


def test_summary_and_cps_render(capsys):
    argus = Argus()
    argus_demo.render_summary(argus)
    argus_demo.render_cps(argus)
    out = capsys.readouterr().out
    assert "CAPITAL PROTECTION SCORE" in out
    assert "Grade" in out


def test_scenario_verdicts_match_expected():
    """The demo must keep telling the same story to judges."""
    argus = Argus()
    expected = {
        "A": "TAKE TRADE",
        "B": "WATCH",
        "C": "NO TRADE",
        "D": "NO TRADE",
        "E": "NO TRADE",
        "F": "WATCH",
    }
    for key, decision in expected.items():
        res = argus.demo(key, mode=Mode.PROFESSIONAL)
        assert res["judge"]["final_decision"] == decision, (
            f"Scenario {key} drifted to {res['judge']['final_decision']}")


def test_alpha_note_prefix_not_duplicated(capsys):
    """The NO-TRADE-IS-ALPHA header must not be printed twice."""
    argus = Argus()
    argus_demo.render_full(argus.wow_moment(mode=Mode.PROFESSIONAL))
    out = capsys.readouterr().out
    assert out.count("NO TRADE IS ALPHA™") == 1
