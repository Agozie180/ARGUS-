"""Frontend bootstrap + Argus access.

Ensures the repo root is importable (so Streamlit pages can `from agents...`
regardless of launch directory) and exposes a single cached Argus instance.
The UI talks to the orchestrator in-process, so it works with no API server
running; set ARGUS_API_URL to route through the FastAPI backend instead.
"""
from __future__ import annotations

import os
import sys

# --- make the repo root importable from anywhere -----------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
for p in (_ROOT,):
    if p not in sys.path:
        sys.path.insert(0, p)

import streamlit as st  # noqa: E402
from agents.orchestrator import Argus  # noqa: E402
from core import demo_scenarios  # noqa: E402
from core.models import Mode  # noqa: E402


@st.cache_resource
def get_argus() -> Argus:
    return Argus()


def mode_from_label(label: str) -> Mode:
    return Mode.BEGINNER if label.lower().startswith("begin") else Mode.PROFESSIONAL


SCENARIOS = demo_scenarios.SCENARIOS
WOW_SCENARIO = demo_scenarios.WOW_SCENARIO
WOW_NARRATIVE = demo_scenarios.WOW_NARRATIVE
