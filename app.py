from flask import Flask
from decimal import Decimal
import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from db import init_engine_and_session, init_db, close_db
from blueprints.main import main_bp
from blueprints.games import games_bp
from blueprints.members import members_bp


def _resolve_database_url() -> str:
    """
    Bevorzugt genau EINE Variable:
      - DATABASE_URI
    Optional zur Kompatibilität:
      - DATABASE_URL
    Fallback: sqlite in ./data/database.db (im Container: /app/data, gemountet auf /data)
    """
    env_url = os.getenv("DATABASE_URI") or os.getenv("DATABASE_URL")
    if env_url:
        return env_url
    # Default (relativ -> /app/data/database.db; Dockerfile mountet /data als Volume)
    return "sqlite:///data/database.db"


def _ensure_sqlite_directory(db_url: str) -> None:
    """
    Legt bei SQLite-URLs das Zielverzeichnis an (falls nicht vorhanden).
    Unterstützt absolute Pfade (sqlite:////...) und relative (sqlite:///...).
    """
    if not db_url.startswith("sqlite:"):
        return

    # Strip schema
    path_part = db_url[len("sqlite:"):].lstrip("/")
    # Bei '////ABS' ergibt lstrip('/') -> 'ABS'; wir brauchen den führenden Slash zurück.
    if db_url.startswith("sqlite:////"):
        fs_path = "/" + path_part  # absolut
    elif db_url.startswith("sqlite:///"):
        # relativ zum Working Directory (systemd/Container: /app)
        fs_path = os.path.abspath(path_part)
    else:
        # andere Formen (z. B. sqlite://) ignorieren
        return

    # Ordner anlegen
    dir_path = Path(fs_path).parent
    dir_path.mkdir(parents=True, exist_ok=True)


def _configure_logging(app: Flask) -> None:
    """
    Optionales File-Logging für App-Logs.
    Gunicorn-Access/Error-Logs werden durch die Service-Parameter geschrieben.
    Setze LOG_DIR, um app.log zu aktivieren.
    """
    log_dir = os.getenv("LOG_DIR")
    if not log_dir:
        return

    Path(log_dir).mkdir(parents=True, exist_ok=True)
    log_file = Path(log_dir) / "app.log"

    handler = RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    handler.setFormatter(formatter)

    app.logger.setLevel(logging.INFO)
    app.logger.addHandler(handler)

    # Werkzeug/Request-Logger ebenfalls auf File führen (optional)
    logging.getLogger("werkzeug").setLevel(logging.INFO)
    logging.getLogger("werkzeug").addHandler(handler)


def create_app():
    app = Flask(__name__)

    # Geheimnis aus ENV (sonst Default)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")

    # Datenbank-URL auflösen & ggf. Verzeichnis anlegen
    db_url = _resolve_database_url()
    _ensure_sqlite_directory(db_url)
    # Einheitlich nur noch DATABASE_URI in der App führen
    app.config["DATABASE_URI"] = db_url

    # DB initialisieren
    init_engine_and_session(app.config["DATABASE_URI"])
    init_db()
    app.teardown_appcontext(close_db)

    # Optionales File-Logging (ergänzend zu Gunicorn-Logs)
    _configure_logging(app)

    # Healthcheck-Endpoint (für Docker HEALTHCHECK)
    @app.get("/healthz")
    def healthz():
        return {"status": "ok"}, 200

    # Jinja-Filter: Geldformat (2 Nachkommastellen)
    @app.template_filter("money")
    def money_filter(value):
        try:
            return f"{Decimal(value):.2f}"
        except Exception:
            return str(value)

    # Blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(games_bp, url_prefix="/games")
    app.register_blueprint(members_bp, url_prefix="/members")

    return app


app = create_app()

if __name__ == "__main__":
    # Lokaler Dev-Server (für Entwicklung). Im Deployment übernimmt Gunicorn.
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_RUN_PORT", "8000"))
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)
