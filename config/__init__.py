from pydantic_settings import BaseSettings, SettingsConfigDict
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    BITGET_API_KEY: str | None = None
    BITGET_SECRET_KEY: str | None = None
    BITGET_PASSPHRASE: str | None = None
    PAPER_TRADING: bool = True  # never disable without reading risk_guardian.py
    SYMBOLS: list[str] = ["BTCUSDT", "ETHUSDT"]
    CYCLE_INTERVAL_SECONDS: int = 900  # 15 min default
    CONFIDENCE_THRESHOLD_DEFAULT: float = 0.65
    CONFIDENCE_THRESHOLD_HIGH_VOL: float = 0.75
    CONFIDENCE_THRESHOLD_UNKNOWN: float = 0.80
    KELLY_FRACTION: float = 0.25
    MAX_DAILY_LOSS_PCT: float = 0.05
    MAX_POSITION_PCT: float = 0.10
    CHROMA_PATH: str = "./chroma_db"
    LOG_LEVEL: str = "INFO"
    HUMAN_IN_LOOP: bool = False

settings = Settings()

class RegimeEnum(str, Enum):
    TRENDING_BULL = "TRENDING_BULL"
    TRENDING_BEAR = "TRENDING_BEAR"
    RANGING = "RANGING"
    HIGH_VOL = "HIGH_VOL"
    LOW_VOL = "LOW_VOL"
    UNKNOWN = "UNKNOWN"

class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    CLOSE = "CLOSE"
    NO_TRADE = "NO_TRADE"

class FearGreedZone(str, Enum):
    EXTREME_FEAR = "EXTREME_FEAR"
    FEAR = "FEAR"
    NEUTRAL = "NEUTRAL"
    GREED = "GREED"
    EXTREME_GREED = "EXTREME_GREED"

class InstitutionalBias(str, Enum):
    ACCUMULATING = "ACCUMULATING"
    DISTRIBUTING = "DISTRIBUTING"
    NEUTRAL = "NEUTRAL"

@dataclass(frozen=True)
class ConfidenceScore:
    technical_confidence: float
    sentiment_confidence: float
    macro_confidence: float
    regime_confidence: float
    composite_confidence: float
    required_threshold: float
    gate_passed: bool
    gate_reason: str

    @classmethod
    def build(cls, tech: float, sent: float, macro: float, regime: float, regime_enum: RegimeEnum) -> "ConfidenceScore":
        composite = (0.4 * tech) + (0.25 * sent) + (0.2 * macro) + (0.15 * regime)
        
        if regime_enum == RegimeEnum.HIGH_VOL:
            threshold = settings.CONFIDENCE_THRESHOLD_HIGH_VOL
        elif regime_enum == RegimeEnum.UNKNOWN:
            threshold = settings.CONFIDENCE_THRESHOLD_UNKNOWN
        else:
            threshold = settings.CONFIDENCE_THRESHOLD_DEFAULT
            
        passed = composite >= threshold
        reason = f"Composite {composite:.4f} {'>=' if passed else '<'} Threshold {threshold:.2f} ({regime_enum.value})"
        
        return cls(
            technical_confidence=tech,
            sentiment_confidence=sent,
            macro_confidence=macro,
            regime_confidence=regime,
            composite_confidence=composite,
            required_threshold=threshold,
            gate_passed=passed,
            gate_reason=reason
        )

@dataclass
class SessionState:
    session_id: str = field(default_factory=lambda: str(uuid4()))
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    cycle_count: int = 0
    daily_pnl: float = 0.0
    daily_pnl_pct: float = 0.0
    active_trades: list[str] = field(default_factory=list)
    halted: bool = False
    halt_reason: str | None = None
    consecutive_losses: int = 0
    last_regime: RegimeEnum = RegimeEnum.UNKNOWN
    last_cycle_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def update_after_trade(self, pnl: float) -> None:
        self.daily_pnl += pnl
        if pnl < 0:
            self.consecutive_losses += 1
        elif pnl > 0:
            self.consecutive_losses = 0
            
    def should_halt(self) -> bool:
        if self.consecutive_losses >= 3:
            self.halted = True
            self.halt_reason = "Circuit breaker: 3 consecutive losses"
            return True
        if self.daily_pnl_pct <= -settings.MAX_DAILY_LOSS_PCT:
            self.halted = True
            self.halt_reason = f"Circuit breaker: Max daily loss exceeded ({self.daily_pnl_pct:.2%})"
            return True
        return False

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at.isoformat(),
            "cycle_count": self.cycle_count,
            "daily_pnl": self.daily_pnl,
            "daily_pnl_pct": self.daily_pnl_pct,
            "active_trades": self.active_trades,
            "halted": self.halted,
            "halt_reason": self.halt_reason,
            "consecutive_losses": self.consecutive_losses,
            "last_regime": self.last_regime.value if isinstance(self.last_regime, RegimeEnum) else self.last_regime,
            "last_cycle_at": self.last_cycle_at.isoformat()
        }

@dataclass(frozen=True)
class TradingSignal:
    symbol: str
    direction: Direction
    confidence_score: ConfidenceScore
    entry_price: float
    stop_loss: float
    take_profit: float
    reasoning: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass(frozen=True)
class RiskParams:
    max_position_pct: float
    kelly_fraction: float
    var_limit: float
    circuit_breaker_daily_loss_pct: float
