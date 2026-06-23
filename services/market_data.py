"""Deterministic synthetic market data + indicator computation.

No network, no keys — a fresh clone produces realistic OHLC and a fully
populated MarketSnapshot for any symbol. The Bitget adapter (services/bitget.py)
swaps this out for live data when credentials are present.
"""
from __future__ import annotations

import hashlib
import math
import random
from typing import Dict, List

from core.models import MarketSnapshot, Direction


_BASE_PRICE = {"BTC": 64_000.0, "ETH": 3_100.0, "SOL": 165.0, "BNB": 580.0}


def _seed_for(symbol: str) -> int:
    # Stable across processes: Python's built-in hash() is salted per run
    # (PYTHONHASHSEED), which would make the "deterministic" feed change on every
    # restart. A content hash keeps a symbol's synthetic series reproducible.
    digest = hashlib.md5(symbol.upper().encode("utf-8")).hexdigest()
    return int(digest, 16) % (2**31)


def generate_ohlc(symbol: str, periods: int = 200, seed_offset: int = 0) -> List[dict]:
    """Generate a deterministic random-walk OHLC series for a symbol."""
    rng = random.Random(_seed_for(symbol) + seed_offset)
    base = next((p for k, p in _BASE_PRICE.items() if k in symbol.upper()), 100.0)
    price = base
    candles: List[dict] = []
    for _ in range(periods):
        drift = rng.gauss(0.0002, 0.012)
        price = max(price * (1 + drift), 1e-9)
        high = price * (1 + abs(rng.gauss(0, 0.006)))
        low = price * (1 - abs(rng.gauss(0, 0.006)))
        vol = abs(rng.gauss(1000, 350))
        candles.append({"open": price, "high": high, "low": low, "close": price, "volume": vol})
    return candles


def _ema(values: List[float], span: int) -> float:
    if not values:
        return 0.0
    k = 2 / (span + 1)
    ema = values[0]
    for v in values[1:]:
        ema = v * k + ema * (1 - k)
    return ema


def _rsi(closes: List[float], period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    gains, losses = [], []
    for i in range(-period, 0):
        diff = closes[i] - closes[i - 1]
        (gains if diff >= 0 else losses).append(abs(diff))
    avg_gain = sum(gains) / period if gains else 1e-9
    avg_loss = sum(losses) / period if losses else 1e-9
    rs = avg_gain / avg_loss if avg_loss else 99
    return 100 - (100 / (1 + rs))


def _atr_pct(candles: List[dict], period: int = 14) -> float:
    if len(candles) < period:
        return 1.0
    trs = [(c["high"] - c["low"]) for c in candles[-period:]]
    atr = sum(trs) / period
    last = candles[-1]["close"] or 1e-9
    return (atr / last) * 100


def build_snapshot(symbol: str, seed_offset: int = 0) -> MarketSnapshot:
    """Compute a full MarketSnapshot from synthetic candles."""
    candles = generate_ohlc(symbol, seed_offset=seed_offset)
    return snapshot_from_candles(symbol, candles)


def snapshot_from_candles(
    symbol: str,
    candles: List[dict],
    *,
    price: float | None = None,
    spread_bps: float | None = None,
    liquidity_score: float | None = None,
    data_freshness: float = 1.0,
    indicator_completeness: float = 1.0,
) -> MarketSnapshot:
    """Compute a full MarketSnapshot from a list of OHLC candle dicts.

    Shared by the synthetic feed and the live Bitget adapter so both produce
    identical indicator math. Optional overrides let the live path supply the
    real last price, real bid/ask spread, and a measured freshness value.
    """
    closes = [c["close"] for c in candles]
    price = closes[-1] if price is None else price

    ema20, ema50, ema200 = _ema(closes[-20:], 20), _ema(closes[-50:], 50), _ema(closes, 200)
    if ema20 > ema50 > ema200:
        ema_stack, bias, structure = "BULL", Direction.LONG, "UPTREND"
    elif ema20 < ema50 < ema200:
        ema_stack, bias, structure = "BEAR", Direction.SHORT, "DOWNTREND"
    else:
        ema_stack, bias, structure = "MIXED", Direction.NEUTRAL, "RANGE"

    rsi = _rsi(closes)
    atr_pct = _atr_pct(candles)
    # ADX proxy from recent directional persistence.
    chg = (closes[-1] - closes[-10]) / (closes[-10] or 1e-9)
    adx = min(45.0, 15 + abs(chg) * 400)
    momentum = max(-1.0, min(1.0, chg * 20))

    # Volume/liquidity proxies.
    recent_vol = sum(c["volume"] for c in candles[-20:]) / 20
    volume_score = max(0.0, min(1.0, candles[-1]["volume"] / (recent_vol or 1)))
    if liquidity_score is None:
        liquidity_score = max(30.0, min(95.0, 60 + (recent_vol - 800) / 20))
    volatility_score = max(0.0, min(100.0, atr_pct * 18))
    if spread_bps is None:
        spread_bps = max(0.8, 6 - liquidity_score / 20)

    tf_signals: Dict[str, float] = {
        "15m": momentum * 0.8 + 0.05,
        "1h": momentum,
        "4h": momentum * 1.1,
        "1d": (1 if ema_stack == "BULL" else -1 if ema_stack == "BEAR" else 0) * 0.6,
    }
    tf_signals = {k: max(-1.0, min(1.0, v)) for k, v in tf_signals.items()}

    support = min(c["low"] for c in candles[-20:])
    resistance = max(c["high"] for c in candles[-20:])

    return MarketSnapshot(
        symbol=symbol,
        price=round(price, 8 if price < 1 else 2),
        direction_bias=bias,
        timeframe_signals={k: round(v, 3) for k, v in tf_signals.items()},
        adx=round(adx, 1),
        ema_stack=ema_stack,
        rsi=round(rsi, 1),
        momentum=round(momentum, 3),
        structure=structure,
        atr_pct=round(atr_pct, 2),
        volatility_score=round(volatility_score, 1),
        liquidity_score=round(liquidity_score, 1),
        spread_bps=round(spread_bps, 1),
        volume_score=round(volume_score, 2),
        indicator_completeness=indicator_completeness,
        data_freshness=data_freshness,
        support=round(support, 8 if price < 1 else 2),
        resistance=round(resistance, 8 if price < 1 else 2),
    )
