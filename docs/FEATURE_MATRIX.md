# Argus — Feature Matrix

Every hackathon phase, mapped to where it lives in the codebase and its status.

| Phase | Capability | Status | Where |
|-------|-----------|--------|-------|
| **1** | Repository audit & repair (runs from a fresh clone) | ✅ | `requirements.txt`, `.env.example`, `Dockerfile`, `docker-compose.yml` |
| **1** | Generated env + deploy artifacts | ✅ | `.env.example`, `Procfile`, `render.yaml` |
| **2** | Clean architecture: backend / frontend / core / agents / services / api / dashboard / tests / docs | ✅ | repo root |
| **2** | FastAPI + Pydantic + async API | ✅ | `backend/`, `api/` |
| **2** | Streamlit web app | ✅ | `frontend/` |
| **2** | Pytest suite | ✅ | `tests/`, `conftest.py` |
| **3** | Market Intelligence Agent | ✅ | `agents/market_intelligence.py` |
| **3** | Risk Guardian Agent | ✅ | `agents/risk_guardian.py` |
| **3** | Trade Validator Agent | ✅ | `agents/trade_validator.py` |
| **3** | Reflection Agent | ✅ | `agents/reflection.py` |
| **3** | Execution Agent (paper) | ✅ | `agents/execution.py` |
| **3** | Trade execution wired: TAKE TRADE → open/track/close paper position | ✅ | `agents/orchestrator.py` (`execute`, `close_position`, `portfolio`) |
| **3** | Execution API + UI (open positions, close, realized P&L) | ✅ | `POST /execute`, `GET /positions`, `frontend/pages/3_Risk_Guardian.py` |
| **3** | Orchestrator | ✅ | `agents/orchestrator.py` |
| **4** | Signal Honesty Engine (hard gates) | ✅ | `core/honesty_engine.py` |
| **4** | Decision states: REJECT / WATCH / POSSIBLE / HIGH QUALITY | ✅ | `core/models.py` |
| **4** | `NO TRADE IS ALPHA™` capital-protection accounting | ✅ | `core/honesty_engine.py` |
| **4** | Session-aware confidence thresholds (Asian 65 / London 72 / NY 75) | ✅ | `core/sessions.py` |
| **★** | "What conditions would improve it" guidance | ✅ | `core/honesty_engine.py`, `core/judge.py` |
| **★** | **Capital Protection Score (CPS)** — proprietary metric | ✅ | `core/cps.py`, `GET /cps` |
| **★** | CPS tracks rejected / losses avoided / exposure avoided / FOMO blocked / liquidity traps | ✅ | `core/cps.py` |
| **5** | Judge Mode (thesis, bull/bear, levels, final decision) | ✅ | `core/judge.py` |
| **5** | Judge Mode — Market Structure / Liquidity / Volatility analysis | ✅ | `core/judge.py` |
| **5** | Judge Mode — Capital Protection Impact | ✅ | `core/judge.py`, `core/cps.py` |
| **6** | Beginner & Professional explanation modes | ✅ | `core/explain.py` |
| **7** | Web app — Dashboard, Scanner, Analysis, Risk, Journal, Analytics, Demo | ✅ | `frontend/`, `frontend/pages/` |
| **7** | Meters: Confidence, Risk, Data Quality, **CPS**, Trade Quality | ✅ | `dashboard/components.py` |
| **7** | Rejected / Accepted / **Watchlist** / Capital Saved / Mistakes Avoided | ✅ | `frontend/Home.py`, `frontend/pages/5_Analytics.py` |
| **8** | Demo scenarios (excellent/weak/liquidity/FOMO/missing/exhaustion) | ✅ | `core/demo_scenarios.py` |
| **9** | Signature WOW moment (FOMO NO-TRADE) | ✅ | `core/demo_scenarios.py`, `GET /wow` |
| **10** | Bitget integration seam (spot/futures/risk) | ✅ | `services/bitget.py` |
| **11** | Presentation package (README, diagrams, pitches, demo script/guide, checklist) | ✅ | `docs/`, `README.md` |
| **12** | Judge-review self-assessment & scorecard | ✅ | `docs/JUDGE_REVIEW.md` |

## Differentiators

| Most trading bots | Argus |
|-------------------|-------|
| Maximize number of signals | Maximizes *quality* of decisions |
| Hide uncertainty behind a confident BUY | Surfaces Data Quality and refuses when blind |
| Empty screen = "no opportunity" | NO TRADE = quantified capital protected |
| Black-box score | Full Judge Mode verdict, two explanation modes |
| Chases parabolas | FOMO-chase guard refuses to buy the top |
