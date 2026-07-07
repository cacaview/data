FROM python:3.11-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Expose port
EXPOSE 8001

# Default API port for backend (frontend vite proxies to 8001)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]