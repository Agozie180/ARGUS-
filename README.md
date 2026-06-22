# 🛡️ Argus — AI Trading Guardian

> **Most bots help you enter trades. Argus helps you survive them.**

Argus is an **AI Trading Guardian** built for the Bitget AI × Crypto Hackathon.

Most trading agents compete to generate *more* signals. Argus does the opposite:
it **protects capital, rejects bad trades, explains risk, and enforces
discipline**. It never fabricates confidence, never invents a signal, and is
*proud* to say **NO TRADE**.

### `NO TRADE IS ALPHA™`

When Argus stands aside, it doesn't show an empty screen — it quantifies the
capital it just protected and the downside it avoided. Avoiding a bad trade is a
*positive* outcome, not an absence of one.

### Capital Protection Score (CPS) — the signature metric

Most metrics measure value created by *taking* trades. The **CPS** (0–100,
graded A+–D) measures value created by *avoiding* bad ones — rolling rejected
trades, losses avoided, risk exposure avoided, FOMO chases blocked, and
low-liquidity traps caught into one headline number, displayed prominently
across the dashboard.

---

## Why Argus

Retail crypto trading is an emotional, reactive game: FOMO entries, panic exits,
and no systematic way to judge whether a setup is actually worth the risk. Argus
replaces that anxiety with a transparent, explainable decision pipeline that
grades every opportunity and refuses the ones that don't clear its gates.

Argus is **not** an oracle that predicts the future. It is a guardian that helps
traders make better decisions, understand risk, and preserve capital. It runs
**paper / read-only by design**.

---

## The Signature Demo (the WOW moment)

Pull up a textbook FOMO chart — `SOLUSDT`, +40% on the week, every short-term
signal green, momentum screaming. **Most bots flash BUY.**

Argus returns **NO TRADE**, and explains exactly why:

- RSI **86** — exhausted, this is late-cycle chasing
- ATR **4.6%** — a *normal* wiggle stops you out
- Reward:risk is upside-down this far into the move

Then it shows the capital that decision just protected. **Standing aside is the trade.**
Run it yourself: the **Demo Mode** page → *FOMO setup*, or `GET /wow`.

---

## How It Works

Argus runs a five-agent guardian pipeline. Every analysis flows through the
**Signal Honesty Engine** (Phase 4) and produces a full **Judge Mode** verdict
(Phase 5).

```
            ┌──────────────────────────────────────────────┐
            │              MARKET SNAPSHOT                   │
            │   (Bitget data, or deterministic simulation)   │
            └───────────────────────┬────────────────────────┘
                                    │
     ┌──────────────────────────────▼──────────────────────────────┐
     │                      AGENT PIPELINE                          │
     │  ┌────────────────┐ ┌──────────────┐ ┌───────────────────┐  │
     │  │ Market         │ │ Risk         │ │ Trade Validator   │  │
     │  │ Intelligence   │ │ Guardian     │ │ (rejects weak     │  │
     │  │ (trend/vol/    │ │ (sizing,     │ │  setups)          │  │
     │  │  liquidity)    │ │  drawdown)   │ │                   │  │
     │  └────────────────┘ └──────────────┘ └───────────────────┘  │
     │  ┌────────────────┐ ┌────────────────────────────────────┐  │
     │  │ Execution      │ │ Reflection (journaling, lessons)   │  │
     │  │ (paper)        │ │                                    │  │
     │  └────────────────┘ └────────────────────────────────────┘  │
     └──────────────────────────────┬──────────────────────────────┘
                                    │
     ┌──────────────────────────────▼──────────────────────────────┐
     │                 SIGNAL HONESTY ENGINE                        │
     │  Hard gates: data-quality floor · liquidity floor · risk     │
     │  ceiling · FOMO-chase guard · signal-conflict · R:R floor    │
     │                                                              │
     │  Grade →  REJECT · WATCH · POSSIBLE SETUP · HIGH QUALITY      │
     └──────────────────────────────┬──────────────────────────────┘
                                    │
     ┌──────────────────────────────▼──────────────────────────────┐
     │                      JUDGE MODE                              │
     │  Thesis · Bull case · Bear case · Entry/Invalidation/TP ·    │
     │  Why it exists · Why it could fail · Why it's rejected       │
     │                                                              │
     │  FINAL DECISION →   TAKE TRADE · WATCH · REJECT · NO TRADE    │
     └──────────────────────────────────────────────────────────────┘
```

Five meters drive the dashboard, all on a 0–100 scale:
**Confidence · Risk · Data Quality · Trade Quality · Capital Protection Score.**

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full system design.

---

## Quickstart

Fresh clone → install → run.

