# Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System-Updates minimal
RUN apt-get update -y && apt-get install -y --no-install-recommends \
      build-essential \
    && rm -rf /var/lib/apt/lists/*

# Non-root User
RUN useradd -m -u 10001 appuser

WORKDIR /app

# Dependencies zuerst (Cache-effizient)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir gunicorn

# App-Code
COPY . .

# Datenverzeichnis (z.B. für SQLite/Logs)
RUN mkdir -p /data && chown -R appuser:appuser /data /app
VOLUME ["/data"]

# Default-DB (kann per Compose überschrieben werden)
ENV SQLALCHEMY_DATABASE_URI=sqlite:////data/app.db

# Port
EXPOSE 8000

USER appuser

# Start via Gunicorn
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:8000", "app:app"]
