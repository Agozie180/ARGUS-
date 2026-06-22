"""Argus — The AI Trading Guardian (live paper-trading loop).

A continuous guardian loop: perceive the market with the agent ensemble,
classify the regime, deliberate a decision, and — only when the setup clears
Argus' gates — open a paper position. Argus is proud to stand aside: when no
setup justifies action it logs NO TRADE, because NO TRADE IS ALPHA™.

Run:
    python main.py --symbols BTCUSDT,ETHUSDT --cycles 3
"""
import asyncio
import argparse
import signal
import sys
import json
import logging
from datetime import datetime, timezone
from typing import List
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.align import Align
from rich.text import Text

from config import settings, SessionState, Direction, ConfidenceScore
from memory import Memory
from bitget_client import BitgetClient
from agents.technical_agent import perceive as tech_perceive
from agents.sentiment_agent import perceive as sent_perceive
from agents.onchain_macro_agent import perceive as macro_perceive
from regime_classifier import classify_regime
from decision_engine import decide
from risk_guardian import assess_risk
from executor import execute_paper, check_and_close_trades

logger = logging.getLogger(__name__)
console = Console()

class TradingAgent:
    def __init__(self, symbols: List[str], interval: int, hil: bool, cycles: int, threshold: float):
        self.symbols = symbols
        self.interval = interval
        self.hil = hil
        self.max_cycles = cycles
        self.threshold = threshold
        self.session = SessionState()
        self.bitget = BitgetClient()
        self.memory = Memory()
        self.shutdown_requested = False
        
        settings.SYMBOLS = symbols
        settings.CYCLE_INTERVAL_SECONDS = interval
        settings.HUMAN_IN_LOOP = hil
        settings.CONFIDENCE_THRESHOLD_DEFAULT = threshold

    def print_banner(self):
        banner_text = Text("🛡  ARGUS", style="bold cyan", justify="center")
        title_text = Text("The AI Trading Guardian", style="cyan", justify="center")
        sub_text = Text("Most bots help you enter trades. Argus helps you survive them.",
                        style="dim italic", justify="center")
        principle_text = Text("NO TRADE IS ALPHA™", style="bold green", justify="center")
        session_text = Text(
            f"Session: {self.session.session_id[:8]} | Mode: PAPER / READ-ONLY | "
            f"Threshold: {self.threshold:.2f}", style="yellow", justify="center")

        panel = Panel.fit(
            Group(banner_text, title_text, Text(""), sub_text, principle_text,
                  Text(""), session_text),
            border_style="bold blue",
            padding=(1, 4)
        )
        console.print(panel)
        sys.stdout.flush()

    async def run_cycle(self):
        self.session.cycle_count += 1
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        console.print(f"\n[bold blue]═══ CYCLE {self.session.cycle_count} | {ts} UTC | PnL: {self.session.daily_pnl_pct:.2%} | Losses: {self.session.consecutive_losses} ═══[/]")
        
        if self.session.should_halt():
            console.print(Panel(f"[bold red]🛑 SESSION HALTED[/]\nReason: {self.session.halt_reason}", title="CIRCUIT BREAKER TRIGGERED", border_style="red"))
            self.shutdown_requested = True
            return

        for symbol in self.symbols:
            with console.status(f"[cyan]Argus is perceiving the market for {symbol}...[/]"):
                tech_task = asyncio.create_task(tech_perceive(symbol, self.session))
                sent_task = asyncio.create_task(sent_perceive(symbol, self.session))
                macro_task = asyncio.create_task(macro_perceive(symbol, self.session))
                
                tech_snap, tech_conf = await tech_task
                sent_snap, sent_conf = await sent_task
                macro_snap, macro_conf = await macro_task
                
            regime_state = classify_regime(tech_snap, sent_snap, macro_snap, self.session)
            self.session.last_regime = regime_state.regime
            console.print(f"  🌐 [magenta]Regime:[/] {regime_state.regime.value} (Conf: {regime_state.regime_confidence:.2f})")
            
            with console.status("[cyan]Agent is deliberating (ReAct Loop)...[/]"):
                decision = await decide(symbol, tech_snap, tech_conf, sent_snap, sent_conf, macro_snap, macro_conf, regime_state, self.session)
                
            # Print Reasoning Trace beautifully
            trace_table = Table.grid(padding=(0, 1))
            trace_table.add_column(style="dim", width=2)
            trace_table.add_column(style="white")
            for i, step in enumerate(decision.reasoning_trace, 1):
                trace_table.add_row(f"{i}.", step)
            console.print(Panel(trace_table, title=f"🧠 Reasoning Trace — {symbol}", border_style="dim blue", width=80))
                
            if decision.action != Direction.NO_TRADE:
                proceed = True
                if self.hil:
                    console.print(f"  [yellow]Proposed:[/] {decision.action.value} {symbol} @ {decision.entry_price:.2f}")
                    user_input = await asyncio.to_thread(input, "  Execute? [y/n/q]: ")
                    if user_input.lower() == 'q': self.shutdown_requested = True; return
                    if user_input.lower() != 'y': proceed = False

                if proceed:
                    risk_decision = await assess_risk(decision, self.session)
                    if risk_decision.approved:
                        trade_rec = await execute_paper(decision, risk_decision, self.session)
                        if trade_rec:
                            console.print(f"  [bold green]✅ TAKE TRADE[/] {decision.action.value} {symbol} @ {trade_rec.fill_price:.2f} | Size: ${risk_decision.adjusted_size_usd:.2f} | Paper fill ✓")
                    else:
                        # Argus stands aside loudly and honestly — NO TRADE IS ALPHA.
                        console.print(Panel(f"[bold red]🛡️ TRADE REJECTED[/]\nReason: {risk_decision.rejection_reason}", title="ARGUS — RISK GUARDIAN", border_style="red", width=60))
            else:
                gate_reason = decision.confidence_score.gate_reason
                console.print(f"  [yellow]⏸️ NO TRADE[/] | Gate: {gate_reason}")

        await check_and_close_trades(self.session)
        self.session.last_cycle_at = datetime.now(timezone.utc)

    async def shutdown(self):
        console.print("\n[bold red]=== SHUTDOWN INITIATED ===[/]")
        self.session.halted = True
        await check_and_close_trades(self.session)
        
        table = Table(title="Final Session Summary", border_style="bold blue")
        table.add_column("Metric", style="cyan", justify="right")
        table.add_column("Value", style="white")
        table.add_row("Total Cycles", str(self.session.cycle_count))
        table.add_row("Final PnL", f"{self.session.daily_pnl_pct:.2%}")
        table.add_row("Halts", "1" if self.session.halted else "0")
        console.print(table)
        
        with open("sessions.jsonl", "a") as f:
            f.write(json.dumps(self.session.to_dict(), default=str) + "\n")

async def main_async():
    parser = argparse.ArgumentParser(description="Argus — The AI Trading Guardian")
    parser.add_argument("--paper", action="store_true", default=True)
    parser.add_argument("--symbols", type=str, default="BTCUSDT,ETHUSDT")
    parser.add_argument("--interval", type=int, default=900)
    parser.add_argument("--cycles", type=int, default=0)
    parser.add_argument("--hil", action="store_true")
    parser.add_argument("--confidence", type=float, default=0.65)
    args = parser.parse_args()

    logging.basicConfig(level=settings.LOG_LEVEL, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    agent = TradingAgent(args.symbols.split(','), args.interval, args.hil, args.cycles, args.confidence)
    agent.print_banner()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try: loop.add_signal_handler(sig, lambda: setattr(agent, 'shutdown_requested', True))
        except NotImplementedError: pass

    try:
        while not agent.shutdown_requested:
            await agent.run_cycle()
            if agent.max_cycles > 0 and agent.session.cycle_count >= agent.max_cycles: break
            for _ in range(agent.interval):
                if agent.shutdown_requested: break
                await asyncio.sleep(1)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
    finally:
        await agent.shutdown()

if __name__ == "__main__":
    asyncio.run(main_async())