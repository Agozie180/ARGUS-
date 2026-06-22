"""Agent 4 — Reflection.

Trade journaling, post-trade review, mistake detection and a continuous
learning report. File-based and fully offline (no LLM required); if an LLM is
configured later it can enrich the narrative, but the agent never depends on it.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from core.cps import compute_cps

JOURNAL_PATH = os.getenv("ARGUS_JOURNAL", "argus_journal.jsonl")


class ReflectionAgent:
    name = "Reflection"

    def __init__(self, path: str = JOURNAL_PATH, capital_usd: float = 10_000.0):
        self.path = path
        self.capital_usd = capital_usd

    def journal(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        entry = {**entry, "logged_at": datetime.now(timezone.utc).isoformat()}
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except OSError:
            pass
        return entry

    def review_trade(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """Post-trade review with simple, rule-based mistake detection."""
        pnl = float(trade.get("pnl_pct", 0.0))
        conf = float(trade.get("confidence", 0.0))
        risk = float(trade.get("risk", 0.0))
        mistakes: List[str] = []

        if pnl < 0 and conf < 60:
            mistakes.append("Entered on sub-60 confidence — should have waited.")
        if pnl < 0 and risk > 70:
            mistakes.append("Took an elevated-risk trade that did not pay.")
        if pnl > 0 and conf >= 70:
            lesson = "High-conviction setup paid off — repeat this discipline."
        elif pnl > 0:
            lesson = "Won, but on a thin edge — don't over-learn from luck."
        else:
            lesson = "Loss within plan — risk was controlled; review entry timing."

        return {
            "trade_id": trade.get("trade_id"),
            "outcome": "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "FLAT",
            "mistakes": mistakes,
            "lesson": lesson,
            "what_worked": "Risk was sized and capped." if risk <= 70 else "",
        }

    def learning_report(self) -> Dict[str, Any]:
        """Aggregate the journal into a continuous-learning summary."""
        entries = self._read()
        trades = [e for e in entries if e.get("type") == "trade_closed"]
        decisions = [e for e in entries if e.get("type") == "decision"]
        rejections = [d for d in decisions if d.get("final_decision") in ("NO TRADE", "REJECT")]

        wins = [t for t in trades if float(t.get("pnl_pct", 0)) > 0]
        win_rate = len(wins) / len(trades) * 100 if trades else 0.0
        capital_saved = sum(float(d.get("capital_protected_usd", 0)) for d in rejections)

        cps = compute_cps(decisions, capital_usd=self.capital_usd).to_dict()

        return {
            "total_decisions": len(decisions),
            "total_trades": len(trades),
            "trades_rejected": len(rejections),
            "rejection_rate_pct": round(len(rejections) / len(decisions) * 100, 1) if decisions else 0.0,
            "win_rate_pct": round(win_rate, 1),
            "estimated_capital_saved_usd": round(capital_saved, 2),
            "cps": cps,
            "top_lesson": (
                "Discipline of standing aside is Argus' biggest edge."
                if rejections else "Build more history to learn from."
            ),
        }

    def _read(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.path):
            return []
        out = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return out
