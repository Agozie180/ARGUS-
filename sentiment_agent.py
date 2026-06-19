import asyncio
import json
import time
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Tuple, List

from config import FearGreedZone, Direction, SessionState
from bitget_client import BitgetClient

logger = logging.getLogger(__name__)
bitget = BitgetClient()

@dataclass
class SentimentSnapshot:
    fear_greed_index: int          # 0–100
    fear_greed_zone: FearGreedZone
    fear_greed_signal: Direction   # contrarian: EXTREME_FEAR→BUY signal
    btc_long_short_ratio: float
    eth_long_short_ratio: float
    btc_funding_rate: float
    eth_funding_rate: float
    funding_signal: Direction      # contrarian above ±0.01% threshold
    news_headlines: List[str]      # last 6 hours
    news_sentiment_score: float    # -1.0 to +1.0 from keyword analysis
    composite_sentiment: float     # weighted combination
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

async def perceive(symbol: str, session: SessionState) -> Tuple[SentimentSnapshot, float]:
    start_time = time.monotonic()
    
    try:
        sent_data = await bitget.get_sentiment(symbol)
    except Exception as e:
        logger.warning(f"Failed to fetch sentiment for {symbol}: {e}. Using fallback neutral data.")
        sent_data = {}
        
    try:
        news_data = await bitget.get_news(symbol)
    except Exception as e:
        logger.warning(f"Failed to fetch news for {symbol}: {e}. Using fallback neutral data.")
        news_data = {}

    # 1. Fear & Greed
    fear_greed_index = int(sent_data.get("fear_greed_index", 50))
    if fear_greed_index <= 24:
        fear_greed_zone = FearGreedZone.EXTREME_FEAR
        fear_greed_signal = Direction.BUY
    elif fear_greed_index <= 44:
        fear_greed_zone = FearGreedZone.FEAR
        fear_greed_signal = Direction.BUY
    elif fear_greed_index <= 55:
        fear_greed_zone = FearGreedZone.NEUTRAL
        fear_greed_signal = Direction.HOLD
    elif fear_greed_index <= 75:
        fear_greed_zone = FearGreedZone.GREED
        fear_greed_signal = Direction.SELL
    else:
        fear_greed_zone = FearGreedZone.EXTREME_GREED
        fear_greed_signal = Direction.SELL

    # 2. Long/Short Ratios
    btc_long_short_ratio = float(sent_data.get("btc_long_short_ratio", 1.0))
    eth_long_short_ratio = float(sent_data.get("eth_long_short_ratio", 1.0))

    # 3. Funding Rates
    # Assuming API returns funding rate as a percentage float (e.g., 0.01 = 0.01%)
    # Logic: > +0.10% → bearish, < -0.05% → bullish, else neutral
    btc_funding_rate = float(sent_data.get("btc_funding_rate", 0.0))
    eth_funding_rate = float(sent_data.get("eth_funding_rate", 0.0))
    
    # Use the symbol's funding rate primarily, fallback to BTC
    primary_funding = eth_funding_rate if "ETH" in symbol else btc_funding_rate
    
    if primary_funding > 0.10:
        funding_signal = Direction.SELL
    elif primary_funding < -0.05:
        funding_signal = Direction.BUY
    else:
        funding_signal = Direction.HOLD

    # 4. News
    news_headlines = news_data.get("headlines", [])
    news_sentiment_score = float(news_data.get("sentiment_score", 0.0))

    # 5. Composite Sentiment (-1.0 to +1.0)
    fg_score = (fear_greed_index - 50) / 50.0 * -1.0  # Invert for contrarian
    funding_score = 0.0
    if funding_signal == Direction.BUY: funding_score = 1.0
    elif funding_signal == Direction.SELL: funding_score = -1.0
    
    composite_sentiment = (0.4 * fg_score) + (0.3 * funding_score) + (0.3 * news_sentiment_score)
    composite_sentiment = max(-1.0, min(1.0, composite_sentiment))

    snapshot = SentimentSnapshot(
        fear_greed_index=fear_greed_index,
        fear_greed_zone=fear_greed_zone,
        fear_greed_signal=fear_greed_signal,
        btc_long_short_ratio=btc_long_short_ratio,
        eth_long_short_ratio=eth_long_short_ratio,
        btc_funding_rate=btc_funding_rate,
        eth_funding_rate=eth_funding_rate,
        funding_signal=funding_signal,
        news_headlines=news_headlines,
        news_sentiment_score=news_sentiment_score,
        composite_sentiment=composite_sentiment,
        timestamp=datetime.now(timezone.utc)
    )

    # Confidence Contribution Logic
    aligned_count = 0
    expected_direction = Direction.BUY if composite_sentiment > 0.2 else (Direction.SELL if composite_sentiment < -0.2 else Direction.HOLD)
    
    if fear_greed_signal == expected_direction: aligned_count += 1
    if funding_signal == expected_direction: aligned_count += 1
    if (news_sentiment_score > 0 and expected_direction == Direction.BUY) or \
       (news_sentiment_score < 0 and expected_direction == Direction.SELL) or \
       (abs(news_sentiment_score) <= 0.2 and expected_direction == Direction.HOLD):
        aligned_count += 1

    if aligned_count == 3:
        confidence = 0.85  # HIGH
    elif aligned_count == 2:
        confidence = 0.65  # MEDIUM
    else:
        confidence = 0.40  # LOW

    duration = (time.monotonic() - start_time) * 1000
    _log_perception(session, "SentimentAgent", symbol, snapshot, confidence, duration)
    
    return snapshot, confidence
