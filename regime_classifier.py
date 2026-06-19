import json
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import List, Dict

from config import RegimeEnum, SessionState
from agents.technical_agent import TechnicalSnapshot
from agents.sentiment_agent import SentimentSnapshot
from agents.onchain_macro_agent import MacroSnapshot
from memory import Memory

logger = logging.getLogger(__name__)

@dataclass
class RegimeState:
    regime: RegimeEnum
    regime_confidence: float
    previous_regime: RegimeEnum
    regime_changed: bool
    similar_historical_regimes: List[Dict]
    historical_outcome_summary: str
    reasoning: str
    timestamp: datetime

def classify_regime(
    tech: TechnicalSnapshot, 
    sent: SentimentSnapshot, 
    macro: MacroSnapshot, 
    session: SessionState
) -> RegimeState:
    atr_p = tech.atr_percentile
    fg = sent.fear_greed_index
    adx = tech.adx
    ema_stack = tech.ema_stack
    headwind = macro.macro_headwind
    
    # Evaluate rules
    is_high_vol = (atr_p > 80 or fg < 20 or fg > 80)
    is_trend_bull = (adx > 25 and ema_stack == "BULL" and not headwind)
    is_trend_bear = (adx > 25 and ema_stack == "BEAR")
    is_ranging = (adx < 20 and atr_p < 50)
    is_low_vol = (atr_p < 20)
    
    active_rules = sum([is_high_vol, is_trend_bull, is_trend_bear, is_ranging, is_low_vol])
    
    # Determine regime based on priority and conflicts
    regime = RegimeEnum.UNKNOWN
    confidence = 0.50
    reasoning = ""
    
    if active_rules == 0:
        regime = RegimeEnum.UNKNOWN
        confidence = 0.20
        reasoning = "No data or no distinct rules met."
    elif active_rules > 2:
        regime = RegimeEnum.UNKNOWN
        confidence = 0.40 + (active_rules - 3) * 0.05  # 0.40-0.64 range
        reasoning = f"Multiple conflicts detected ({active_rules} rules active)."
    else:
        # Priority order evaluation
        if is_high_vol:
            regime = RegimeEnum.HIGH_VOL
            confidence = 0.90 if active_rules == 1 else 0.75
            reasoning = "High volatility detected (ATR/F&G)."
        elif is_trend_bull:
            regime = RegimeEnum.TRENDING_BULL
            confidence = 0.90 if active_rules == 1 else 0.75
            reasoning = "Bullish trend (ADX > 25, EMA BULL, no macro headwind)."
        elif is_trend_bear:
            regime = RegimeEnum.TRENDING_BEAR
            confidence = 0.90 if active_rules == 1 else 0.75
            reasoning = "Bearish trend (ADX > 25, EMA BEAR)."
        elif is_ranging:
            regime = RegimeEnum.RANGING
            confidence = 0.85 if active_rules == 1 else 0.70
            reasoning = "Ranging market (ADX < 20, ATR < 50th pct)."
        elif is_low_vol:
            regime = RegimeEnum.LOW_VOL
            confidence = 0.85 if active_rules == 1 else 0.70
            reasoning = "Low volatility (ATR < 20th pct)."
            
    previous_regime = session.last_regime
    regime_changed = (previous_regime != regime)
    
    # Memory retrieval (ChromaDB)
    similar_historical = []
    historical_summary = "No historical data available."
    try:
        mem = Memory()
        # Construct a simple feature vector for similarity search
        feature_vec = [adx, atr_p, fg, macro.macro_score]
        
        # Store current regime first
        regime_snapshot = {
            "regime_id": f"regime_{session.session_id}_{session.cycle_count}",
            "regime": regime.value,
            "adx": adx,
            "atr_percentile": atr_p,
            "fear_greed": fg,
            "macro_score": macro.macro_score,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        mem.store_regime(regime_snapshot)
        
        # Retrieve similar
        similar_historical = mem.retrieve_similar_regimes(feature_vec, n=5)
        if similar_historical:
            profitable = sum(1 for r in similar_historical if r.get("metadata", {}).get("pnl", 0) > 0)
            avg_ret = sum(r.get("metadata", {}).get("pnl", 0) for r in similar_historical) / len(similar_historical)
            historical_summary = f"In {len(similar_historical)} similar regimes: {profitable} profitable, avg return {avg_ret:.2f}%"
    except Exception as e:
        logger.warning(f"ChromaDB memory retrieval failed: {e}")
        
    state = RegimeState(
        regime=regime,
        regime_confidence=confidence,
        previous_regime=previous_regime,
        regime_changed=regime_changed,
        similar_historical_regimes=similar_historical,
        historical_outcome_summary=historical_summary,
        reasoning=reasoning,
        timestamp=datetime.now(timezone.utc)
    )
    
    # Log to file
    log_entry = {
        "session_id": session.session_id,
        "cycle": session.cycle_count,
        "regime_state": asdict(state),
        "timestamp": state.timestamp.isoformat()
    }
    with open("regime_log.jsonl", "a") as f:
        f.write(json.dumps(log_entry, default=str) + "\n")
        
    return state
