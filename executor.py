import json
import uuid
import time
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Optional

from config import settings, Direction, SessionState
from decision_engine import Decision
from risk_guardian import RiskDecision
from bitget_client import BitgetClient
import reflection

logger = logging.getLogger(__name__)
bitget = BitgetClient()

@dataclass
class TradeRecord:
    trade_id: str
    session_id: str
    cycle: int
    symbol: str
    action: str
    entry_price: float
    fill_price: float
    slippage_usd: float
    size_usd: float
    stop_loss: float
    take_profit: float
    confidence_score: dict
    regime: str
    reasoning_summary: str
    timestamp: str
    status: str = "OPEN"
    exit_price: Optional[float] = None
    pnl_usd: Optional[float] = None
    pnl_pct: Optional[float] = None
    hold_duration_min: Optional[float] = None

async def execute_paper(decision: Decision, risk: RiskDecision, session: SessionState) -> Optional[TradeRecord]:
    if not risk.approved or decision.action == Direction.NO_TRADE:
        return None
        
    trade_id = f"trade_{uuid.uuid4().hex[:8]}"
    slippage_pct = 0.0005 if "BTC" in decision.symbol or "ETH" in decision.symbol else 0.0020
    
    if decision.action == Direction.BUY:
        fill_price = decision.entry_price * (1 + slippage_pct)
    else:
        fill_price = decision.entry_price * (1 - slippage_pct)
        
    slippage_usd = abs(fill_price - decision.entry_price)
    
    record = TradeRecord(
        trade_id=trade_id,
        session_id=session.session_id,
        cycle=session.cycle_count,
        symbol=decision.symbol,
        action=decision.action.value,
        entry_price=decision.entry_price,
        fill_price=fill_price,
        slippage_usd=slippage_usd,
        size_usd=risk.adjusted_size_usd,
        stop_loss=decision.stop_loss,
        take_profit=decision.take_profit,
        confidence_score=asdict(decision.confidence_score),
        regime=decision.regime_state.regime.value,
        reasoning_summary=decision.reasoning_trace[-1] if decision.reasoning_trace else "",
        timestamp=datetime.now(timezone.utc).isoformat()
    )
    
    with open("paper_trades.jsonl", "a") as f:
        f.write(json.dumps(asdict(record)) + "\n")
        
    session.active_trades.append(trade_id)
    return record

async def check_and_close_trades(session: SessionState) -> None:
    open_trades = []
    closed_trades_data = []
    
    try:
        with open("paper_trades.jsonl", "r") as f:
            lines = f.readlines()
            
        for line in lines:
            t = json.loads(line)
            if t.get("status") == "OPEN" and t.get("session_id") == session.session_id:
                open_trades.append(t)
    except FileNotFoundError:
        return
        
    for trade in open_trades:
        try:
            ticker = await bitget.get_ticker(trade["symbol"])
            current_price = float(ticker.get("lastPrice", ticker.get("price", 0.0)))
        except Exception:
            continue
            
        should_close = False
        exit_price = current_price
        
        if trade["action"] == "BUY":
            if current_price <= trade["stop_loss"]:
                should_close = True
                exit_price = trade["stop_loss"]
            elif current_price >= trade["take_profit"]:
                should_close = True
                exit_price = trade["take_profit"]
        else: # SELL
            if current_price >= trade["stop_loss"]:
                should_close = True
                exit_price = trade["stop_loss"]
            elif current_price <= trade["take_profit"]:
                should_close = True
                exit_price = trade["take_profit"]
                
        if session.halted or should_close:
            # Calculate PnL
            size_usd = trade["size_usd"]
            entry = trade["fill_price"]
            if trade["action"] == "BUY":
                pnl_usd = ((exit_price - entry) / entry) * size_usd
            else:
                pnl_usd = ((entry - exit_price) / entry) * size_usd
                
            pnl_pct = pnl_usd / size_usd if size_usd > 0 else 0.0
            duration_min = (datetime.now(timezone.utc) - datetime.fromisoformat(trade["timestamp"])).total_seconds() / 60.0
            
            trade["status"] = "CLOSED"
            trade["exit_price"] = exit_price
            trade["pnl_usd"] = pnl_usd
            trade["pnl_pct"] = pnl_pct
            trade["hold_duration_min"] = duration_min
            closed_trades_data.append(trade)
            
            session.update_after_trade(pnl_pct)
            if trade["trade_id"] in session.active_trades:
                session.active_trades.remove(trade["trade_id"])
                
            # Trigger Reflection
            reflection.run_reflection(trade, session)
            
    # Rewrite file if trades were closed
    if closed_trades_data:
        closed_ids = {t["trade_id"] for t in closed_trades_data}
        new_lines = []
        for line in lines:
            t = json.loads(line)
            if t["trade_id"] in closed_ids:
                # Find updated version
                for ct in closed_trades_data:
                    if ct["trade_id"] == t["trade_id"]:
                        new_lines.append(json.dumps(ct) + "\n")
                        break
            else:
                new_lines.append(line)
                
        with open("paper_trades.jsonl", "w") as f:
            f.writelines(new_lines)
