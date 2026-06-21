# Argus — Deployment Guide

Argus runs anywhere Python 3.12 runs. Without Bitget credentials it falls back
to deterministic simulated data, so every deployment is demo-ready out of the box.

---

## Local (fastest)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Web app (primary UI)
streamlit run frontend/Home.py            # http://localhost:8501

# API (separate terminal)
uvicorn backend.main:app --reload         # http://localhost:8000/docs
```

---

## Docker / Docker Compose

Brings up the API and frontend together:

```bash
docker compose up --build
# API      → http://localhost:8000/docs
# Frontend → http://localhost:8501  (talks to the API via ARGUS_API_URL)
```

To run just the API image:

```bash
docker build -t argus .
docker run -p 8000:8000 argus
```

---

## Railway

Argus ships a `Procfile`, so Railway auto-detects the web process.

1. **New Project → Deploy from GitHub repo.**
2. Railway installs `requirements.txt` and runs the `Procfile`:
   `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`.
3. (Optional) Add a second service for the frontend with the start command:
   `streamlit run frontend/Home.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`
   and set `ARGUS_API_URL` to the API service URL.
4. Variables: leave `PAPER_TRADING=true`. Bitget keys are optional.

---

## Render

A `render.yaml` blueprint defines both services.

1. **New → Blueprint**, point at the repo.
2. Render reads `render.yaml` and provisions **argus-api** and **argus-frontend**.
3. The frontend's `ARGUS_API_URL` is wired to the API service automatically.
4. Set Bitget secrets in the dashboard if you want live data (`sync: false` keys).

---

## Environment Variables

See [`.env.example`](../.env.example) for the full list. The essentials:

| Variable | Default | Notes |
|----------|---------|-------|
| `PAPER_TRADING` | `true` | **Keep true.** `false` enables live execution. |
| `BITGET_API_KEY` / `BITGET_SECRET_KEY` / `BITGET_PASSPHRASE` | empty | Optional. Empty → simulated data. |
| `ARGUS_API_URL` | unset | Set on the frontend to route through the API instead of in-process. |

---

## Health & Verification

```bash
curl localhost:8000/health        # liveness
curl localhost:8000/wow           # the signature NO-TRADE moment
pytest -q                         # full test suite
```
