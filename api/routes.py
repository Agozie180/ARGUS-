"""Argus API routes."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from core.models import Mode
from core import demo_scenarios
from agents.orchestrator import Argus
from api import schemas

VERSION = "1.0.0"

router = APIRouter()
_argus = Argus()


def _mode(mode: str) -> Mode:
    try:
        return Mode(mode.upper())
    except ValueError:
        return Mode.PROFESSIONAL


@router.get("/health", response_model=schemas.HealthResponse, tags=["meta"])
def health():
    return schemas.HealthResponse(data_mode=_argus.data.mode, version=VERSION)


@router.get("/market/status", response_model=schemas.MarketStatusResponse, tags=["meta"])
def market_status():
    """Live Bitget market-data connectivity — proves the data source for judges."""
    return _argus.market_status()


@router.get("/symbols", tags=["analysis"])
def symbols(limit: int = Query(20, ge=1, le=100)):
    """Dynamically discovered top-liquidity Bitget USDT symbols (live)."""
    return {"symbols": _argus.discover_symbols(limit=limit)}


@router.get("/execution/status", tags=["execution"])
def execution_status():
    """Current execution mode (PAPER/LIVE) + safety gates + recent order log."""
    return _argus.execution_status()


@router.get("/analyze/{symbol}", response_model=schemas.AnalysisResponse, tags=["analysis"])
def analyze(symbol: str, mode: str = Query("professional"), product: str = Query("futures")):
    """Full guardian analysis for a symbol (Judge Mode verdict + meters)."""
    return _argus.analyze(symbol.upper(), mode=_mode(mode), product=product)


@router.get("/scan", response_model=List[schemas.ScanRow], tags=["analysis"])
def scan(symbols: Optional[str] = Query(None, description="Comma-separated symbols")):
    syms = [s.strip().upper() for s in symbols.split(",")] if symbols else None
    return _argus.scan(syms)


@router.get("/scenarios", response_model=List[schemas.ScenarioInfo], tags=["demo"])
def scenarios():
    return [
        {"key": k, "name": v["name"], "teaches": v["teaches"]}
        for k, v in demo_scenarios.SCENARIOS.items()
    ]


@router.get("/demo/{scenario}", response_model=schemas.AnalysisResponse, tags=["demo"])
def demo(scenario: str, mode: str = Query("professional")):
    try:
        return _argus.demo(scenario, mode=_mode(mode))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/wow", response_model=schemas.AnalysisResponse, tags=["demo"])
def wow(mode: str = Query("professional")):
    """The signature WOW moment — a setup most bots buy, Argus rejects."""
    return _argus.wow_moment(mode=_mode(mode))


@router.get("/journal", response_model=schemas.LearningReport, tags=["analysis"])
def journal():
    return _argus.learning_report()


@router.get("/cps", response_model=schemas.CPSReport, tags=["analysis"])
def cps():
    """Capital Protection Score — Argus' signature metric across representative setups."""
    return _argus.cps_overview()


@router.post("/execute/{symbol}", response_model=schemas.AnalysisResponse, tags=["execution"])
def execute(symbol: str, mode: str = Query("professional"), product: str = Query("futures")):
    """Analyze and, **only if Argus approves a TAKE TRADE**, open a paper position."""
    return _argus.execute(symbol.upper(), mode=_mode(mode), product=product)


@router.get("/positions", response_model=schemas.PortfolioResponse, tags=["execution"])
def positions():
    """Open + closed paper positions with realized P&L."""
    return _argus.portfolio()


@router.post("/positions/{trade_id}/close", response_model=schemas.CloseResponse, tags=["execution"])
def close_position(trade_id: str, exit_price: float = Query(..., gt=0)):
    """Close a paper position at a given exit price and run the post-trade review."""
    try:
        return _argus.close_position(trade_id, exit_price)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown trade_id '{trade_id}'.")
