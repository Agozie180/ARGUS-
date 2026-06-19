import logging
from datetime import datetime, timezone, timedelta
from config import SessionState, Direction, settings

logger = logging.getLogger(__name__)

class DisciplineEngine:
    """
    Enforces the Iron Laws of trading discipline.
    The agent must swear an oath to these rules before every trade.
    """
    
    # Law 1: Cooldown after any trade (prevents overtrading)
    TRADE_COOLDOWN_MINUTES = 15
    
    # Law 2: Cooldown after a loss (prevents revenge trading)
    LOSS_COOLDOWN_MINUTES = 30
    
    # Law 3: Cooldown after consecutive losses (forces reset)
    MAX_CONSEC_LOSSES_BEFORE_EXILE = 3
    EXILE_MINUTES = 120
    
    # Law 4: Max trades per day (prevents fatigue drift)
    MAX_DAILY_TRADES = 10

    def __init__(self, session: SessionState):
        self.session = session

    def _get_last_trade_time(self) -> datetime | None:
        """Reads paper_trades.jsonl to find the last trade timestamp."""
        try:
            with open("paper_trades.jsonl", "r") as f:
                lines = f.readlines()
                if not lines: return None
                last_trade = json.loads(lines[-1])
                return datetime.fromisoformat(last_trade["timestamp"])
        except:
            return None

    def _get_daily_trade_count(self) -> int:
        """Counts trades made in the current UTC day."""
        try:
            today = datetime.now(timezone.utc).date()
            count = 0
            with open("paper_trades.jsonl", "r") as f:
                for line in f:
                    try:
                        trade = json.loads(line)
                        trade_date = datetime.fromisoformat(trade["timestamp"]).date()
                        if trade_date == today:
                            count += 1
                    except:
                        continue
            return count
        except:
            return 0

    def enforce_oath(self) -> tuple[bool, str]:
        """
        Returns (True, "") if the agent is allowed to trade, 
        or (False, "Reason") if blocked by the Iron Laws.
        """
        now = datetime.now(timezone.utc)
        
        # 1. Global Session Halt (Circuit Breaker)
        if self.session.halted:
            return False, f"[HALT] Session is halted: {self.session.halt_reason}"
            
        # 2. Daily Trade Limit
        if self._get_daily_trade_count() >= self.MAX_DAILY_TRADES:
            return False, f"[FATIGUE] Hit max daily trades ({self.MAX_DAILY_TRADES}). Rest until tomorrow."
            
        # 3. Exile after consecutive losses
        if self.session.consecutive_losses >= self.MAX_CONSEC_LOSSES_BEFORE_EXILE:
            # This should ideally trigger a halt in session state, but double-check here
            if not self.session.halted:
                self.session.halted = True
                self.session.halt_reason = f"Exiled: {self.MAX_CONSEC_LOSSES_BEFORE_EXILE} consecutive losses"
            return False, f"[EXILE] {self.MAX_CONSEC_LOSSES_BEFORE_EXILE} consecutive losses. Exiled for {self.EXILE_MINUTES}m."

        last_trade_time = self._get_last_trade_time()
        if last_trade_time:
            time_since_last = now - last_trade_time
            
            # 4. Revenge Trading Cooldown
            if self.session.consecutive_losses > 0:
                required_cooldown = timedelta(minutes=self.LOSS_COOLDOWN_MINUTES)
                if time_since_last < required_cooldown:
                    remaining = required_cooldown - time_since_last
                    return False, f"[REVENGE_GUARD] Cooldown after loss. {remaining.seconds // 60}m {remaining.seconds % 60}s remaining."
            
            # 5. General Overtrading Cooldown
            required_cooldown = timedelta(minutes=self.TRADE_COOLDOWN_MINUTES)
            if time_since_last < required_cooldown:
                remaining = required_cooldown - time_since_last
                return False, f"[OVERTRADE_GUARD] Cooldown active. {remaining.seconds // 60}m {remaining.seconds % 60}s remaining."

        return True, "Oath cleared."

# Note: Ensure 'import json' is at the top of the file in actual implementation.