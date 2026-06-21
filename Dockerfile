# Argus — AI Trading Guardian
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: serve the FastAPI backend. The frontend image overrides the command
# (see docker-compose.yml).
EXPOSE 8000 8501

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
