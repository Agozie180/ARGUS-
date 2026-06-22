"""Phase 10 — Bitget-compatible data adapter.

Argus is designed for Bitget but never *requires* live access to run. If Bitget
credentials are configured the adapter is structured to call market / futures /
spot endpoints; otherwise it transparently falls back to the deterministic
synthetic feed so the guardian always has something to reason about.

Execution is intentionally read-only here — Argus is a guardian first. Future
order execution plugs into `place_order` behind the paper-trading guard.
"""
from __future__ import annotations

import os
from typing import List, Optional

from core.models import MarketSnapshot
from services import market_data


class BitgetService:
    DEFAULT_UNIVERSE = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]

    def __init__(self) -> None:
        self.api_key = os.getenv("BITGET_API_KEY")
        self.secret = os.getenv("BITGET_SECRET_KEY")
        self.passphrase = os.getenv("BITGET_PASSPHRASE")
        self.paper = os.getenv("PAPER_TRADING", "true").lower() != "false"
        # Live data integration is structured but not yet wired (see _live_snapshot).
        self._live_ready = False

    @property
    def has_credentials(self) -> bool:
        return bool(self.api_key and self.secret and self.passphrase)

    @property
    def live(self) -> bool:
        """True only when credentials exist AND the live integration is wired."""
        return self.has_credentials and self._live_ready

    @property
    def mode(self) -> str:
        return "LIVE-DATA" if self.live else "SIMULATED-DATA"

    def get_snapshot(self, symbol: str, product: str = "futures") -> MarketSnapshot:
        """Return a MarketSnapshot for a symbol.

        `product` is one of 'spot' | 'futures' — accepted for Bitget API parity.
        With no credentials this uses the synthetic feed.
        """
        if self.live:
            try:
                return self._live_snapshot(symbol, product)
            except Exception:
                # Never let a live-data hiccup blind the guardian.
                pass
        # Vary the synthetic series slightly by product so spot/futures differ.
        seed_offset = 7 if product == "spot" else 0
        return market_data.build_snapshot(symbol, seed_offset=seed_offset)

    def scan(self, symbols: Optional[List[str]] = None, product: str = "futures") -> List[MarketSnapshot]:
        return [self.get_snapshot(s, product) for s in (symbols or self.DEFAULT_UNIVERSE)]

    # --- live path (structured, not invoked without credentials) -------------
    def _live_snapshot(self, symbol: str, product: str) -> MarketSnapshot:  # pragma: no cover
        """Placeholder for the live Bitget REST/MCP integration.

        Wire Bitget's market-data endpoints here (ticker, candles, orderbook,
        funding) and map them onto MarketSnapshot. Kept behind `self.live` so
        the project runs end-to-end offline.
        """
        raise NotImplementedError("Live Bitget data integration not yet configured.")

    def place_order(self, *args, **kwargs):  # pragma: no cover
        """Risk-monitoring build is read-only. Execution is paper-only."""
        raise NotImplementedError(
            "Argus is a guardian: live execution is disabled. Use the paper "
            "Execution agent for simulated fills."
        )
