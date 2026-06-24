# 🛡️ Argus — AI Trading Guardian

> **Most bots help you enter trades. Argus helps you survive them.**

### 🔗 Live demo: **https://web-production-d757d.up.railway.app/**

Argus is an **AI Trading Guardian** built for the Bitget AI × Crypto Hackathon.
It runs on **live public Bitget market data** and is **Powered by Qwen**.

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

### Live Bitget data by default — no keys required

- **Argus uses live, public Bitget market data by default.** Every analysis,
  scan and the home dashboard read real prices and candles from Bitget's public
  REST API — **no API key needed**.
- **Bitget API keys are only needed for private features** — account balance,
  positions and live order execution. Market intelligence works fully without
  them.
- **Honest fallback** — if the live feed ever fails, Argus drops to a
  deterministic snapshot that is clearly labelled **`🟡 DEMO DATA` / SIMULATED**.
  It never presents simulated data as live.
- **Powered by Qwen** — reasoning/reflection use Qwen by default (OpenAI optional
  fallback); with no provider it runs on its deterministic rule-based engine.

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
Run it yourself three ways: the **Demo Mode** page → *FOMO setup*, `GET /wow`, or
the one-liner `python argus_demo.py --wow`.

---

## How It Works

Argus runs a five-agent guardian pipeline. Every analysis flows through the
**Signal Honesty Engine** (Phase 4) and produces a full **Judge Mode** verdict
(Phase 5).

```
            ┌──────────────────────────────────────────────┐
            │              MARKET SNAPSHOT                   │
            │  (LIVE Bitget data → labelled SIM on failure)  │
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

# 2. (Optional) copy env. Argus reads LIVE public Bitget market data out of the
#    box — NO keys needed. If Bitget is unreachable it falls back to a clearly
#    labelled simulated snapshot, so the demo always works.
cp .env.example .env

# 3a. Run the web app (primary hackathon UI)
streamlit run frontend/Home.py            # → http://localhost:8501

# 3b. Or run the API
uvicorn backend.main:app --reload         # → http://localhost:8000/docs

# 3c. Or the zero-setup terminal demo (no server, no browser)
python argus_demo.py                      # WOW moment + all 6 scenarios + CPS
python argus_demo.py --wow                # just the signature NO-TRADE moment
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
argus_demo.py  Zero-setup rich terminal demo (WOW moment + all scenarios + CPS)
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

Argus ships with a `Dockerfile` (backend), `Dockerfile.frontend` (dashboard),
`docker-compose.yml`, `Procfile`, `render.yaml`, and `railway.json`. See
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for full walkthroughs.

- **Render** runs the **FastAPI backend** (`render.yaml` → `uvicorn backend.main:app`).
- **Railway** runs the **Streamlit dashboard** — `railway.json` builds
  `Dockerfile.frontend` and runs
  `python -m streamlit run frontend/Home.py --server.port $PORT --server.address 0.0.0.0`.

**Builds are lightweight by default.** The heavy ML extras (chromadb,
sentence-transformers → torch, litellm) are *not* in `requirements.txt` — they
slow cloud builds and can OOM free-tier containers. The dashboard, API, and
Bitget integration don't need them; install `requirements-ml.txt` only for the
optional vector-memory / LLM features.

### Blank dashboard after deploy?

A Streamlit page that loads but renders blank is almost always the websocket
being blocked by the platform's reverse proxy. Argus fixes this in two places:
`.streamlit/config.toml` and explicit `--server.enableCORS false
--server.enableXsrfProtection false` flags in the start commands. If you still
see a blank page, confirm the service is running the **Streamlit** command
(not the FastAPI backend) and that it redeployed from the latest commit.

---

## Bitget Integration

**Live Bitget market data powers the entire guardian — not just one page.**
Every analysis, the Market Scanner, the home dashboard watchlist and the Live
Bitget Example all read **real, live** prices and candles from Bitget's public
REST API and run them through the exact same decision engine. No API key is
required for market data, and execution stays disabled by default.

### Endpoints used (public, read-only, no credentials)

| Endpoint | Purpose | Used by |
|---|---|---|
| `GET /api/v2/spot/market/tickers?symbol=…` | Last price, 24h change, bid/ask, USDT turnover | per-symbol analysis |
| `GET /api/v2/spot/market/tickers` (no symbol) | Whole-market snapshot for scanning & discovery | Market Scanner, `discover_symbols` |
| `GET /api/v2/spot/market/candles?symbol=…&granularity=…` | OHLC history for indicator math (EMA/RSI/ATR/ADX) | every snapshot |

Base URL: `https://api.bitget.com` (`services/live_bitget.py`).

