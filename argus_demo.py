"""Argus — terminal demo (zero-setup, deterministic).

A self-contained walkthrough of the Argus guardian that needs nothing but the
core dependencies (no Streamlit, no API server, no network). It plays the
signature WOW moment in full, then grades all six built-in scenarios and prints
the Capital Protection Score — the same verdicts the web app and API produce.

Run:
    python argus_demo.py            # WOW moment + all six scenarios + CPS
    python argus_demo.py --wow      # just the signature NO-TRADE moment
    python argus_demo.py --scenario C   # one scenario in full detail

Every result is deterministic, so a judge sees the same thing every time.
"""
from __future__ import annotations

import argparse
import sys

# Make the demo robust on Windows' legacy cp1252 console so the emoji/box-drawing
# in the guardian's output never crashes a judge's terminal.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.columns import Columns

from agents.orchestrator import Argus
from core import demo_scenarios
from core.models import Mode

console = Console()

# Decision → (rich colour, icon). Matches the web app's palette.
DECISION_STYLE = {
    "TAKE TRADE": ("green", "✅"),
    "WATCH": ("yellow", "👀"),
    "REJECT": ("red", "⛔"),
    "NO TRADE": ("bright_red", "🛡️"),
}


def _decision_text(decision: str) -> Text:
    color, icon = DECISION_STYLE.get(decision, ("white", "•"))
    return Text(f"{icon} {decision}", style=f"bold {color}")


def banner() -> None:
    title = Text("🛡  A R G U S", style="bold cyan", justify="center")
    sub = Text("AI Trading Guardian", style="cyan", justify="center")
    tag = Text("Most bots help you enter trades. Argus helps you survive them.",
               style="dim italic", justify="center")
    principle = Text("NO TRADE IS ALPHA™", style="bold green", justify="center")
    body = Group(title, sub, Text(""), tag, principle)
    console.print(Panel(body, border_style="bold blue", padding=(1, 6)))


def _meter_bar(value: float, invert: bool = False, width: int = 18) -> Text:
    """A coloured unicode bar for a 0–100 score (invert for risk: high = bad)."""
    v = max(0.0, min(100.0, value))
    judged = (100 - v) if invert else v
    color = "green" if judged >= 75 else "yellow" if judged >= 55 else \
        "orange1" if judged >= 40 else "red"
    filled = int(round(v / 100 * width))
    return Text("█" * filled + "░" * (width - filled), style=color)


def render_full(result: dict, heading: str = "") -> None:
    """Render a single analysis the way Judge Mode reads on the web app."""
    j = result["judge"]
    s = result["scores"]
    v = result["validation"]

    if heading:
        console.rule(f"[bold]{heading}", style="blue")

    head = Text()
    head.append(f"{j['symbol']} @ {j['price']:,}", style="bold white")
    head.append("   ")
    head.append_text(_decision_text(j["final_decision"]))
    head.append(f"   {j['setup_quality']}", style="dim")
    head.append(f"\nDirection {j['direction']}  •  Session {j.get('session','?')} "
                f"(take ≥{j.get('confidence_threshold',0):.0f}%)  •  Data {result['data_mode']}",
                style="dim")
    console.print(head)

    # Four meters.
    meters = Table.grid(padding=(0, 2))
    meters.add_column(justify="right", style="bold")
    meters.add_column()
    meters.add_column(justify="right")
    for label, key, inv in (
        ("Confidence", "confidence", False),
        ("Risk", "risk", True),
        ("Data Quality", "data_quality", False),
        ("Trade Quality", "trade_quality", False),
    ):
        meters.add_row(label, _meter_bar(s[key], invert=inv), f"{s[key]:.0f}/100")
    console.print(meters)

    # NO TRADE IS ALPHA banner when the guardian stands aside profitably.
    if v.get("is_no_trade_alpha"):
        cap = result.get("capital_protected_usd", 0.0)
        note = j.get("capital_protection_note", "")
        # The note may already lead with the trademark — don't print it twice.
        for prefix in ("NO TRADE IS ALPHA™ — ", "NO TRADE IS ALPHA™ —", "NO TRADE IS ALPHA™ "):
            if note.startswith(prefix):
                note = note[len(prefix):]
                break
        alpha = Text()
        alpha.append("NO TRADE IS ALPHA™\n", style="bold green")
        alpha.append(f"{note}\n", style="white")
        alpha.append(f"${cap:,.0f} capital protected", style="bold green")
        console.print(Panel(alpha, border_style="green", padding=(0, 2)))

    console.print(Text("\nTrade thesis", style="bold"))
    console.print(j["trade_thesis"])

    bull = Text("🐂 Bull case\n", style="bold green")
    for b in j["bull_case"]:
        bull.append(f"  • {b}\n")
    bear = Text("🐻 Bear case\n", style="bold red")
    for b in j["bear_case"]:
        bear.append(f"  • {b}\n")
    console.print(Columns([Panel(bull, border_style="green"),
                           Panel(bear, border_style="red")], equal=True, expand=True))

    jt = Table.grid(padding=(0, 3))
    jt.add_column(style="dim", justify="right")
    jt.add_column(style="bold")
    jt.add_row("Entry zone", f"{j['entry_zone'][0]:,} – {j['entry_zone'][1]:,}")
    jt.add_row("Invalidation", f"{j['invalidation_zone']:,}")
    jt.add_row("Reward:Risk", f"{v.get('risk_reward', 0):.2f}")
    jt.add_row("Take-profit", ", ".join(f"{t:,}" for t in j["take_profit"]))
    console.print(jt)

    why = Text()
    why.append("Why it exists:  ", style="bold green")
    why.append(f"{j['why_trade_exists']}\n")
    why.append("Why it could fail:  ", style="bold yellow")
    why.append(f"{j['why_trade_could_fail']}\n")
    why.append("Why it's rejected:  ", style="bold red")
    why.append(f"{j['why_trade_should_be_rejected']}")
    console.print(Panel(why, title="Judge Mode", border_style="dim", padding=(0, 2)))

    if j.get("what_would_improve"):
        imp = Text("🔧 What would improve this setup\n", style="bold")
        for c in j["what_would_improve"]:
            imp.append(f"  • {c}\n")
        console.print(imp)
    console.print()


