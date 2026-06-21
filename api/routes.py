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
