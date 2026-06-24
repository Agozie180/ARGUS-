"""Live Bitget market-data client — public REST, read-only, zero new deps.

Argus is a guardian first: this module fetches **public** market data only
(ticker + candlesticks) over Bitget's REST API. It never authenticates, never
sends API keys, and never places orders — so there is no credential to leak in
logs, the browser, or the UI. It exists purely to feed *real* prices into the
existing decision engine for one live demo example.

Everything degrades gracefully: any network/parse failure raises
``LiveBitgetError`` and the caller falls back to a deterministic demo scenario.
"""
from __future__ import annotations

import json
import math
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import List, Optional

from core.models import MarketSnapshot
from services.market_data import snapshot_from_candles

_BASE_URL = "https://api.bitget.com"
_TIMEOUT = 6.0  # seconds — fail fast and fall back rather than hang the page


class LiveBitgetError(Exception):
    """Raised when live Bitget data cannot be fetched or parsed."""


@dataclass
class LiveMarket:
    """A live read of one symbol, ready for the UI and the decision engine."""
    symbol: str
    price: float
    change_24h_pct: Optional[float]
    high_24h: Optional[float]
    low_24h: Optional[float]
    base_volume: Optional[float]
    candles: List[dict]          # most-recent-last OHLC dicts
    fetched_at: float            # unix seconds when we fetched
    data_age_seconds: float      # age of the exchange timestamp at fetch
    snapshot: MarketSnapshot = field(repr=False)

    @property
    def freshness_label(self) -> str:
        secs = max(0.0, self.data_age_seconds)
        if secs < 90:
            return f"{secs:.0f}s ago"
        return f"{secs / 60:.0f}m ago"


def _get(path: str, params: dict) -> list:
    """GET a public Bitget endpoint and return its ``data`` payload."""
    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{_BASE_URL}{path}?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": "argus-guardian/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise LiveBitgetError(f"Bitget request failed: {e}") from e
    except json.JSONDecodeError as e:
        raise LiveBitgetError("Bitget returned malformed JSON") from e

    if str(payload.get("code")) != "00000":
        raise LiveBitgetError(f"Bitget API error: {payload.get('msg', 'unknown')}")
    data = payload.get("data")
    if not data:
        raise LiveBitgetError("Bitget returned no data")
    return data


def fetch_ticker(symbol: str) -> dict:
    """Public spot ticker for ``symbol`` (e.g. BTCUSDT)."""
    data = _get("/api/v2/spot/market/tickers", {"symbol": symbol})
    return data[0]


def fetch_all_tickers() -> List[dict]:
    """Every public spot ticker in a single request.

    One call to ``/api/v2/spot/market/tickers`` (no symbol param) returns the
    whole spot market — used for the Market Scanner and dynamic symbol discovery
    so Argus reflects the live Bitget universe, not a hardcoded three-token list.
    """
    return _get("/api/v2/spot/market/tickers", {})


def discover_symbols(limit: int = 20, quote: str = "USDT", preferred: Optional[List[str]] = None) -> List[str]:
    """Rank live Bitget spot symbols by 24h USDT turnover and return the top N.

    `preferred` symbols (if currently tradable) are floated to the front so the
    majors judges expect (BTC/ETH/SOL...) always appear, with the rest filled by
    real liquidity ranking from the live exchange.
    """
    tickers = fetch_all_tickers()
    rows = []
    for t in tickers:
        sym = str(t.get("symbol", "")).upper()
        if not sym.endswith(quote):
            continue
        base = sym[: -len(quote)]
        # Skip leveraged ETF-style tokens (e.g. BTC3LUSDT/ETH5SUSDT) so the
        # universe stays the spot crypto pairs a guardian should reason about.
        if any(base.endswith(suf) for suf in ("3L", "3S", "5L", "5S", "2L", "2S")):
            continue
        vol = _safe_float(t.get("usdtVolume")) or _safe_float(t.get("quoteVolume")) or 0.0
        rows.append((sym, vol))
    rows.sort(key=lambda r: r[1], reverse=True)
    ranked = [sym for sym, _ in rows]

    out: List[str] = []
    if preferred:
        ranked_set = set(ranked)
        for p in preferred:
            p = p.upper()
            if p in ranked_set and p not in out:
                out.append(p)
    for sym in ranked:
        if sym not in out:
            out.append(sym)
        if len(out) >= limit:
            break
    return out[:limit]


