"""Argus backend — FastAPI application entrypoint.

Run locally:
    uvicorn backend.main:app --reload --port 8000

Interactive docs at http://localhost:8000/docs
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router, VERSION

app = FastAPI(
    title="Argus — AI Trading Guardian",
    description=(
        "Most bots help you enter trades. Argus helps you survive them. "
        "A guardian that scores confidence, risk and data quality, and is "
        "proud to reject bad trades. NO TRADE IS ALPHA™."
    ),
    version=VERSION,
)

# Open CORS so the Streamlit frontend (any port) can call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/", tags=["meta"])
def root():
    return {
        "service": "argus",
        "tagline": "Most bots help you enter trades. Argus helps you survive them.",
        "docs": "/docs",
        "endpoints": ["/health", "/analyze/{symbol}", "/scan", "/scenarios", "/demo/{scenario}", "/wow", "/journal", "/cps", "/execute/{symbol}", "/positions", "/positions/{trade_id}/close"],
    }