### Market-data flow

```
symbol ─▶ services/bitget.py (BitgetService)
            ├─ live: services/live_bitget.get_live_market()  ─▶ Bitget public REST
            │        └─ real ticker + candles ─▶ snapshot_from_candles()
            │                                     (source=BITGET_LIVE, fetched_at, market_type)
            └─ fallback: services/market_data.build_snapshot()  (source=SIMULATED)
                                   │
                                   ▼
        MarketSnapshot ─▶ agents ─▶ scores ─▶ Signal Honesty Engine ─▶ Judge Mode ─▶ UI / API
```

Every `MarketSnapshot` carries its own provenance (`source`, `market_type`,
`fetched_at`), so the UI proves the source on **each** result instead of
asserting it globally.

### How Argus uses Bitget data

- **Real prices everywhere** — `BitgetService.get_snapshot()` fetches live data
  by default (TTL-cached ~45s, parallelised across a scan to stay fast and
  within rate limits). Tokens like SOLUSDT now show the true live Bitget price.
- **Bitget-wide universe** — `discover_symbols()` ranks the live USDT market by
  24h turnover, so the scanner reflects what's actually trading on Bitget (20+
  symbols by default), not a hardcoded three-token list.
- **Provenance on every analysis** — Source · Last Updated · Market Type ·
  Status (`🟢 Live Bitget Market Data`) rendered on each verdict.
- **Status endpoint** — `GET /market/status` reports live connectivity, the
  probe price, and the endpoint in use.

### What happens if Bitget is unavailable

Argus **never pretends simulated data is live.** On any network/parse failure it
falls back to a deterministic synthetic snapshot stamped `source=SIMULATED`, and
the UI shows an amber **`🟡 DEMO DATA`** badge. Set `ARGUS_LIVE_DATA=false` to
force offline mode (the test suite does this for determinism).

- **Read-only & key-free for live data** — only public market endpoints are
  called, so no API keys are ever sent, logged, or exposed in the UI or browser.
- **Execution stays off** — `PAPER_TRADING=True` by default; live order
  execution is intentionally gated off. Argus is a guardian, not an auto-trader.

---

## Execution — paper by default, execution-ready

Argus is **execution-capable without requiring real funds**, and ships a visible
**`📝 PAPER MODE` / `🔴 LIVE MODE`** indicator on the Home, Trade Analysis, Risk
Guardian and Execution Console pages. A unified execution abstraction
(`agents/execution.py` + `services/bitget.py`) can **simulate** orders,
**record** every order to an auditable log, and **place real Bitget orders** —
but only after clearing four independent safety gates (`services/execution_mode.py`):

1. `PAPER_TRADING=false`
2. `ARGUS_ALLOW_LIVE_TRADING=true` (deployment master switch — unset on the demo)
3. Bitget trading credentials present
4. Live mode *armed* at runtime by typing `ENABLE LIVE TRADING` in the Execution
   Console (each order also passes a per-order `confirm`)

If any gate is unmet the app is **hard-locked to PAPER** — orders are simulated
and recorded, never sent. `GET /execution/status` exposes the mode, gates and
order log. `ARGUS_LIVE_ORDER_DRYRUN=true` rehearses the full signed-order path
without transmitting. **No real trade can happen by accident or on the judging
deployment.**

---

## AI Reasoning — Qwen-first

Argus's optional LLM narration and reflection are **Qwen-powered by default**
(Alibaba's open model family via DashScope), aligning with the Bitget AI stack.
OpenAI is supported only as an optional fallback when `OPENAI_API_KEY` is set.
With no provider configured, Argus runs entirely on its **deterministic
rule-based engine** — it never fabricates reasoning or confidence it didn't run.

- Provider routing lives in `core/llm.py` (Qwen → OpenAI → rules).
- Configure via `ARGUS_LLM_PROVIDER` (`qwen` default), `ARGUS_QWEN_MODEL`
  (`dashscope/qwen-plus`), and `DASHSCOPE_API_KEY`. See `.env.example`.

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
