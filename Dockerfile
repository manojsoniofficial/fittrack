# ── FitTrack Pro — Flask API Dockerfile ──────────────────────────────────────
# Multi-stage build: builder installs deps, final image is lean

# ── Stage 1: Builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tools needed for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-api.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements-api.txt


# ── Stage 2: Final image ──────────────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Runtime PostgreSQL client library only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY api/            ./api/
COPY models/         ./models/
COPY run_api.py      ./run_api.py

# Non-root user for security
RUN addgroup --system fittrack && adduser --system --ingroup fittrack fittrack
USER fittrack

# Expose API port
EXPOSE 5000

# Health-check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Production: gunicorn with 4 workers
CMD ["gunicorn", "run_api:app", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "4", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
