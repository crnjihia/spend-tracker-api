FROM python:3.11-slim

# Add OCI standard labels for GHCR package metadata
LABEL org.opencontainers.image.title="Spend Tracker API" \
      org.opencontainers.image.description="Personal finance & M-Pesa transaction tracking REST API for East African spending habits" \
      org.opencontainers.image.url="https://github.com/crnjihia/spend-tracker-api" \
      org.opencontainers.image.source="https://github.com/crnjihia/spend-tracker-api" \
      org.opencontainers.image.licenses="MIT"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=false

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir poetry

COPY pyproject.toml README.md LICENSE /app/

RUN poetry install --no-interaction --no-ansi --only main --no-root

COPY . /app

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser \
    && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
