from flask import Blueprint, render_template, request, redirect, url_for, flash
from decimal import Decimal
from db import get_db
from models import (
    TippingGame,
    Member,
    GameConfig,
    PlacementPayout,
)

games_bp = Blueprint("games", __name__, template_folder="../templates/games")


@games_bp.route("/create", methods=["GET", "POST"])
def create():
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        stake_raw = request.form.get("stake_per_person", "0").replace(",", ".")
        url = request.form.get("url", "").strip() or None

        if not name:
            flash("Name ist erforderlich.", "danger")
            return render_template("games/form.html", game=None)

        try:
            stake = Decimal(stake_raw)
        except Exception:
            flash("Einsatz pro Person muss eine Zahl sein.", "danger")
            return render_template("games/form.html", game=None)

        game = TippingGame(name=name, stake_per_person=stake, url=url)
        db.add(game)
        db.flush()  # damit game.id da ist

        # Default-Konfig anlegen
        cfg = GameConfig(
            game_id=game.id,
            victory_share_percent=Decimal("50.00"),
            placement_share_percent=Decimal("50.00"),
            num_matchdays=1,
        )
        db.add(cfg)
        db.commit()

        flash("Tippspiel wurde angelegt.", "success")
        return redirect(url_for("main.index"))
    return render_template("games/form.html", game=None)


