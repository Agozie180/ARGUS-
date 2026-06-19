import json
import logging
from dataclasses import dataclass, asdict
from typing import Optional
from config import settings, SessionState
from decision_engine import Decision
from bitget_client import BitgetClient
from memory import Memory
from discipline import DisciplineEngine

logger = logging.getLogger(__name__)
bitget = BitgetClient()

@dataclass
class RiskDecision:
    approved: bool
    adjusted_size_usd: float
    adjusted_size_pct: float
    adjusted_stop: float
    trailing_stop_active: bool
    rejection_reason: Optional[str]
    var_estimate: float
    kelly_fraction_used: float
    confidence_size_scalar: float
    log_entry: dict

async def assess_risk(decision: Decision, session: SessionState) -> RiskDecision:
    portfolio_value = 10000.0
    try:
        balance_data = await bitget.get_balance()
        portfolio_value = float(balance_data.get("totalEquity", balance_data.get("balance", 10000.0)))
    except Exception:
        logger.warning("Failed to fetch balance. Using fallback 10,000 USD.")

    approved = False
    adjusted_size_usd = 0.0
    adjusted_size_pct = 0.0
    adjusted_stop = decision.stop_loss
    trailing_stop_active = False
    rejection_reason = None
    var_estimate = 0.0
    kelly_fraction_used = 0.0
    confidence_size_scalar = decision.confidence_score.composite_confidence

    # --- THE SWORN OATH (DISCIPLINE FIRST) ---
    discipline = DisciplineEngine(session)
    oath_passed, oath_reason = discipline.enforce_oath()
    
    if not oath_passed:
        rejection_reason = oath_reason
        logger.warning(f"🛡️ DISCIPLINE BLOCK: {oath_reason}")
        
    # --- RISK MATHEMATICS ---
    elif session.daily_pnl_pct <= -settings.MAX_DAILY_LOSS_PCT:
        session.halted = True
        session.halt_reason = "Daily loss limit hit"
        rejection_reason = "[HALT] Daily loss limit hit"
        
    elif len(session.active_trades) >= 3:
        rejection_reason = "[EXPOSURE] Max active positions (3) reached"
        
    else:
        size_multiplier = 1.0
        if session.consecutive_losses == 2: # Danger zone
            size_multiplier *= 0.50
            logger.info("⚠️ Danger zone: 2 consecutive losses. Size reduced 50%.")
            
        edge = 0.1  # Default 10% edge
        odds = 1.5
        try:
            mem = Memory()
            stats = mem.get_session_stats(session.session_id)
            win_rate = stats.get("win_rate", 0.5)
            if win_rate > 0: edge = (2 * win_rate) - 1.0
            if stats.get("avg_rr", 0) > 0: odds = stats["avg_rr"]
        except: pass
            
        kelly_f = (edge / odds) * settings.KELLY_FRACTION if odds > 0 and edge > 0 else 0.0
        position_usd = portfolio_value * kelly_f * confidence_size_scalar * size_multiplier
        kelly_fraction_used = kelly_f * size_multiplier
        
        atr_pct = 0.02 
        position_var = position_usd * atr_pct * 1.645
        var_estimate = position_var
        max_var = portfolio_value * 0.02
        
        if position_var > max_var:
            position_usd *= (max_var / position_var)
            
        max_pos_usd = portfolio_value * settings.MAX_POSITION_PCT
        if position_usd > max_pos_usd:
            position_usd = max_pos_usd
            
        adjusted_size_usd = position_usd
        adjusted_size_pct = position_usd / portfolio_value if portfolio_value > 0 else 0.0
        
        if decision.regime_state.regime.value in ["TRENDING_BULL", "TRENDING_BEAR"]:
            trailing_stop_active = True
        approved = True
        
    risk_decision = RiskDecision(
        approved=approved, adjusted_size_usd=adjusted_size_usd, adjusted_size_pct=adjusted_size_pct,
        adjusted_stop=adjusted_stop, trailing_stop_active=trailing_stop_active,
        rejection_reason=rejection_reason, var_estimate=var_estimate,
        kelly_fraction_used=kelly_fraction_used, confidence_size_scalar=confidence_size_scalar,
        log_entry={"session_id": session.session_id, "cycle": session.cycle_count, "approved": approved, "rejection": rejection_reason}
    )
    
    with open("risk_log.jsonl", "a") as f:
        f.write(json.dumps(asdict(risk_decision), default=str) + "\n")
        
    return risk_decision