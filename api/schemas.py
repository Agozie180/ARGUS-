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
    scenario: Optional[Dict[str, Any]] = None
    wow_narrative: Optional[str] = None


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


class LearningReport(BaseModel):
    total_decisions: int
    total_trades: int
    trades_rejected: int
    rejection_rate_pct: float
    win_rate_pct: float
    estimated_capital_saved_usd: float
    top_lesson: str
