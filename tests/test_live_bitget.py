"""Live Bitget adapter — network-free unit tests.

We never hit the real exchange here: we exercise the parsing/normalisation and
the shared snapshot math so the live path stays correct and the decision engine
keeps consuming real-shaped data. (The actual REST call is covered manually via
the Live Bitget Example page.)
"""
import pytest

from services import live_bitget as lb
from services.market_data import snapshot_from_candles
from agents.orchestrator import Argus
from core.models import Mode


def _fake_candles(n=60, start=60_000.0):
    candles = []
    price = start
    for i in range(n):
        price *= 1.001
        candles.append({
            "ts": 1_700_000_000_000 + i * 3_600_000,
            "open": price, "high": price * 1.004, "low": price * 0.996,
            "close": price, "volume": 1000 + i,
        })
    return candles


def test_safe_float_handles_bad_input():
    assert lb._safe_float("1.5") == 1.5
    assert lb._safe_float(None) is None
    assert lb._safe_float("not-a-number", default=0.0) == 0.0


def test_snapshot_from_candles_honors_overrides():
    candles = _fake_candles()
    snap = snapshot_from_candles(
        "BTCUSDT", candles, price=63_500.0, spread_bps=1.5, data_freshness=0.8,
    )
    assert snap.symbol == "BTCUSDT"
    assert snap.price == 63_500.0          # live last price wins over last close
    assert snap.spread_bps == 1.5          # real bid/ask spread wins
    assert snap.data_freshness == 0.8
    assert 0 <= snap.rsi <= 100


def test_live_snapshot_feeds_decision_engine():
    """A live-shaped snapshot flows through the real guardian and yields a verdict."""
    snap = snapshot_from_candles("ETHUSDT", _fake_candles(start=3_000.0), price=3_200.0)
    result = Argus().analyze_snapshot(snap, mode=Mode.PROFESSIONAL, journal=False)
    assert result["judge"]["final_decision"] in {"TAKE TRADE", "WATCH", "REJECT", "NO TRADE"}
    assert 0 <= result["scores"]["confidence"] <= 100
    assert 0 <= result["scores"]["risk"] <= 100


def test_get_live_market_raises_on_bad_payload(monkeypatch):
    """A non-success code from Bitget surfaces as LiveBitgetError (→ demo fallback)."""
    def _boom(path, params):
        raise lb.LiveBitgetError("simulated outage")
    monkeypatch.setattr(lb, "_get", _boom)
    with pytest.raises(lb.LiveBitgetError):
        lb.get_live_market("BTCUSDT")
