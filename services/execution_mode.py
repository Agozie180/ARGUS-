"""Execution-mode resolution — the safety spine for paper vs live trading.

Argus is a guardian first. It ships **execution-ready** but **paper by default**,
and getting to a real Bitget order requires clearing several independent gates so
no real trade can ever happen by accident or on the public judging deployment:

    1. PAPER_TRADING must be explicitly set to ``false``.
    2. ARGUS_ALLOW_LIVE_TRADING must be explicitly set to ``true`` (deployment
       master switch — unset on the hosted demo, so it stays PAPER there).
    3. Bitget trading credentials (key/secret/passphrase) must be present.
    4. The operator must *arm* live trading at runtime by typing the exact
       confirmation phrase in the Execution Console (a per-session action).
    5. Each individual live order still passes an explicit ``confirm`` flag.

If any gate is unmet, Argus runs in PAPER mode: orders are simulated, recorded,
and never sent to the exchange. This module only *reports and resolves* the mode;
the actual order routing lives in agents/execution.py + services/bitget.py.
"""
from __future__ import annotations

import os
from typing import Dict

_TRUE = {"true", "1", "yes", "on"}

# The operator must type this verbatim in the Execution Console to arm live mode.
CONFIRM_PHRASE = "ENABLE LIVE TRADING"


def _env_true(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in _TRUE


def paper_trading() -> bool:
    """PAPER_TRADING env — defaults to True (safe). Live needs this to be false."""
    return os.getenv("PAPER_TRADING", "true").strip().lower() != "false"


def has_credentials() -> bool:
    return bool(
        os.getenv("BITGET_API_KEY")
        and os.getenv("BITGET_SECRET_KEY")
        and os.getenv("BITGET_PASSPHRASE")
    )


def live_allowed_by_deployment() -> bool:
    """True only when the deployment is explicitly configured to permit live
    trading. The hosted judging build leaves ARGUS_ALLOW_LIVE_TRADING unset, so
    this is False and the app is hard-locked to PAPER regardless of UI actions."""
    return (
        _env_true("ARGUS_ALLOW_LIVE_TRADING")
        and not paper_trading()
        and has_credentials()
    )


def blockers() -> Dict[str, bool]:
    """Per-gate readiness, for a transparent Execution Console checklist."""
    return {
        "paper_trading_disabled": not paper_trading(),
        "live_master_switch_on": _env_true("ARGUS_ALLOW_LIVE_TRADING"),
        "credentials_present": has_credentials(),
    }


def deployment_status() -> Dict[str, object]:
    b = blockers()
    allowed = live_allowed_by_deployment()
    return {
        "live_allowed_by_deployment": allowed,
        "paper_trading_default": paper_trading(),
        "blockers": b,
        "confirm_phrase": CONFIRM_PHRASE,
        "detail": (
            "Deployment permits live trading once armed in the Execution Console."
            if allowed else
            "Live trading is disabled by deployment configuration — running in PAPER mode."
        ),
    }
