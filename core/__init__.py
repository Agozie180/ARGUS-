"""Argus core domain: models, scoring, the Signal Honesty Engine, Judge Mode,
explainability, and built-in demo scenarios.

This package is intentionally dependency-light (standard library only) so the
guardian logic runs in any environment — a fresh clone analyses trades with no
external services, API keys, or ML stack required.
"""
from core.models import (
    Direction,
    Mode,
    SetupQuality,
    FinalDecision,
    MarketSnapshot,
    Scores,
    JudgeReport,
)

__all__ = [
    "Direction",
    "Mode",
    "SetupQuality",
    "FinalDecision",
    "MarketSnapshot",
    "Scores",
    "JudgeReport",
]
