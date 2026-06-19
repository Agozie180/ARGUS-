import json
import logging
import os
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import List
import asyncio

from config import Direction, ConfidenceScore, SessionState, RegimeEnum
from regime_classifier import RegimeState
from agents.technical_agent import TechnicalSnapshot
from agents.sentiment_agent import SentimentSnapshot
from agents.onchain_macro_agent import MacroSnapshot

logger = logging.getLogger(__name__)

try:
    import litellm
    litellm_available = True
except ImportError:
    litellm_available = False

@dataclass
class Decision:
    action: Direction
    symbol: str
    entry_price: float
    stop_loss: float
    take_profit: float
    raw_size_pct: float
    confidence_score: ConfidenceScore
    reasoning_trace: List[str]
    regime_state: RegimeState
    session_snapshot: dict
    timestamp: datetime

async def _llm_reason(tech, sent, macro, regime_state, session) -> dict:
    prompt = f"""You are an elite crypto trading agent. Analyze the market data and decide whether to BUY, SELL, or NO_TRADE.
    
    Current Regime: {regime_state.regime.value} (Conf: {regime_state.regime_confidence:.2f})
    Historical Context: {regime_state.historical_outcome_summary}
    Session PnL: {session.daily_pnl_pct:.2%}, Consecutive Losses: {session.consecutive_losses}
    
    Technicals: ADX {tech.adx:.1f}, EMA Stack {tech.ema_stack}, ATR % {tech.atr_percentile:.1f}, Support {tech.support}, Resistance {tech.resistance}
    Sentiment: F&G {sent.fear_greed_index}, Funding {sent.funding_signal.value}, News Score {sent.news_sentiment_score:.2f}
    Macro: ETF Flow {macro.etf_flow_signal.value}, Whale Flow {macro.whale_signal.value}, DXY {macro.dxy_trend}
    
    Respond in JSON only:
    {{
      "reasoning_trace": ["OBSERVE: ...", "ORIENT: ...", "HYPOTHESIZE: ...", "CHALLENGE: ...", "DECIDE: ..."],
      "action": "BUY" | "SELL" | "NO_TRADE",
      "entry_price": float,
      "stop_loss": float,
      "take_profit": float
    }}"""
    
    try:
        response = await litellm.completion(
            model="gpt-4o-mini", # Fallback to ensure availability
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.warning(f"LLM reasoning failed, using rule-based fallback: {e}")
        return None

def _rule_based_reason(tech, sent, macro, regime_state, session) -> dict:
    current_price = tech.raw_indicators.get("close", (tech.support + tech.resistance) / 2 or 100.0)
    atr = tech.raw_indicators.get("atr", [100.0])[0] if tech.raw_indicators.get("atr") else 100.0
    action = "NO_TRADE"
    entry, sl, tp = current_price, 0.0, 0.0
    
    if regime_state.regime == RegimeEnum.TRENDING_BULL and tech.ema_stack == "BULL":
        action, entry, sl, tp = "BUY", current_price, current_price - atr, current_price + (2*atr)
    elif regime_state.regime == RegimeEnum.TRENDING_BEAR and tech.ema_stack == "BEAR":
        action, entry, sl, tp = "SELL", current_price, current_price + atr, current_price - (2*atr)
        
    return {
        "reasoning_trace": [
            "OBSERVE: Market data analyzed.",
            "ORIENT: Regime assessed.",
            f"HYPOTHESIZE: Proposing {action}.",
            "CHALLENGE: Risk checked.",
            f"DECIDE: Action is {action}."
        ],
        "action": action, "entry_price": entry, "stop_loss": sl, "take_profit": tp
    }

async def decide(symbol, tech, tech_conf, sent, sent_conf, macro, macro_conf, regime_state, session) -> Decision:
    cs = ConfidenceScore.build(tech_conf, sent_conf, macro_conf, regime_state.regime_confidence, regime_state.regime)
    
    # Get decision from LLM or fallback
    llm_result = await _llm_reason(tech, sent, macro, regime_state, session) if litellm_available else None
    if not llm_result:
        llm_result = _rule_based_reason(tech, sent, macro, regime_state, session)
        
    try:
        action_str = llm_result.get("action", "NO_TRADE").upper()
        action = Direction[action_str] if action_str in Direction.__members__ else Direction.NO_TRADE
        entry_price = float(llm_result.get("entry_price", 0.0))
        stop_loss = float(llm_result.get("stop_loss", 0.0))
        take_profit = float(llm_result.get("take_profit", 0.0))
        trace = llm_result.get("reasoning_trace", ["Decision engine processed."])
    except Exception:
        action, entry_price, stop_loss, take_profit, trace = Direction.NO_TRADE, 0.0, 0.0, 0.0, ["Error parsing decision."]

    raw_size_pct = 0.02
    if regime_state.regime == RegimeEnum.HIGH_VOL:
        raw_size_pct *= 0.5

    # HARD GATE CHECK
    if not cs.gate_passed:
        action = Direction.NO_TRADE
        entry_price = 0.0
        stop_loss = 0.0
        take_profit = 0.0
        trace.append(f"GATE OVERRIDE: Composite {cs.composite_confidence:.1%} < Threshold {cs.required_threshold:.1%}. Trade blocked.")

    decision = Decision(
        action=action, symbol=symbol, entry_price=entry_price, stop_loss=stop_loss,
        take_profit=take_profit, raw_size_pct=raw_size_pct, confidence_score=cs,
        reasoning_trace=trace, regime_state=regime_state, session_snapshot=session.to_dict(),
        timestamp=datetime.now(timezone.utc)
    )
    
    with open("decisions.jsonl", "a") as f:
        f.write(json.dumps(asdict(decision), default=str) + "\n")
        
    return decision