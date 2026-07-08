# --- Stage 1: builder ---
FROM python:3.11-slim AS builder

WORKDIR /build

# Build dependencies for any C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps to a prefix we can copy
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# --- Stage 2: runtime ---
FROM python:3.11-slim

# Create non-root user early
RUN groupadd --system --gid 1001 appgroup \
    && useradd --system --uid 1001 --gid appgroup --no-create-home --shell /usr/sbin/nologin appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy source with correct ownership
COPY --chown=appuser:appgroup . .

# Pre-create data directory for SQLite + cache, owned by appuser
RUN mkdir -p /app/data && chown -R appuser:appgroup /app/data

# Drop privileges
USER appuser

# Default API port
EXPOSE 8001

# Healthcheck uses the dedicated readiness endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; r=urllib.request.urlopen('http://localhost:8001/api/health/ready', timeout=4); sys.exit(0 if r.status==200 else 1)" \
    || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
