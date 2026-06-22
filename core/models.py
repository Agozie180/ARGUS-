"""Shared domain models for Argus — the AI Trading Guardian.

Everything that flows between the agents, the Signal Honesty Engine, Judge Mode
and the UI is typed here. Scores are expressed on a 0–100 scale so they map
directly onto the dashboard meters.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Optional


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class Mode(str, Enum):
    BEGINNER = "BEGINNER"
    PROFESSIONAL = "PROFESSIONAL"


class SetupQuality(str, Enum):
    """Phase 4 — graded quality of a potential setup."""
    REJECT = "REJECT"
    WATCH = "WATCH"
    POSSIBLE_SETUP = "POSSIBLE SETUP"
    HIGH_QUALITY_SETUP = "HIGH QUALITY SETUP"


class FinalDecision(str, Enum):
    """Phase 5 — Argus' final verdict on the trade."""
    TAKE_TRADE = "TAKE TRADE"
    WATCH = "WATCH"
    REJECT = "REJECT"
    NO_TRADE = "NO TRADE"


@dataclass
class MarketSnapshot:
    """A single, point-in-time read of a market. The agents consume this."""
    symbol: str
    price: float
    direction_bias: Direction = Direction.NEUTRAL

    # Trend / momentum
    timeframe_signals: Dict[str, float] = field(default_factory=dict)  # tf -> [-1, 1]
    adx: float = 0.0
    ema_stack: str = "MIXED"          # BULL | BEAR | MIXED
    rsi: float = 50.0
    momentum: float = 0.0             # [-1, 1]
    structure: str = "RANGE"          # UPTREND | DOWNTREND | RANGE

    # Volatility
    atr_pct: float = 1.0              # ATR as % of price
    volatility_score: float = 50.0    # 0 (calm) .. 100 (chaotic)

    # Liquidity
    liquidity_score: float = 70.0     # 0 (illiquid) .. 100 (deep)
    spread_bps: float = 2.0           # bid/ask spread in basis points
    volume_score: float = 0.6         # relative volume [0, 1]

    # Data quality inputs
    indicator_completeness: float = 1.0  # fraction of expected indicators present [0,1]
    data_freshness: float = 1.0          # 1.0 = fresh, decays toward 0 when stale

    # Levels
    support: float = 0.0
    resistance: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["direction_bias"] = self.direction_bias.value
        return d


@dataclass
class Scores:
    """The four meters that drive every Argus decision (all 0–100)."""
    confidence: float
    risk: float
    data_quality: float
    trade_quality: float
    components: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RiskAssessment:
    risk_score: float                 # 0 (safe) .. 100 (dangerous)
    suggested_position_pct: float     # fraction of capital
    suggested_position_usd: float
    risk_reward: float
    max_loss_usd: float
    portfolio_health: str             # HEALTHY | CAUTION | CRITICAL
    capital_preserved_usd: float = 0.0
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class JudgeReport:
    """Phase 5 — the full, explainable verdict produced for every analysis."""
    symbol: str
    price: float
    direction: Direction
    mode: Mode

    # Narrative
    trade_thesis: str
    bull_case: List[str]
    bear_case: List[str]
    why_trade_exists: str
    why_trade_could_fail: str
    why_trade_should_be_rejected: str
    what_would_improve: List[str]

    # Market context (Judge Mode)
    market_structure: str
    liquidity_analysis: str
    volatility_analysis: str
    capital_protection_impact: str

    # Session-aware conviction gate
    session: str
    confidence_threshold: float

    # Scores
    scores: Scores
    setup_quality: SetupQuality
    final_decision: FinalDecision

    # Levels
    entry_zone: List[float]           # [low, high]
    invalidation_zone: float
    take_profit: List[float]          # laddered targets

    # Honesty / capital protection
    rejection_reasons: List[str]
    is_no_trade_alpha: bool
    capital_protection_note: str

    # Explainability (Phase 6)
    explanation: str                  # rendered for the requested mode

    def to_dict(self) -> dict:
        d = asdict(self)
        d["direction"] = self.direction.value
        d["mode"] = self.mode.value
        d["setup_quality"] = self.setup_quality.value
        d["final_decision"] = self.final_decision.value
        d["scores"] = self.scores.to_dict()
        return d
