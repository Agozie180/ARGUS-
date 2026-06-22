"""Pydantic response schemas for the Argus API.

Responses are deliberately permissive (the orchestrator already returns clean,
JSON-serialisable dicts) — these models document the contract and power the
auto-generated OpenAPI docs at /docs.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "argus"
    data_mode: str
    version: str


class ScoreBlock(BaseModel):
    confidence: float
    risk: float
    data_quality: float
    trade_quality: float
    components: Dict[str, float] = Field(default_factory=dict)


class AnalysisResponse(BaseModel):
    data_mode: str
    snapshot: Dict[str, Any]
    intelligence: Dict[str, Any]
    scores: Dict[str, Any]
    risk: Dict[str, Any]
    validation: Dict[str, Any]
    judge: Dict[str, Any]
    capital_protected_usd: float
    session: Optional[str] = None
    confidence_threshold: Optional[float] = None
    execution: Optional[Dict[str, Any]] = None
    scenario: Optional[Dict[str, Any]] = None
    wow_narrative: Optional[str] = None


class PortfolioResponse(BaseModel):
    open_positions: List[Dict[str, Any]] = Field(default_factory=list)
    closed_positions: List[Dict[str, Any]] = Field(default_factory=list)
    open_count: int
    closed_count: int
    realized_pnl_usd: float
    wins: int
    losses: int


class CloseResponse(BaseModel):
    position: Dict[str, Any]
    review: Dict[str, Any]


class ScanRow(BaseModel):
    symbol: str
    decision: str
    setup_quality: str
    confidence: float
    risk: float
    data_quality: float
    trade_quality: float
    direction: str


class ScenarioInfo(BaseModel):
    key: str
    name: str
    teaches: str


class CPSReport(BaseModel):
    cps: float
    grade: str
    decisions: int
    trades_rejected: int
    rejection_rate_pct: float
    potential_loss_avoided_usd: float
    risk_exposure_avoided_usd: float
    fomo_blocked: int
    liquidity_traps_avoided: int
    category_breakdown: Dict[str, int] = Field(default_factory=dict)
    headline: str


class LearningReport(BaseModel):
    total_decisions: int
    total_trades: int
    trades_rejected: int
    rejection_rate_pct: float
    win_rate_pct: float
    estimated_capital_saved_usd: float
    cps: CPSReport
    top_lesson: str
