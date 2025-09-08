# Produktions-Image (ARM-tauglich, z. B. Raspberry Pi)
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# System-Abhängigkeiten (für psycopg2/SSL/libpq; ARM-kompatibel)
RUN apt-get update -y && apt-get install -y --no-install-recommends \
      build-essential \
      libpq5 \
      libpq-dev \
      ca-certificates \
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
# Hinweis: Für Supabase einfach beim Start DATABASE_URI setzen.
ENV DATABASE_URI=sqlite:////data/app.db

# HEALTHCHECK – pingt /healthz via Python Einzeiler
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import os,sys,urllib.request; url=f'http://127.0.0.1:{os.getenv(\"PORT\",\"8000\")}/healthz'; \
import urllib.request; \
import socket; \
socket.setdefaulttimeout(2); \
try: \
    with urllib.request.urlopen(url) as r: \
        sys.exit(0 if 200 <= r.status < 300 else 1) \
except Exception: \
    sys.exit(1)"

EXPOSE 8000
USER appuser

# Start über Gunicorn (WSGI)
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:8000", "wsgi:app"]
