"""Session-aware confidence thresholds.

Liquidity, follow-through and trap-rate differ by trading session, so the bar
for *taking* a trade should differ too. Argus raises its conviction threshold
as the day's dominant session gets more efficient / crowded:

    Asian     65%   — thinner, choppier; a modest edge is workable
    London    72%   — deeper, trendier; demand more before committing
    New York  75%   — most efficient / news-driven; only the cleanest setups

The threshold gates the TAKE decision in the Signal Honesty Engine.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class TradingSession(str, Enum):
    ASIAN = "ASIAN"
    LONDON = "LONDON"
    NEW_YORK = "NEW_YORK"


# Confidence (0–100) required to TAKE a trade, by session.
SESSION_CONFIDENCE = {
    TradingSession.ASIAN: 65.0,
    TradingSession.LONDON: 72.0,
    TradingSession.NEW_YORK: 75.0,
}

SESSION_LABEL = {
    TradingSession.ASIAN: "Asian",
    TradingSession.LONDON: "London",
    TradingSession.NEW_YORK: "New York",
}


def session_for_hour(utc_hour: int) -> TradingSession:
    """Map a UTC hour [0,23] to its dominant trading session.

    Ranges (UTC): Asian 22:00–06:59, London 07:00–11:59,
    New York 12:00–20:59, then 21:00 rolls back into the Asian open.
    """
    h = utc_hour % 24
    if 7 <= h <= 11:
        return TradingSession.LONDON
    if 12 <= h <= 20:
        return TradingSession.NEW_YORK
    return TradingSession.ASIAN  # 21:00–06:59


def current_session(now: Optional[datetime] = None) -> TradingSession:
    """The active session right now (UTC), or for a supplied datetime."""
    now = now or datetime.now(timezone.utc)
    return session_for_hour(now.hour)


def confidence_threshold(session: TradingSession) -> float:
    return SESSION_CONFIDENCE[session]
