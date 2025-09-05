import os
from typing import Tuple
try:
    # Deine App ist laut README unter "app:app" erreichbar. :contentReference[oaicite:2]{index=2}
    from app import app as _app
except Exception as e:
    # Fallback für klare Fehlermeldung im Container-Log
    raise RuntimeError(f"Could not import 'app:app': {e}")

app = _app  # von Gunicorn als wsgi:app verwendet

# --- Health Endpoints ---
@app.get("/healthz")
def healthz():
    """
    Liveness-Check: Prozess läuft, HTTP-Stack antwortet.
    Keine DB-Pflicht, damit der Container früh "healthy" wird.
    """
    return {
        "status": "ok",
        "service": "tipptrace",
        "version": os.getenv("APP_VERSION", "unknown")
    }, 200

@app.get("/readyz")
def readyz():
    """
    Readiness-Check: einfache Plausibilitäten, z. B. SQLite-Verzeichnis vorhanden.
    (Optional – wenn du DB-Verfügbarkeit erzwingen willst, kannst du hier echte DB-Checks einbauen.)
    """
    db_url = os.getenv("SQLALCHEMY_DATABASE_URI", "")
    # SQLite-Heuristik: existiert das Zielverzeichnis?
    if db_url.startswith("sqlite:////"):
        path = db_url.replace("sqlite:////", "/")
        dir_ok = os.path.isdir(os.path.dirname(path)) if path else False
        if not dir_ok:
            return {"status": "degraded", "detail": "sqlite dir missing"}, 503
    # Für andere DBs (Postgres etc.) könntest du hier einen kurzen Connect-Versuch einbauen.
    return {"status": "ok"}, 200
