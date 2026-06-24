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
from core.sessions import current_session
from core import demo_scenarios

from services.bitget import BitgetService
from services import execution_mode
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
        self.reflection = ReflectionAgent(capital_usd=capital_usd)
        self.execution = ExecutionAgent(bitget=self.data)
        # Runtime live-trading arm switch (off by default). Even when armed, the
        # deployment must independently permit live trading (execution_mode), so
        # this can never enable real orders on the judging build.
        self._live_armed = False

    # --- core entry points ----------------------------------------------------
    def analyze_snapshot(self, s: MarketSnapshot, mode: Mode = Mode.PROFESSIONAL,
                         journal: bool = True) -> Dict[str, Any]:
        # Resolve the active trading session once so the validator and Judge Mode
        # apply the same session-aware confidence threshold (Asian/London/NY).
        session = current_session()
        scores = compute_scores(s)
        intelligence = self.market.analyze(s)
        risk = self.risk.assess(s, scores, capital_usd=self.capital_usd)
        validation = self.validator.validate(s, scores, capital_usd=self.capital_usd, session=session)
        report = build_judge_report(s, mode=mode, capital_usd=self.capital_usd, session=session)

        capital_protected = 0.0
        if validation.is_no_trade_alpha:
            capital_protected = round(self.capital_usd * 0.10 * (scores.risk / 100.0), 2)

        result = {
            "data_mode": "LIVE-DATA" if s.is_live else "SIMULATED-DATA",
            "data_source": s.source,
            "market_type": s.market_type,
            "fetched_at": s.fetched_at,
            "snapshot": s.to_dict(),
            "intelligence": intelligence.to_dict(),
            "scores": scores.to_dict(),
            "risk": risk.to_dict(),
            "validation": validation.to_dict(),
            "judge": report.to_dict(),
            "capital_protected_usd": capital_protected,
            "session": validation.session,
            "confidence_threshold": validation.confidence_threshold,
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
                "protection_categories": validation.protection_categories,
                "exposure_usd": validation.exposure_usd,
                "loss_avoided_usd": validation.loss_avoided_usd,
            })
        return result

    def analyze(self, symbol: str, mode: Mode = Mode.PROFESSIONAL, product: str = "futures",
                journal: bool = True) -> Dict[str, Any]:
        s = self.data.get_snapshot(symbol, product=product)
        return self.analyze_snapshot(s, mode=mode, journal=journal)

    # --- Execution mode (paper by default, live multi-gated) ------------------
    def effective_mode(self) -> str:
        """The mode a trade would actually execute in right now: LIVE only when
        the deployment permits it AND the operator has armed it; else PAPER."""
        if execution_mode.live_allowed_by_deployment() and self._live_armed:
            return "LIVE"
        return "PAPER"

    def arm_live(self, confirm_phrase: str) -> Dict[str, Any]:
        """Arm live trading for this session — requires the exact confirm phrase
        and a deployment that permits live trading. Returns the new status."""
        if not execution_mode.live_allowed_by_deployment():
            return {"armed": False, "reason": "Deployment does not permit live trading.",
                    **self.execution_status()}
        if confirm_phrase.strip() != execution_mode.CONFIRM_PHRASE:
            return {"armed": False, "reason": "Confirmation phrase did not match.",
                    **self.execution_status()}
        self._live_armed = True
        return {"armed": True, **self.execution_status()}

    def disarm_live(self) -> Dict[str, Any]:
        self._live_armed = False
        return {"armed": False, **self.execution_status()}

    def execution_status(self) -> Dict[str, Any]:
        dep = execution_mode.deployment_status()
        return {
            "mode": self.effective_mode(),
            "armed": self._live_armed,
            **dep,
            "recent_orders": self.execution.recent_orders(),
        }

    # --- Execution (paper by default; live only when armed + permitted) -------
    def execute_snapshot(self, s: MarketSnapshot, mode: Mode = Mode.PROFESSIONAL,
                         journal: bool = True) -> Dict[str, Any]:
        """Analyze, then open a position **only** if Argus approves a TAKE TRADE.
        Routes to a real Bitget order only in armed+permitted LIVE mode; otherwise
        the fill is simulated and recorded. The guardian refuses to deploy capital
        on anything weaker than TAKE TRADE."""
        result = self.analyze_snapshot(s, mode=mode, journal=journal)
        exec_mode = self.effective_mode()
        decision = result["judge"]["final_decision"]
        scores, risk = result["scores"], result["risk"]

        if decision != FinalDecision.TAKE_TRADE.value:
            result["execution"] = {
                "executed": False, "mode": exec_mode,
                "reason": (f"Argus withheld execution — decision was {decision}. "
                           "Capital is only deployed on a TAKE TRADE. NO TRADE IS ALPHA™."),
            }
            return result

        size = risk["suggested_position_usd"]
        if size <= 0:
            result["execution"] = {
                "executed": False, "mode": exec_mode,
                "reason": "Risk Guardian sized this to $0 (drawdown halt or risk limits).",
            }
            return result

        pos = self.execution.open(
            symbol=s.symbol, direction=s.direction_bias, entry_price=s.price,
            size_usd=size, stop_loss=result["judge"]["invalidation_zone"],
            take_profit=result["judge"]["take_profit"],
            entry_confidence=scores["confidence"], entry_risk=scores["risk"],
            live=(exec_mode == "LIVE"),
        )
        if journal:
            self.reflection.journal({
                "type": "trade_opened", "trade_id": pos.trade_id, "symbol": s.symbol,
                "direction": pos.direction, "size_usd": pos.size_usd,
                "fill_price": pos.fill_price, "stop_loss": pos.stop_loss,
                "mode": pos.mode,
            })
        result["execution"] = {"executed": True, "mode": pos.mode, "position": pos.to_dict()}
        return result

    def execute(self, symbol: str, mode: Mode = Mode.PROFESSIONAL, product: str = "futures",
                journal: bool = True) -> Dict[str, Any]:
        s = self.data.get_snapshot(symbol, product=product)
        return self.execute_snapshot(s, mode=mode, journal=journal)

    def close_position(self, trade_id: str, exit_price: float) -> Dict[str, Any]:
        pos = self.execution.close(trade_id, exit_price)
        self.reflection.journal({
            "type": "trade_closed", "trade_id": pos.trade_id, "symbol": pos.symbol,
            "pnl_pct": pos.pnl_pct, "pnl_usd": pos.pnl_usd,
            "confidence": pos.entry_confidence, "risk": pos.entry_risk,
        })
        review = self.reflection.review_trade({
            "trade_id": pos.trade_id, "pnl_pct": pos.pnl_pct,
            "confidence": pos.entry_confidence, "risk": pos.entry_risk,
        })
        return {"position": pos.to_dict(), "review": review}

    def mark_to_market(self, prices: Dict[str, float]) -> List[Dict[str, Any]]:
        closed = self.execution.mark_to_market(prices)
        for pos in closed:
            self.reflection.journal({
                "type": "trade_closed", "trade_id": pos.trade_id, "symbol": pos.symbol,
                "pnl_pct": pos.pnl_pct, "pnl_usd": pos.pnl_usd,
                "confidence": pos.entry_confidence, "risk": pos.entry_risk,
            })
        return [p.to_dict() for p in closed]

    def portfolio(self) -> Dict[str, Any]:
        open_pos = self.execution.open_positions()
        closed_pos = self.execution.closed_positions()
        realized = round(sum(p.pnl_usd or 0 for p in closed_pos), 2)
        wins = sum(1 for p in closed_pos if (p.pnl_usd or 0) > 0)
        return {
            "open_positions": [p.to_dict() for p in open_pos],
            "closed_positions": [p.to_dict() for p in closed_pos],
            "open_count": len(open_pos),
            "closed_count": len(closed_pos),
            "realized_pnl_usd": realized,
            "wins": wins,
            "losses": len(closed_pos) - wins,
        }

    def scan(self, symbols: Optional[List[str]] = None, mode: Mode = Mode.PROFESSIONAL) -> List[Dict[str, Any]]:
        out = []
        for s in self.data.scan(symbols):
            r = self.analyze_snapshot(s, mode=mode, journal=False)
            # CPS impact: positive when the guardian protects capital by standing
            # aside (rejections), neutral/positive when it greenlights real edge.
            decision = r["judge"]["final_decision"]
            cps_impact = "+ protects capital" if decision in ("NO TRADE", "REJECT") else (
                "+ disciplined entry" if decision == "TAKE TRADE" else "neutral")
            out.append({
                "symbol": s.symbol,
                "price": s.price,
                "change_24h_pct": s.change_24h_pct,
                "decision": decision,
                "setup_quality": r["judge"]["setup_quality"],
                "confidence": r["scores"]["confidence"],
                "risk": r["scores"]["risk"],
                "data_quality": r["scores"]["data_quality"],
                "trade_quality": r["scores"]["trade_quality"],
                "direction": s.direction_bias.value,
                "source": s.source,
                "market_type": s.market_type,
                "fetched_at": s.fetched_at,
                "cps_impact": cps_impact,
            })
        # Best opportunities first; rejections sink to the bottom.
        out.sort(key=lambda x: (x["decision"] != "TAKE TRADE", -x["trade_quality"]))
        return out

    def market_status(self) -> Dict[str, Any]:
        """Live Bitget connectivity status for the UI/API data-source badge."""
        return self.data.market_status()

    def discover_symbols(self, limit: int = 20) -> List[str]:
        """Top-liquidity Bitget USDT symbols (live), falling back to the static universe."""
        return self.data.discover_symbols(limit=limit)

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

    def cps(self) -> Dict[str, Any]:
        """Live Capital Protection Score from the session journal (real track record)."""
        return self.reflection.learning_report()["cps"]

    def cps_overview(self) -> Dict[str, Any]:
        """Deterministic CPS across the six canonical scenarios — the showcase
        number for the dashboard. These are real guardian verdicts on a
        representative spread of setups, so it never reads as an empty 0."""
        from core.cps import compute_cps  # local import avoids a cycle at module load
        decisions = []
        for key in demo_scenarios.SCENARIOS:
            s = demo_scenarios.get_scenario(key)
            v = self.validator.validate(s, compute_scores(s), capital_usd=self.capital_usd)
            decisions.append({
                "final_decision": v.final_decision,
                "loss_avoided_usd": v.loss_avoided_usd,
                "exposure_usd": v.exposure_usd,
                "protection_categories": v.protection_categories,
            })
        return compute_cps(decisions, capital_usd=self.capital_usd).to_dict()
