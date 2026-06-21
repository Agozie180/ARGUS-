import asyncio
import json
import time
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Tuple, Any

from config import InstitutionalBias, Direction, SessionState
from bitget_client import BitgetClient

logger = logging.getLogger(__name__)
bitget = BitgetClient()

@dataclass
class MacroSnapshot:
    etf_net_flow_24h: float        # USD, positive = inflows
    etf_flow_signal: Direction
    whale_net_flow: float          # exchange inflow/outflow USD
    whale_signal: Direction        # inflow to exchange = sell pressure
    btc_nasdaq_correlation: float  # rolling 30d
    dxy_trend: str                 # "STRENGTHENING" | "WEAKENING" | "FLAT"
    macro_headwind: bool           # True if DXY strengthening + corr > 0.6
    institutional_bias: InstitutionalBias
    macro_score: float             # -1.0 to +1.0
    timestamp: datetime

def _log_perception(session: SessionState, agent: str, symbol: str, snapshot: Any, confidence: float, duration: float):
    entry = {
        "session_id": session.session_id,
        "cycle": session.cycle_count,
        "agent": agent,
        "symbol": symbol,
        "snapshot": asdict(snapshot) if hasattr(snapshot, '__dataclass_fields__') else str(snapshot),
        "confidence_contribution": confidence,
        "duration_ms": duration
    }
    with open("perception_log.jsonl", "a") as f:
        f.write(json.dumps(entry, default=str) + "\n")

async def perceive(symbol: str, session: SessionState) -> Tuple[MacroSnapshot, float]:
    start_time = time.monotonic()
    
    try:
        macro_data = await bitget.get_macro()
    except Exception as e:
        logger.warning(f"Failed to fetch macro data: {e}. Using fallback neutral data.")
        macro_data = {}
        
    try:
        # Use ticker as a proxy for market-intel skill if needed, or just use macro_data
        market_intel_data = await bitget.get_ticker(symbol)
    except Exception as e:
        logger.warning(f"Failed to fetch market intel for {symbol}: {e}. Using fallback neutral data.")
        market_intel_data = {}

    # 1. ETF Flows
    etf_net_flow_24h = float(macro_data.get("etf_net_flow_24h", 0.0))
    if etf_net_flow_24h > 0:
        etf_flow_signal = Direction.BUY
    elif etf_net_flow_24h < 0:
        etf_flow_signal = Direction.SELL
    else:
        etf_flow_signal = Direction.HOLD

    # 2. Whale Flows (Assume positive = inflow to exchange = bearish)
    whale_net_flow = float(macro_data.get("whale_net_flow", 0.0))
    if whale_net_flow > 0:  # Inflow to exchange
        whale_signal = Direction.SELL
    elif whale_net_flow < 0:  # Outflow from exchange
        whale_signal = Direction.BUY
    else:
        whale_signal = Direction.HOLD

    # 3. Correlation & DXY
    btc_nasdaq_correlation = float(macro_data.get("btc_nasdaq_correlation", 0.0))
    dxy_trend = str(macro_data.get("dxy_trend", "FLAT")).upper()
    
    # 4. Macro Headwind
    macro_headwind = (dxy_trend == "STRENGTHENING" and btc_nasdaq_correlation > 0.6)

    # 5. Institutional Bias
    if etf_flow_signal == Direction.BUY and whale_signal == Direction.BUY:
        institutional_bias = InstitutionalBias.ACCUMULATING
    elif etf_flow_signal == Direction.SELL and whale_signal == Direction.SELL:
        institutional_bias = InstitutionalBias.DISTRIBUTING
    else:
        institutional_bias = InstitutionalBias.NEUTRAL

    # 6. Macro Score (-1.0 to +1.0)
    etf_score = 1.0 if etf_flow_signal == Direction.BUY else (-1.0 if etf_flow_signal == Direction.SELL else 0.0)
    whale_score = 1.0 if whale_signal == Direction.BUY else (-1.0 if whale_signal == Direction.SELL else 0.0)
    dxy_score = -0.5 if dxy_trend == "STRENGTHENING" else (0.5 if dxy_trend == "WEAKENING" else 0.0)
    
    macro_score = (0.4 * etf_score) + (0.4 * whale_score) + (0.2 * dxy_score)
    macro_score = max(-1.0, min(1.0, macro_score))

    snapshot = MacroSnapshot(
        etf_net_flow_24h=etf_net_flow_24h,
        etf_flow_signal=etf_flow_signal,
        whale_net_flow=whale_net_flow,
        whale_signal=whale_signal,
        btc_nasdaq_correlation=btc_nasdaq_correlation,
        dxy_trend=dxy_trend,
        macro_headwind=macro_headwind,
        institutional_bias=institutional_bias,
        macro_score=macro_score,
        timestamp=datetime.now(timezone.utc)
    )

    # Confidence Contribution Logic
    aligned_count = 0
    expected_direction = Direction.BUY if macro_score > 0.2 else (Direction.SELL if macro_score < -0.2 else Direction.HOLD)
    
    if etf_flow_signal == expected_direction: aligned_count += 1
    if whale_signal == expected_direction: aligned_count += 1
    
    macro_aligned = False
    if (expected_direction == Direction.BUY and not macro_headwind and dxy_trend != "STRENGTHENING") or \
       (expected_direction == Direction.SELL and macro_headwind) or \
       (expected_direction == Direction.HOLD and dxy_trend == "FLAT"):
        macro_aligned = True
        aligned_count += 1

    # Fallback check: if data was empty/unavailable, confidence floor is 0.40
    is_data_stale = not macro_data and not market_intel_data

    if is_data_stale:
        confidence = 0.40
    elif aligned_count == 3:
        confidence = 0.80  # HIGH
    elif aligned_count == 2:
        confidence = 0.60  # MEDIUM
    else:
        confidence = 0.40  # LOW (conflicting)

    duration = (time.monotonic() - start_time) * 1000
    _log_perception(session, "OnchainMacroAgent", symbol, snapshot, confidence, duration)
    
    return snapshot, confidence
