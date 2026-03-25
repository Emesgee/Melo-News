# ── Stage 1: Build dependencies ────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Build deps for native wheels (spacy/blis, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential gcc python3-dev libffi-dev && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

COPY requirements.txt .
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt \
    && python -m spacy download en_core_web_sm

# ── Stage 2: Production image ─────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Runtime deps only (curl for healthchecks)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY . .

# Non-root user for security
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Use gunicorn in production
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "4", "-b", "0.0.0.0:5000", "main:app"]
