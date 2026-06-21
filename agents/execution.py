"""Agent 5 — Execution.

Paper trading only. Tracks position lifecycle (open -> mark-to-market -> close)
with simulated slippage. Argus is a guardian: there is no live order path here.
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

    def to_dict(self) -> dict:
        return asdict(self)


class ExecutionAgent:
    name = "Execution"

    def __init__(self):
        self.positions: Dict[str, Position] = {}

    def open(self, symbol: str, direction: Direction, entry_price: float, size_usd: float,
             stop_loss: float, take_profit: List[float]) -> Position:
        slippage = 0.0005 if any(k in symbol.upper() for k in ("BTC", "ETH")) else 0.002
        fill = entry_price * (1 + slippage) if direction == Direction.LONG else entry_price * (1 - slippage)
        pos = Position(
            trade_id=f"trade_{uuid.uuid4().hex[:8]}",
            symbol=symbol,
            direction=direction.value,
            entry_price=round(entry_price, 8),
            fill_price=round(fill, 8),
            size_usd=round(size_usd, 2),
            stop_loss=round(stop_loss, 8),
            take_profit=[round(t, 8) for t in take_profit],
            opened_at=datetime.now(timezone.utc).isoformat(),
        )
        self.positions[pos.trade_id] = pos
        return pos

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