def render_summary(argus: Argus) -> None:
    """One row per scenario — the whole library at a glance."""
    table = Table(title="Scenario library — every verdict is deterministic",
                  border_style="blue", title_style="bold")
    table.add_column("", style="bold cyan", justify="center")
    table.add_column("Scenario")
    table.add_column("Decision", justify="center")
    table.add_column("Conf", justify="right")
    table.add_column("Risk", justify="right")
    table.add_column("DQ", justify="right")
    table.add_column("Capital saved", justify="right", style="green")
    table.add_column("Lesson", style="dim")

    for key, meta in demo_scenarios.SCENARIOS.items():
        r = argus.demo(key, mode=Mode.PROFESSIONAL)
        j, s = r["judge"], r["scores"]
        saved = r.get("capital_protected_usd", 0.0)
        table.add_row(
            key, meta["name"], _decision_text(j["final_decision"]),
            f"{s['confidence']:.0f}", f"{s['risk']:.0f}", f"{s['data_quality']:.0f}",
            f"${saved:,.0f}" if saved else "—", meta["teaches"],
        )
    console.print(table)


def render_cps(argus: Argus) -> None:
    cps = argus.cps_overview()
    color = "green" if cps["cps"] >= 75 else "yellow" if cps["cps"] >= 55 else "red"
    body = Text()
    body.append("CAPITAL PROTECTION SCORE™  ", style="dim")
    body.append(f"Grade {cps['grade']}\n", style=f"bold {color}")
    body.append(f"{cps['cps']:.0f}/100\n", style=f"bold {color}")
    body.append(f"{cps['headline']}\n\n", style="white")
    body.append(
        f"💰 ${cps['potential_loss_avoided_usd']:,.0f} losses avoided     "
        f"📉 ${cps['risk_exposure_avoided_usd']:,.0f} exposure avoided\n"
        f"🚀 {cps['fomo_blocked']} FOMO chases blocked     "
        f"💧 {cps['liquidity_traps_avoided']} liquidity traps caught",
        style="dim",
    )
    console.print(Panel(body, border_style=color, padding=(1, 3)))


def main() -> None:
    parser = argparse.ArgumentParser(description="Argus terminal demo")
    parser.add_argument("--wow", action="store_true",
                        help="Play only the signature NO-TRADE moment.")
    parser.add_argument("--scenario", type=str, metavar="A-F",
                        help="Show a single scenario (A–F) in full detail.")
    args = parser.parse_args()

    argus = Argus()
    banner()

    if args.scenario:
        r = argus.demo(args.scenario, mode=Mode.PROFESSIONAL)
        meta = r["scenario"]
        render_full(r, heading=f"Scenario {meta['key']} — {meta['name']}")
        return

    # The WOW moment — the centrepiece every run leads with.
    wow = argus.wow_moment(mode=Mode.PROFESSIONAL)
    console.print(Panel(Text(wow["wow_narrative"], style="italic"),
                        title="⭐ The WOW moment — most bots flash BUY",
                        border_style="bold magenta", padding=(1, 3)))
    render_full(wow, heading="Argus' verdict")

    if args.wow:
        return

    console.rule("[bold]The full scenario library", style="blue")
    render_summary(argus)
    console.print()
    render_cps(argus)
    console.print(Align.center(Text(
        "Argus does not win by predicting every trade. "
        "It wins by helping traders avoid the ones that end accounts.",
        style="dim italic")))


if __name__ == "__main__":
    main()