def fetch_candles(symbol: str, granularity: str = "1h", limit: int = 100) -> List[dict]:
    """Public spot candlesticks, normalised to OHLC dicts (oldest first)."""
    raw = _get(
        "/api/v2/spot/market/candles",
        {"symbol": symbol, "granularity": granularity, "limit": limit},
    )
    candles: List[dict] = []
    for row in raw:
        # Bitget row: [ts, open, high, low, close, baseVol, quoteVol, usdtVol]
        candles.append({
            "ts": int(row[0]),
            "open": float(row[1]),
            "high": float(row[2]),
            "low": float(row[3]),
            "close": float(row[4]),
            "volume": float(row[5]),
        })
    if not candles:
        raise LiveBitgetError("Bitget returned no candles")
    return candles


def _safe_float(value, default: Optional[float] = None) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def get_live_market(symbol: str, granularity: str = "1h", limit: int = 100) -> LiveMarket:
    """Fetch live ticker + candles and build a MarketSnapshot for the engine.

    Raises LiveBitgetError on any failure so the caller can fall back to demo.
    """
    symbol = symbol.strip().upper()
    ticker = fetch_ticker(symbol)
    candles = fetch_candles(symbol, granularity=granularity, limit=limit)

    now = time.time()
    last_price = _safe_float(ticker.get("lastPr")) or candles[-1]["close"]
    bid = _safe_float(ticker.get("bidPr"))
    ask = _safe_float(ticker.get("askPr"))
    # Real bid/ask spread in basis points when available.
    spread_bps = None
    if bid and ask and last_price:
        spread_bps = round(abs(ask - bid) / last_price * 10_000, 2)

    # Bitget's change24h is a fraction (e.g. -0.0299 == -2.99%).
    change_frac = _safe_float(ticker.get("change24h"))
    change_pct = round(change_frac * 100, 2) if change_frac is not None else None

    # Real liquidity read from 24h USDT turnover + spread, so deep majors (BTC/ETH)
    # are scored as liquid instead of inheriting the synthetic volume scale.
    quote_vol = _safe_float(ticker.get("usdtVolume")) or _safe_float(ticker.get("quoteVolume"))
    liquidity_score = None
    if quote_vol and quote_vol > 0:
        liq = 50.0 + min(35.0, math.log10(quote_vol / 1_000_000.0) * 12.0)  # $1M→50, ~$1B→~86
        if spread_bps is not None:
            liq += max(-15.0, min(15.0, (3.0 - spread_bps) * 5.0))          # tight spread = deeper
        liquidity_score = round(max(30.0, min(98.0, liq)), 1)

    exchange_ts = _safe_float(ticker.get("ts"))
    data_age = (now - exchange_ts / 1000.0) if exchange_ts else 0.0
    # Freshness decays from 1.0 toward 0 over ~5 minutes of staleness.
    freshness = max(0.0, min(1.0, 1.0 - max(0.0, data_age) / 300.0))

    snapshot = snapshot_from_candles(
        symbol,
        candles,
        price=last_price,
        spread_bps=spread_bps,
        liquidity_score=liquidity_score,
        data_freshness=round(freshness, 3),
        source="BITGET_LIVE",
        market_type="spot",
        fetched_at=now,
        change_24h_pct=change_pct,
    )

    return LiveMarket(
        symbol=symbol,
        price=last_price,
        change_24h_pct=change_pct,
        high_24h=_safe_float(ticker.get("high24h")),
        low_24h=_safe_float(ticker.get("low24h")),
        base_volume=_safe_float(ticker.get("baseVolume")),
        candles=candles,
        fetched_at=now,
        data_age_seconds=max(0.0, data_age),
        snapshot=snapshot,
    )
