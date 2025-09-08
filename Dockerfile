FROM python:3.11-slim AS builder

WORKDIR /app
COPY requirements.txt .

# Install build deps temporarily
RUN apt-get update && apt-get install -y gcc libjpeg-dev zlib1g-dev libpng-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get remove -y gcc \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# Final minimal image
FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /usr/local /usr/local
COPY . .

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 5000

# 🔑 Gunicorn config: 120s timeout, 4 workers, bind to all interfaces
CMD ["gunicorn", "mathAI:app", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "2", "--timeout", "180"]
