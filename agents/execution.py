"""Agent 5 — Execution.

Execution-ready, paper by default. Tracks position lifecycle
(open -> mark-to-market -> close) with simulated slippage, records every order,
and can route a REAL Bitget order **only** when live trading has cleared all of
the execution_mode safety gates. Argus is a guardian: live orders never fire by
default or on the judging deployment.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional

from core.models import Direction


@dataclass
class Position:
    trade_id: str
    symbol: str
    direction: str
    entry_price: float
    fill_price: float
    size_usd: float
    stop_loss: float
    take_profit: List[float]
    opened_at: str
    status: str = "OPEN"
    exit_price: Optional[float] = None
    pnl_usd: Optional[float] = None
    pnl_pct: Optional[float] = None
    closed_at: Optional[str] = None
    # Entry context, kept so the Reflection agent can review the trade on close.
    entry_confidence: float = 0.0
    entry_risk: float = 0.0
    # Execution provenance: which mode actually filled this position.
    mode: str = "PAPER"                       # PAPER | LIVE
    order_ref: Optional[str] = None           # exchange order id / paper ref

    def to_dict(self) -> dict:
        return asdict(self)


class ExecutionAgent:
    name = "Execution"

    def __init__(self, bitget=None):
        self.positions: Dict[str, Position] = {}
        # A flat, append-only record of every order Argus routes (paper or live),
        # so the Execution Console can prove what was simulated vs sent.
        self.order_log: List[dict] = []
        self._bitget = bitget  # set by the orchestrator to enable the live path

    def open(self, symbol: str, direction: Direction, entry_price: float, size_usd: float,
             stop_loss: float, take_profit: List[float],
             entry_confidence: float = 0.0, entry_risk: float = 0.0,
             live: bool = False) -> Position:
        slippage = 0.0005 if any(k in symbol.upper() for k in ("BTC", "ETH")) else 0.002
        fill = entry_price * (1 + slippage) if direction == Direction.LONG else entry_price * (1 - slippage)
        trade_id = f"trade_{uuid.uuid4().hex[:8]}"
        mode = "PAPER"
        order_ref: Optional[str] = f"paper_{trade_id}"

        # Live routing is only attempted when explicitly requested AND a Bitget
        # service is wired; the service itself re-checks every safety gate and
        # raises if live trading is not fully enabled.
        if live and self._bitget is not None:
            side = "buy" if direction == Direction.LONG else "sell"
            ack = self._bitget.place_spot_order(
                symbol=symbol, side=side, size=size_usd, order_type="market", confirm=True,
            )
            mode = "LIVE"
            order_ref = str(ack.get("status", "SENT"))

        pos = Position(
            trade_id=trade_id,
            symbol=symbol,
            direction=direction.value,
            entry_price=round(entry_price, 8),
            fill_price=round(fill, 8),
            size_usd=round(size_usd, 2),
            stop_loss=round(stop_loss, 8),
            take_profit=[round(t, 8) for t in take_profit],
            opened_at=datetime.now(timezone.utc).isoformat(),
            entry_confidence=round(entry_confidence, 1),
            entry_risk=round(entry_risk, 1),
            mode=mode,
            order_ref=order_ref,
        )
        self.positions[pos.trade_id] = pos
        self.order_log.append({
            "trade_id": trade_id, "symbol": symbol, "side": direction.value,
            "size_usd": round(size_usd, 2), "fill_price": round(fill, 8),
            "mode": mode, "order_ref": order_ref,
            "ts": pos.opened_at,
        })
        return pos

    def recent_orders(self, limit: int = 25) -> List[dict]:
        return list(reversed(self.order_log[-limit:]))

    def mark_to_market(self, current_prices: Dict[str, float]) -> List[Position]:
        """Close any open position that hit its stop or first target."""
        closed: List[Position] = []
        for pos in list(self.positions.values()):
            if pos.status != "OPEN":
                continue
            price = current_prices.get(pos.symbol)
            if price is None:
                continue
            tp1 = pos.take_profit[0] if pos.take_profit else None
            hit = False
            exit_price = price
            if pos.direction == "LONG":
                if price <= pos.stop_loss:
                    hit, exit_price = True, pos.stop_loss
                elif tp1 and price >= tp1:
                    hit, exit_price = True, tp1
            else:
                if price >= pos.stop_loss:
                    hit, exit_price = True, pos.stop_loss
                elif tp1 and price <= tp1:
                    hit, exit_price = True, tp1
            if hit:
                closed.append(self.close(pos.trade_id, exit_price))
        return closed

    def close(self, trade_id: str, exit_price: float) -> Position:
        pos = self.positions[trade_id]
        if pos.direction == "LONG":
            pnl_pct = (exit_price - pos.fill_price) / pos.fill_price
        else:
            pnl_pct = (pos.fill_price - exit_price) / pos.fill_price
        pos.exit_price = round(exit_price, 8)
        pos.pnl_pct = round(pnl_pct, 4)
        pos.pnl_usd = round(pnl_pct * pos.size_usd, 2)
        pos.status = "CLOSED"
        pos.closed_at = datetime.now(timezone.utc).isoformat()
        return pos

    def open_positions(self) -> List[Position]:
        return [p for p in self.positions.values() if p.status == "OPEN"]

    def closed_positions(self) -> List[Position]:
        return [p for p in self.positions.values() if p.status == "CLOSED"]
