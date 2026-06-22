# Argus — Bitget Hackathon Submission Checklist

A pre-flight list to make sure the submission is complete, runnable, and
judge-ready.

## Repository

- [x] Fresh clone installs cleanly (`pip install -r requirements.txt`)
- [x] Runs with **zero credentials** (deterministic simulated data)
- [x] `.env.example` documents every variable; no secrets committed
- [x] `.gitignore` excludes `.env`, caches, `chroma_db/`, `*.jsonl`
- [x] Tests pass (`pytest -q`)
- [x] Clean architecture: `backend/ api/ core/ agents/ services/ frontend/ dashboard/ tests/ docs/`

## Core Product

- [x] Five agents: Market Intelligence, Risk Guardian, Trade Validator, Reflection, Execution
- [x] **Trade execution wired**: a TAKE TRADE opens a tracked paper position; close records realized P&L + post-trade review; guardian refuses to execute anything weaker
- [x] **Signal Honesty System** with hard gates (data, liquidity, risk, R:R, FOMO, conflict)
- [x] Four decision states: TAKE TRADE / WATCH / REJECT / NO TRADE
- [x] `NO TRADE IS ALPHA™` capital-protection accounting
- [x] **Capital Protection Score (CPS)** — proprietary metric, shown prominently
- [x] **Judge Mode** — thesis, bull/bear, market structure, liquidity, volatility,
      confidence/risk/data-quality scores, capital-protection impact, entry/invalidation/TP,
      why exists / could fail / should be rejected, final decision
- [x] Explainability: Beginner + Pro modes

## Web Application

- [x] FastAPI backend (`/docs` OpenAPI), Streamlit frontend
- [x] Pages: Dashboard, Market Scanner, Trade Analysis, Risk Guardian, Journal, Analytics, Demo Mode
- [x] Widgets: Confidence, Risk, Data Quality, **CPS**, Trade Quality meters; Rejected/Accepted trades; **Watchlist**; Capital Saved; Mistakes Avoided

## Demo

- [x] Six built-in scenarios (excellent / weak / liquidity trap / FOMO / missing data / trend exhaustion)
- [x] Signature **WOW moment** (FOMO → NO TRADE with quantified capital protected)
- [x] `GET /wow` and Demo Mode page both reproduce it deterministically

## Bitget Integration

- [x] `services/bitget.py` adapter — spot/futures parity, risk-monitoring read-only
- [x] Live data seam (`_live_snapshot`) ready to wire; never blocks offline demo

## Deployment

- [x] `Dockerfile` + `docker-compose.yml` (API + frontend)
- [x] `Procfile` (Railway) + `render.yaml` (Render blueprint)

## Presentation Package

- [x] `README.md`
- [x] `docs/ARCHITECTURE.md` (system + component diagrams)
- [x] `docs/FEATURE_MATRIX.md`
- [x] `docs/DEPLOYMENT.md`
- [x] `docs/DEMO_SCRIPT.md` (judge script)
- [x] `docs/DEMO_GUIDE.md` (self-guided walkthrough)
- [x] `docs/PITCH.md` (3-minute + 5-minute)
- [x] `docs/TECHNICAL.md`
- [x] `docs/JUDGE_REVIEW.md` (self-assessment scorecard)
- [x] `docs/SUBMISSION_CHECKLIST.md` (this file)

## Final Pre-Submission

- [ ] Record a 2–3 minute demo video built on `docs/DEMO_SCRIPT.md`
- [ ] Deploy a public instance (Railway/Render) and paste the URL into the submission
- [ ] Confirm the repo link is public and the README renders on the platform
- [ ] (Optional) Wire one live Bitget endpoint for a live-data flex
