# Argus — Architecture

> Most bots help you enter trades. Argus helps you survive them.

Argus is a guardian, not a signal mill. Its architecture is built around one
idea: **every analysis must be allowed to end in NO TRADE**, and that outcome
must be as explainable and as valued as a TAKE.

---

## 1. System Diagram

```
┌───────────────────────────────────────────────────────────────────────┐
│                          PRESENTATION LAYER                             │
│                                                                         │
│   Streamlit multipage app (frontend/)          FastAPI (backend/, api/) │
│   Home · Scanner · Analysis · Risk ·           /analyze /scan /demo     │
│   Journal · Analytics · Demo Mode              /wow /journal /health     │
│        │  (in-process Orchestrator, or ARGUS_API_URL → HTTP)            │
└────────┼────────────────────────────────────────────────────────────────┘
         │
┌────────▼────────────────────────────────────────────────────────────────┐
│                          ORCHESTRATION LAYER                              │
│                       agents/orchestrator.py  (Argus)                     │
│   analyze() · scan() · demo() · wow_moment() · learning_report()          │
│   execute() · close_position() · mark_to_market() · portfolio()           │
└────────┬────────────────────────────────────────────────────────────────┘
         │
┌────────▼──────────────────────────┐   ┌──────────────────────────────────┐
│            AGENT LAYER             │   │           CORE ENGINE             │
│  Market Intelligence              │   │  core/scoring.py    (4 meters)    │
│  Risk Guardian                    │──▶│  core/honesty_engine.py (gates)   │
│  Trade Validator                  │   │  core/judge.py      (verdict)     │
│  Reflection                       │   │  core/explain.py    (modes)       │
│  Execution (paper)                │   │  core/models.py     (types)       │
└────────┬──────────────────────────┘   └──────────────────────────────────┘
         │
┌────────▼────────────────────────────────────────────────────────────────┐
│                            SERVICES LAYER                                 │
│   services/market_data.py · services/bitget.py                           │
│   Live Bitget data when credentialed, deterministic simulation otherwise │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Data Flow

```
symbol ──▶ services ──▶ MarketSnapshot ──▶ agents ──▶ Scores
                                                │        │
                                                ▼        ▼
                                      Signal Honesty Engine
                                       (hard gates + grade)
                                                │
                                                ▼
                                          Judge Mode
                                    (thesis, cases, levels,
                                     final decision, explain)
                                                │
                                                ▼
                                   UI meters / API JSON / Journal
```

Everything that moves between layers is a typed dataclass from
[`core/models.py`](../core/models.py): `MarketSnapshot`, `Scores`,
`RiskAssessment`, `JudgeReport`. Scores are 0–100 so they map directly onto the
dashboard meters.

---

## 3. The Five Agents

| Agent | File | Responsibility |
|-------|------|----------------|
| **Market Intelligence** | `agents/market_intelligence.py` | Multi-timeframe trend, volatility, liquidity, structure, momentum |
| **Risk Guardian** | `agents/risk_guardian.py` | Risk scoring, drawdown, position sizing, portfolio health, capital protection |
| **Trade Validator** | `agents/trade_validator.py` | Validates each trade, rejects weak setups, checks R:R, detects thin liquidity & conflicts |
| **Reflection** | `agents/reflection.py` | Trade journaling, post-trade review, mistake detection, learning reports |
| **Execution** | `agents/execution.py` | Paper trading, position tracking, trade lifecycle |

The **Orchestrator** (`agents/orchestrator.py`, class `Argus`) wires them
together and is the single entry point shared by the UI and the API.

---

## 4. The Signal Honesty Engine (Phase 4 — the core innovation)

`core/honesty_engine.py` interrogates every setup against **hard gates**. Any
single hard-gate failure forces the trade down to `NO TRADE`:

| Gate | Default | Why |
|------|---------|-----|
| Data-quality floor | 55 | Can't trade what you can't trust |
| Liquidity floor | 45 | Illiquid = slippage trap |
| Risk ceiling | 78 | Too dangerous regardless of edge |
| FOMO-chase guard | RSI≥82 + high ATR/vol | Refuse to buy the top |
| Signal-conflict | timeframes disagree | No clean direction |
| Reward:risk floor | 1.5 | The math has to pay |

Grades: `REJECT · WATCH · POSSIBLE SETUP · HIGH QUALITY SETUP`.
When Argus rejects, **`NO TRADE IS ALPHA™`** quantifies the exposure protected
and downside avoided.

---

## 5. Judge Mode (Phase 5)

`core/judge.py` produces a full `JudgeReport` for *every* analysis — it argues
against itself before it argues for a trade:

- Trade thesis · Bull case · Bear case
- Entry zone · Invalidation zone · Laddered take-profit
- Why the trade exists · why it could fail · why it should be rejected
- Final decision: `TAKE TRADE · WATCH · REJECT · NO TRADE`

---

## 6. Explainability (Phase 6)

`core/explain.py` renders the same verdict in two registers:

- **Beginner** — plain language, teaches the *why*
- **Professional** — full technical reasoning and numbers

---

## 7. Design Principles

1. **NO TRADE is a first-class output**, not an error path.
2. **Never fabricate confidence** — missing/poor data lowers Data Quality and
   gates the decision rather than being papered over.
3. **Deterministic demos** — simulated data is seeded so judges see the same
   result every run.
4. **Read-only by design** — live execution is intentionally gated off.
5. **Typed everywhere** — dataclasses + Pydantic schemas at the API boundary.
