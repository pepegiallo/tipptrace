# Produktions-Image (ARM-tauglich, z. B. Raspberry Pi)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# System-Abhängigkeiten (psycopg2/SSL/libpq + curl)
RUN apt-get update -y && apt-get install -y --no-install-recommends \
      build-essential \
      libpq5 \
      libpq-dev \
      ca-certificates \
      curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root User
RUN useradd -m -u 10001 appuser
WORKDIR /app

# Dependencies zuerst (Caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App-Code
COPY . .

# Persistenz (SQLite/Logs – per Volume)
RUN mkdir -p /data && chown -R appuser:appuser /data /app
VOLUME ["/data"]

# Default-DB (per ENV überschreibbar) – nur EINE Variable mit Fallback-Logik in app.py
ENV DATABASE_URI=sqlite:////data/app.db

# HEALTHCHECK – sauberer HTTP-GET via curl
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT}/healthz" >/dev/null || exit 1

EXPOSE 8000
USER appuser

# Start über Gunicorn (WSGI)
# (Optional etwas ruhiger loggen: --log-level warning)
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:8000", "--log-level", "info", "wsgi:app"]
