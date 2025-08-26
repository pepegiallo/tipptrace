from flask import Flask
from decimal import Decimal
import os

from db import init_engine_and_session, init_db, close_db
from blueprints.main import main_bp
from blueprints.games import games_bp
from blueprints.members import members_bp

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-secret-change-me"

    # Datenbank unter data/database.db
    os.makedirs("data", exist_ok=True)
    app.config["DATABASE_URL"] = "sqlite:///data/database.db"

    # DB
    init_engine_and_session(app.config["DATABASE_URL"])
    init_db()
    app.teardown_appcontext(close_db)

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
    app.run(debug=True)
