"""The Argus orchestrator — the single facade over the whole guardian.

Pipeline for every analysis:
    Bitget/market data  ->  Market Intelligence
                        ->  scoring (4 meters)
                        ->  Risk Guardian (sizing, health)
                        ->  Trade Validator (Signal Honesty Engine)
                        ->  Judge Mode (full verdict)
                        ->  Reflection (journal)

The API and the Streamlit frontend both call this; nothing else needs to know
how the agents fit together.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.models import MarketSnapshot, Mode, Direction, FinalDecision
from core.scoring import compute_scores
from core.judge import judge as build_judge_report
from core import demo_scenarios

from services.bitget import BitgetService
from agents.market_intelligence import MarketIntelligenceAgent
from agents.risk_guardian import RiskGuardianAgent
from agents.trade_validator import TradeValidatorAgent
from agents.reflection import ReflectionAgent
from agents.execution import ExecutionAgent


class Argus:
    def __init__(self, capital_usd: float = 10_000.0):
        self.capital_usd = capital_usd
        self.data = BitgetService()
        self.market = MarketIntelligenceAgent()
        self.risk = RiskGuardianAgent()
        self.validator = TradeValidatorAgent()
        self.reflection = ReflectionAgent()
        self.execution = ExecutionAgent()

    # --- core entry points ----------------------------------------------------
    def analyze_snapshot(self, s: MarketSnapshot, mode: Mode = Mode.PROFESSIONAL,
                         journal: bool = True) -> Dict[str, Any]:
        scores = compute_scores(s)
        intelligence = self.market.analyze(s)
        risk = self.risk.assess(s, scores, capital_usd=self.capital_usd)
        validation = self.validator.validate(s, scores, capital_usd=self.capital_usd)
        report = build_judge_report(s, mode=mode, capital_usd=self.capital_usd)

        capital_protected = 0.0
        if validation.is_no_trade_alpha:
            capital_protected = round(self.capital_usd * 0.10 * (scores.risk / 100.0), 2)

        result = {
            "data_mode": self.data.mode,
            "snapshot": s.to_dict(),
            "intelligence": intelligence.to_dict(),
            "scores": scores.to_dict(),
            "risk": risk.to_dict(),
            "validation": validation.to_dict(),
            "judge": report.to_dict(),
            "capital_protected_usd": capital_protected,
        }

        if journal:
            self.reflection.journal({
                "type": "decision",
                "symbol": s.symbol,
                "final_decision": report.final_decision.value,
                "setup_quality": report.setup_quality.value,
                "confidence": scores.confidence,
                "risk": scores.risk,
                "data_quality": scores.data_quality,
                "capital_protected_usd": capital_protected,
            })
        return result

    def analyze(self, symbol: str, mode: Mode = Mode.PROFESSIONAL, product: str = "futures",
                journal: bool = True) -> Dict[str, Any]:
        s = self.data.get_snapshot(symbol, product=product)
        return self.analyze_snapshot(s, mode=mode, journal=journal)

    def scan(self, symbols: Optional[List[str]] = None, mode: Mode = Mode.PROFESSIONAL) -> List[Dict[str, Any]]:
        out = []
        for s in self.data.scan(symbols):
            r = self.analyze_snapshot(s, mode=mode, journal=False)
            out.append({
                "symbol": s.symbol,
                "decision": r["judge"]["final_decision"],
                "setup_quality": r["judge"]["setup_quality"],
                "confidence": r["scores"]["confidence"],
                "risk": r["scores"]["risk"],
                "data_quality": r["scores"]["data_quality"],
                "trade_quality": r["scores"]["trade_quality"],
                "direction": s.direction_bias.value,
            })
        # Best opportunities first; rejections sink to the bottom.
        out.sort(key=lambda x: (x["decision"] != "TAKE TRADE", -x["trade_quality"]))
        return out

    def demo(self, scenario: str, mode: Mode = Mode.PROFESSIONAL) -> Dict[str, Any]:
        s = demo_scenarios.get_scenario(scenario)
        meta = demo_scenarios.SCENARIOS[scenario.strip().upper()]
        result = self.analyze_snapshot(s, mode=mode, journal=False)
        result["scenario"] = {
            "key": scenario.strip().upper(),
            "name": meta["name"],
            "teaches": meta["teaches"],
        }
        return result

    def wow_moment(self, mode: Mode = Mode.PROFESSIONAL) -> Dict[str, Any]:
        result = self.demo(demo_scenarios.WOW_SCENARIO, mode=mode)
        result["wow_narrative"] = demo_scenarios.WOW_NARRATIVE
        return result

    def learning_report(self) -> Dict[str, Any]:
        return self.reflection.learning_report()
