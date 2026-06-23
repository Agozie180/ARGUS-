#!/bin/sh
# Streamlit launcher for Railway/Render. Kept as a script so the platform start
# command needs NO "$PORT" on its command line (Railway exec's the start command
# without a shell, passing "$PORT" literally — which crashes Streamlit). Here the
# port is expanded inside a real shell, with 8501 as a fallback.
exec python -m streamlit run frontend/Home.py \
  --server.port "${PORT:-8501}" \
  --server.address 0.0.0.0 \
  --server.headless true \
  --server.enableCORS false \
  --server.enableXsrfProtection false
