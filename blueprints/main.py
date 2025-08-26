from flask import Blueprint, render_template
from db import get_db
from models import TippingGame

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    db = get_db()
    games = db.query(TippingGame).all()
    return render_template("index.html", games=games)