```bash
# 1. Install (Python 3.12 recommended)
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. (Optional) add Bitget keys — without them Argus uses deterministic
#    simulated data, so the demo always works.
cp .env.example .env

# 3a. Run the web app (primary hackathon UI)
streamlit run frontend/Home.py            # → http://localhost:8501

# 3b. Or run the API
uvicorn backend.main:app --reload         # → http://localhost:8000/docs
```

### With Docker

```bash
docker compose up --build
# API      → http://localhost:8000/docs
# Frontend → http://localhost:8501
```

---

## Web App

The multipage Streamlit app (`frontend/`) is the primary hackathon UI, styled
like a Bloomberg terminal crossed with an AI copilot:

| Page | What it does |
|------|--------------|
| **Home** | Live capital-protection summary + one-click analysis |
| **Market Scanner** | Grade a watchlist at a glance |
| **Trade Analysis** | Full Judge Mode verdict for any symbol |
| **Risk Guardian** | Position sizing, drawdown, portfolio health |
| **Journal** | Trade journaling + continuous-learning lessons |
| **Analytics** | Rejections, acceptances, capital saved, mistakes avoided |
| **Demo Mode** | Six built-in scenarios + the signature WOW moment |

Both **Beginner** (plain language) and **Professional** (technical reasoning)
explanation modes are available everywhere.

---

## API

`uvicorn backend.main:app` exposes (full schema at `/docs`):

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness check |
| `GET /analyze/{symbol}` | Full Judge Mode analysis |
| `GET /scan` | Grade a list of symbols |
| `GET /scenarios` | List built-in demo scenarios |
| `GET /demo/{scenario}` | Run scenario A–F |
| `GET /wow` | The signature NO-TRADE moment |
| `GET /journal` | Continuous-learning report (incl. live CPS) |
| `GET /cps` | Capital Protection Score across representative setups |
| `POST /execute/{symbol}` | Open a **paper** position — only if Argus approves a TAKE TRADE |
| `GET /positions` | Open + closed paper positions with realized P&L |
| `POST /positions/{trade_id}/close` | Close a paper position and run the post-trade review |

---

## Demo Scenarios

Every scenario is deterministic, so judges get the same result every time.

| | Scenario | Argus says | Lesson |
|-|----------|-----------|--------|
| **A** | Excellent trade | TAKE TRADE | What a genuinely high-quality setup looks like |
| **B** | Weak trade | WATCH | Mediocre signals are not opportunities |
| **C** | Low-liquidity trap | REJECT | A pretty chart on a thin book is a slippage trap |
| **D** | FOMO setup | **NO TRADE** | Chasing an overbought parabola is how accounts die |
| **E** | Missing data | NO TRADE | If you can't trust the inputs, you can't trust the trade |
| **F** | Trend exhaustion | WATCH | Strong trends end — momentum divergence is the tell |

---

## Project Layout

```
backend/    FastAPI app entrypoint
api/        Routes + Pydantic schemas
core/       Domain models, scoring, Signal Honesty Engine, Judge Mode, demos
agents/     Market Intelligence · Risk Guardian · Trade Validator · Reflection · Execution · Orchestrator
services/   Bitget + market-data adapters (simulated fallback)
frontend/   Streamlit multipage web app (primary UI)
dashboard/  Shared UI theme + components
tests/      Pytest suite
docs/       Architecture, deployment, demo script, pitches, feature matrix
```

---

## Testing

```bash
pytest -q
```

---

## Deployment

Argus ships with a `Dockerfile`, `docker-compose.yml`, `Procfile`, and
`render.yaml`. See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for Railway,
Render, and Docker walkthroughs.

---

## Bitget Integration

Argus is built for Bitget compatibility — spot and futures market data, risk
monitoring, and agent-based workflows — with `services/bitget.py` as the
adapter seam. Without credentials it runs on deterministic simulated data so the
guardian logic is always demonstrable. Live order execution is intentionally
gated off; Argus is a guardian, not an auto-trader.

---

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system & component design
- [`docs/FEATURE_MATRIX.md`](docs/FEATURE_MATRIX.md) — features mapped to hackathon phases
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — Railway / Render / Docker
- [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) — judge walkthrough
- [`docs/PITCH.md`](docs/PITCH.md) — 3-minute & 5-minute pitches
- [`docs/TECHNICAL.md`](docs/TECHNICAL.md) — engine internals, scoring & CPS math
- [`docs/DEMO_GUIDE.md`](docs/DEMO_GUIDE.md) — self-guided walkthrough
- [`docs/JUDGE_REVIEW.md`](docs/JUDGE_REVIEW.md) — hackathon judge self-review & scorecard
- [`docs/SUBMISSION_CHECKLIST.md`](docs/SUBMISSION_CHECKLIST.md) — pre-submission checklist

---

*Argus is a guardian, not an oracle. Paper / read-only by design. It helps
traders avoid bad trades, understand risk, and preserve capital.*
