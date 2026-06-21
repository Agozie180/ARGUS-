import asyncio
import json
import time
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Tuple, Dict, Any

from config import RegimeEnum, Direction, SessionState
from bitget_client import BitgetClient

logger = logging.getLogger(__name__)
bitget = BitgetClient()

@dataclass
class TechnicalSnapshot:
    symbol: str
    signal_strength: float        # -1.0 (strong sell) to +1.0 (strong buy)
    trend_direction: Direction
    adx: float
    atr_percentile: float         # 0–100, where in vol distribution
    ema_stack: str                # "BULL" | "BEAR" | "MIXED"
    support: float
    resistance: float
    timeframe_agreement: float    # % of TFs agreeing on direction
    regime_hint: RegimeEnum       # TRENDING if ADX>25 else RANGING
    raw_indicators: dict
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

async def perceive(symbol: str, session: SessionState) -> Tuple[TechnicalSnapshot, float]:
    start_time = time.monotonic()
    
    # Fetch TA data for 4 timeframes concurrently
    # Assuming bitget.get_technical_analysis returns a dict containing all TFs or we mock it.
    # For strict standalone functionality without a live CLI, we use a defensive parser.
    try:
        raw_data = await bitget.get_technical_analysis(symbol)
    except Exception as e:
        logger.warning(f"Failed to fetch technical analysis for {symbol}: {e}. Using fallback neutral data.")
        raw_data = {}

    # Extract timeframe data safely
    tf_keys = ["15m", "1h", "4h", "1d"]
    tf_signals = []
    adx_values = []
    atr_values = []
    ema_20_values = []
    ema_50_values = []
    ema_200_values = []
    volumes = []
    
    for tf in tf_keys:
        tf_data = raw_data.get(tf, raw_data.get(f"ta_{tf}", {}))
        tf_signals.append(tf_data.get("signal", 0.0))
        adx_values.append(float(tf_data.get("adx", 0.0)))
        atr_values.append(float(tf_data.get("atr", 0.0)))
        ema_20_values.append(float(tf_data.get("ema_20", 0.0)))
        ema_50_values.append(float(tf_data.get("ema_50", 0.0)))
        ema_200_values.append(float(tf_data.get("ema_200", 0.0)))
        volumes.append(float(tf_data.get("volume", 0.0)))

    # 1. Signal Strength (average across TFs)
    signal_strength = sum(tf_signals) / len(tf_signals) if tf_signals else 0.0
    
    # 2. Trend Direction
    if signal_strength > 0.3:
        trend_direction = Direction.BUY
    elif signal_strength < -0.3:
        trend_direction = Direction.SELL
    else:
        trend_direction = Direction.HOLD
        
    # 3. ADX (average)
    adx = sum(adx_values) / len(adx_values) if adx_values else 0.0
    
    # 4. ATR Percentile (mocked calculation based on relative values)
    avg_atr = sum(atr_values) / len(atr_values) if atr_values else 0.0
    # Assuming a mock percentile mapping for demonstration
    atr_percentile = min(100.0, max(0.0, (avg_atr / 1000.0) * 100.0)) if avg_atr > 0 else 50.0
    
    # 5. EMA Stack (using 1h as primary reference)
    if ema_20_values[1] > ema_50_values[1] > ema_200_values[1]:
        ema_stack = "BULL"
    elif ema_20_values[1] < ema_50_values[1] < ema_200_values[1]:
        ema_stack = "BEAR"
    else:
        ema_stack = "MIXED"
        
    # 6. Support/Resistance (mocked from raw data)
    support = float(raw_data.get("support", 0.0))
    resistance = float(raw_data.get("resistance", 0.0))
    
    # 7. Timeframe Agreement
    bullish_tfs = sum(1 for s in tf_signals if s > 0.3)
    bearish_tfs = sum(1 for s in tf_signals if s < -0.3)
    max_agreement = max(bullish_tfs, bearish_tfs)
    timeframe_agreement = (max_agreement / len(tf_signals)) * 100.0 if tf_signals else 0.0
    
    # 8. Regime Hint
    if adx > 25:
        if trend_direction == Direction.BUY:
            regime_hint = RegimeEnum.TRENDING_BULL
        elif trend_direction == Direction.SELL:
            regime_hint = RegimeEnum.TRENDING_BEAR
        else:
            regime_hint = RegimeEnum.RANGING
    else:
        regime_hint = RegimeEnum.RANGING
        
    # 9. Raw Indicators
    raw_indicators = {
        "tf_signals": tf_signals,
        "adx": adx_values,
        "atr": atr_values,
        "ema_20": ema_20_values,
        "volumes": volumes
    }
    
    snapshot = TechnicalSnapshot(
        symbol=symbol,
        signal_strength=signal_strength,
        trend_direction=trend_direction,
        adx=adx,
        atr_percentile=atr_percentile,
        ema_stack=ema_stack,
        support=support,
        resistance=resistance,
        timeframe_agreement=timeframe_agreement,
        regime_hint=regime_hint,
        raw_indicators=raw_indicators,
        timestamp=datetime.now(timezone.utc)
    )
    
    # Confidence Contribution Logic
    volume_confirms = sum(volumes) / len(volumes) > 0 if volumes else False
    adx_clear = adx > 25
    
    if timeframe_agreement >= 100.0 and adx_clear and volume_confirms:
        confidence = 0.85  # HIGH
    elif timeframe_agreement >= 75.0 or (volume_confirms and adx_clear):
        confidence = 0.70  # MEDIUM
    elif timeframe_agreement >= 50.0:
        confidence = 0.50  # LOW
    else:
        confidence = 0.30  # VERY LOW
        
    duration = (time.monotonic() - start_time) * 1000
    _log_perception(session, "TechnicalAgent", symbol, snapshot, confidence, duration)
    
    return snapshot, confidence