@games_bp.route("/<int:game_id>/edit", methods=["GET", "POST"])
def edit(game_id):
    db = get_db()
    game = db.get(TippingGame, game_id)
    if not game:
        flash("Tippspiel nicht gefunden.", "warning")
        return redirect(url_for("main.index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        stake_raw = request.form.get("stake_per_person", "0").replace(",", ".")
        url = request.form.get("url", "").strip() or None

        if not name:
            flash("Name ist erforderlich.", "danger")
            return render_template("games/form.html", game=game)

        try:
            game.stake_per_person = Decimal(stake_raw)
        except Exception:
            flash("Einsatz pro Person muss eine Zahl sein.", "danger")
            return render_template("games/form.html", game=game)

        game.name = name
        game.url = url
        db.commit()
        flash("Tippspiel wurde aktualisiert.", "success")
        return redirect(url_for("games.detail", game_id=game.id))

    return render_template("games/form.html", game=game)


@games_bp.route("/<int:game_id>")
def detail(game_id):
    db = get_db()
    game = db.get(TippingGame, game_id)
    if not game:
        flash("Tippspiel nicht gefunden.", "warning")
        return redirect(url_for("main.index"))
    # Ensure config exists
    if not game.config:
        cfg = GameConfig(
            game_id=game.id,
            victory_share_percent=Decimal("50.00"),
            placement_share_percent=Decimal("50.00"),
            num_matchdays=1,
        )
        db.add(cfg)
        db.commit()
    return render_template("games/detail.html", game=game)


@games_bp.route("/<int:game_id>/delete", methods=["POST"])
def delete(game_id):
    db = get_db()
    game = db.get(TippingGame, game_id)
    if not game:
        flash("Tippspiel nicht gefunden.", "warning")
        return redirect(url_for("main.index"))
    db.delete(game)
    db.commit()
    flash("Tippspiel wurde gelöscht.", "info")
    return redirect(url_for("main.index"))


# ------------------------------
#   Konfiguration
# ------------------------------
@games_bp.route("/<int:game_id>/config", methods=["GET", "POST"])
def config(game_id):
    db = get_db()
    game = db.get(TippingGame, game_id)
    if not game:
        flash("Tippspiel nicht gefunden.", "warning")
        return redirect(url_for("main.index"))

    # ensure config
    if not game.config:
        game.config = GameConfig(
            game_id=game.id,
            victory_share_percent=Decimal("50.00"),
            placement_share_percent=Decimal("50.00"),
            num_matchdays=1,
        )
        db.add(game.config)
        db.commit()

    if request.method == "POST":
        action = request.form.get("action", "save_config")

        if action == "save_config":
            try:
                v = Decimal(request.form.get("victory_share_percent", "0").replace(",", "."))
                p = Decimal(request.form.get("placement_share_percent", "0").replace(",", "."))
                md = int(request.form.get("num_matchdays", "1"))

                if v + p != Decimal("100"):
                    flash("Die Summe von Siege-% und Platzierungs-% muss 100 ergeben.", "danger")
                    return render_template("games/config.html", game=game)

                if md <= 0:
                    flash("Anzahl der Spieltage muss größer 0 sein.", "danger")
                    return render_template("games/config.html", game=game)

                game.config.victory_share_percent = v
                game.config.placement_share_percent = p
                game.config.num_matchdays = md
                db.commit()
                flash("Konfiguration gespeichert.", "success")
                return redirect(url_for("games.config", game_id=game.id))
            except Exception:
                db.rollback()
                flash("Ungültige Eingaben.", "danger")
                return render_template("games/config.html", game=game)

        elif action == "add_rank":
            try:
                rank = int(request.form.get("rank"))
                percent = Decimal(request.form.get("percent", "0").replace(",", "."))
                if rank <= 0:
                    raise ValueError("Rank muss > 0 sein.")
                if percent < 0:
                    raise ValueError("Prozent muss ≥ 0 sein.")

                db.add(PlacementPayout(game_id=game.id, rank=rank, percent=percent))
                db.commit()
                flash("Platzierungsregel hinzugefügt.", "success")
            except Exception:
                db.rollback()
                flash("Konnte Platzierungsregel nicht hinzufügen. Prüfe Rang und Prozent (evtl. Duplikat?).", "danger")
            return redirect(url_for("games.config", game_id=game.id))

    return render_template("games/config.html", game=game)


@games_bp.route("/<int:game_id>/config/delete_rank/<int:rank_id>", methods=["POST"])
def delete_rank(game_id, rank_id):
    db = get_db()
    game = db.get(TippingGame, game_id)
    if not game:
        flash("Tippspiel nicht gefunden.", "warning")
        return redirect(url_for("main.index"))
    rp = db.get(PlacementPayout, rank_id)
    if not rp or rp.game_id != game.id:
        flash("Regel nicht gefunden.", "warning")
        return redirect(url_for("games.config", game_id=game.id))

    db.delete(rp)
    db.commit()
    flash("Platzierungsregel gelöscht.", "info")
    return redirect(url_for("games.config", game_id=game.id))


# ------------------------------
#   Auswertung
# ------------------------------
@games_bp.route("/<int:game_id>/evaluation")
def evaluation(game_id):
    db = get_db()
    game = db.get(TippingGame, game_id)
    if not game:
        flash("Tippspiel nicht gefunden.", "warning")
        return redirect(url_for("main.index"))

    # Sicherstellen, dass Konfig existiert
    if not game.config:
        flash("Bitte zuerst die Konfiguration einstellen.", "warning")
        return redirect(url_for("games.config", game_id=game.id))

    # Ranking: primär Punkte (desc), dann Siege (desc), dann Nachname/Vorname
    def latest_pts(m: Member) -> int:
        return m.latest_points.points if m.latest_points else 0

    def latest_vic(m: Member) -> float:
        return m.latest_victory.victories if m.latest_victory else 0.0

    members_sorted = sorted(
        game.members,
        key=lambda m: (latest_pts(m), latest_vic(m), m.last_name.lower(), m.first_name.lower()),
        reverse=True,
    )

    # Töpfe
    total_stake = Decimal(game.total_stake or 0)
    victory_pot = (total_stake * Decimal(game.config.victory_share_percent) / Decimal("100")).quantize(Decimal("0.01"))
    placement_pot = (total_stake * Decimal(game.config.placement_share_percent) / Decimal("100")).quantize(Decimal("0.01"))
    per_matchday = (victory_pot / Decimal(game.config.num_matchdays)).quantize(Decimal("0.01")) if game.config.num_matchdays > 0 else Decimal("0.00")

    # Platzierungsregeln in Dict
    rank_to_percent = {pp.rank: Decimal(pp.percent) for pp in game.placement_payouts}

    # Tabelle für Ausgabe
    rows = []
    for idx, m in enumerate(members_sorted, start=1):
        pts = latest_pts(m)
        vic = Decimal(str(latest_vic(m)))
        payout_victories = (per_matchday * vic).quantize(Decimal("0.01")) if per_matchday else Decimal("0.00")
        placement_percent = rank_to_percent.get(idx, Decimal("0"))
        payout_placement = (placement_pot * placement_percent / Decimal("100")).quantize(Decimal("0.01"))
        payout_total = (payout_victories + payout_placement).quantize(Decimal("0.01"))

        rows.append(
            {
                "rank": idx,
                "member": m,
                "points": pts,
                "victories": float(vic),
                "payout_victories": payout_victories,
                "payout_placement": payout_placement,
                "payout_total": payout_total,
            }
        )

    # Summe der Platzierungs-Prozente zur Info
    placement_percent_sum = sum((Decimal(pp.percent) for pp in game.placement_payouts), Decimal("0"))

    return render_template(
        "games/evaluation.html",
        game=game,
        rows=rows,
        victory_pot=victory_pot,
        placement_pot=placement_pot,
        per_matchday=per_matchday,
        placement_percent_sum=placement_percent_sum,
        total_stake=total_stake,
    )
