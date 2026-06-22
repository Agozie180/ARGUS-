"""Capital Protection Score (CPS) — Argus' signature proprietary metric.

Most trading metrics measure the value created by *taking* trades. The CPS
measures the value created by *avoiding* bad ones — the thing a guardian is
actually for.

It rolls five guardian behaviours into a single 0–100 score:
  - rejected trades            (discipline to say NO)
  - potential losses avoided   (quantified downside dodged)
  - risk exposure avoided      (capital kept off the table)
  - FOMO trades blocked        (refusing to chase the top)
  - low-liquidity traps avoided(refusing slippage traps)

The score rewards catching *dangerous* setups, not blanket rejection — a high
CPS means Argus is actively protecting capital, not merely inactive.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List


# Category labels emitted by the Signal Honesty Engine.
FOMO = "FOMO_BLOCKED"
LIQUIDITY_TRAP = "LIQUIDITY_TRAP_AVOIDED"
LOW_DATA = "LOW_DATA_QUALITY_AVOIDED"
HIGH_RISK = "HIGH_RISK_AVOIDED"
POOR_RR = "POOR_RR_AVOIDED"
CONFLICT = "SIGNAL_CONFLICT_AVOIDED"

_HUMAN = {
    FOMO: "FOMO chases blocked",
    LIQUIDITY_TRAP: "Low-liquidity traps avoided",
    LOW_DATA: "Untrustworthy-data trades avoided",
    HIGH_RISK: "High-risk trades avoided",
    POOR_RR: "Poor reward:risk trades avoided",
    CONFLICT: "Conflicting-signal trades avoided",
}


@dataclass
class CPSReport:
    cps: float                      # 0–100 — the headline Capital Protection Score
    grade: str                      # A+ .. D, a quick read for the dashboard
    decisions: int
    trades_rejected: int
    rejection_rate_pct: float
    potential_loss_avoided_usd: float
    risk_exposure_avoided_usd: float
    fomo_blocked: int
    liquidity_traps_avoided: int
    category_breakdown: Dict[str, int]
    headline: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _grade(cps: float) -> str:
    if cps >= 90:
        return "A+"
    if cps >= 80:
        return "A"
    if cps >= 70:
        return "B"
    if cps >= 55:
        return "C"
    return "D"


def compute_cps(decisions: List[Dict[str, Any]], capital_usd: float = 10_000.0) -> CPSReport:
    """Aggregate journalled decision entries into a Capital Protection Score.

    `decisions` are the reflection journal's `type == "decision"` entries, each
    carrying `final_decision`, `loss_avoided_usd`, `exposure_usd` and
    `protection_categories`.
    """
    n = len(decisions)
    rejections = [d for d in decisions if d.get("final_decision") in ("NO TRADE", "REJECT")]
    rej = len(rejections)

    loss_avoided = sum(float(d.get("loss_avoided_usd", 0) or 0) for d in rejections)
    exposure_avoided = sum(float(d.get("exposure_usd", 0) or 0) for d in rejections)

    breakdown: Dict[str, int] = {}
    for d in rejections:
        for c in d.get("protection_categories", []) or []:
            breakdown[c] = breakdown.get(c, 0) + 1

    fomo_blocked = breakdown.get(FOMO, 0)
    liquidity_traps = breakdown.get(LIQUIDITY_TRAP, 0)

    # --- Score assembly (0–100) ----------------------------------------------
    # No history yet → a neutral-but-honest baseline rather than a fake 100.
    if n == 0:
        return CPSReport(
            cps=50.0, grade=_grade(50.0), decisions=0, trades_rejected=0,
            rejection_rate_pct=0.0, potential_loss_avoided_usd=0.0,
            risk_exposure_avoided_usd=0.0, fomo_blocked=0, liquidity_traps_avoided=0,
            category_breakdown={}, headline="No decisions yet — run an analysis to start protecting capital.",
        )

    rejection_rate = rej / n
    # Discipline: rewards saying NO when warranted (cap contribution at a
    # healthy ~50% rejection rate so it never pays to reject everything).
    discipline = min(rejection_rate / 0.5, 1.0) * 40.0
    # Magnitude: quantified downside dodged, normalised against capital at risk.
    magnitude = min(loss_avoided / (capital_usd * 0.10), 1.0) * 30.0
    # Specificity: catching the *named* dangerous patterns, not just abstaining.
    dangerous = sum(breakdown.get(c, 0) for c in (FOMO, LIQUIDITY_TRAP, LOW_DATA, HIGH_RISK))
    specificity = min(dangerous / n, 1.0) * 30.0

    cps = round(min(discipline + magnitude + specificity, 100.0), 1)

    headline = (
        f"Argus protected ~${loss_avoided:,.0f} of downside across {rej} rejected "
        f"trade(s); CPS {cps:.0f}/100 ({_grade(cps)})."
        if rej else
        f"No rejections yet across {n} decision(s) — capital deployed within limits."
    )

    return CPSReport(
        cps=cps,
        grade=_grade(cps),
        decisions=n,
        trades_rejected=rej,
        rejection_rate_pct=round(rejection_rate * 100, 1),
        potential_loss_avoided_usd=round(loss_avoided, 2),
        risk_exposure_avoided_usd=round(exposure_avoided, 2),
        fomo_blocked=fomo_blocked,
        liquidity_traps_avoided=liquidity_traps,
        category_breakdown=breakdown,
        headline=headline,
    )


def impact_statement(is_alpha: bool, categories: List[str], loss_avoided_usd: float,
                     exposure_usd: float) -> str:
    """Per-analysis 'Capital Protection Impact' line for Judge Mode."""
    if not is_alpha:
        return (
            "Positive expected value — capital is being deployed within risk "
            "limits, not protected by abstaining."
        )
    caught = ", ".join(_HUMAN.get(c, c) for c in categories) or "an unfavourable setup"
    return (
        f"+${loss_avoided_usd:,.0f} estimated downside avoided "
        f"(${exposure_usd:,.0f} exposure kept off the table). Danger caught: {caught}."
    )
