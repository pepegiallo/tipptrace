from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import get_db
from models import TippingGame, Member, PaymentMethod, VictoryStatus, PointsStatus

members_bp = Blueprint("members", __name__, template_folder="../templates/members")

@members_bp.route("/create/<int:game_id>", methods=["GET", "POST"])
def create(game_id):
    db = get_db()
    game = db.get(TippingGame, game_id)
    if not game:
        flash("Tippspiel nicht gefunden.", "warning")
        return redirect(url_for("main.index"))

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name  = request.form.get("last_name", "").strip()
        email      = request.form.get("email", "").strip()
        nickname   = request.form.get("nickname", "").strip() or None

        pm_label   = request.form.get("pm_label", "").strip()
        pm_ref     = request.form.get("pm_reference", "").strip() or None

        if not (first_name and last_name and email and pm_label):
            flash("Bitte füllen Sie alle Pflichtfelder aus (Vorname, Nachname, E-Mail, Zahlungsart-Bezeichnung).", "danger")
            return render_template("members/form.html", member=None, game=game, today=date.today())

        member = Member(
            game=game,
            first_name=first_name,
            last_name=last_name,
            email=email,
            nickname=nickname
        )
        pm = PaymentMethod(label=pm_label, reference=pm_ref, member=member)

        db.add(member)
        db.add(pm)
        db.commit()
        flash("Mitglied wurde angelegt.", "success")
        return redirect(url_for("games.detail", game_id=game.id))

    return render_template("members/form.html", member=None, game=game, today=date.today())

@members_bp.route("/edit/<int:member_id>", methods=["GET", "POST"])
def edit(member_id):
    db = get_db()
    member = db.get(Member, member_id)
    if not member:
        flash("Mitglied nicht gefunden.", "warning")
        return redirect(url_for("main.index"))
    game = member.game

    if request.method == "POST":
        action = request.form.get("action", "save_member")

        # 1) Nur Stammdaten speichern
        if action == "save_member":
            member.first_name = request.form.get("first_name", "").strip()
            member.last_name  = request.form.get("last_name", "").strip()
            member.email      = request.form.get("email", "").strip()
            member.nickname   = request.form.get("nickname", "").strip() or None

            pm_label   = request.form.get("pm_label", "").strip()
            pm_ref     = request.form.get("pm_reference", "").strip() or None

            if not (member.first_name and member.last_name and member.email and pm_label):
                flash("Bitte füllen Sie alle Pflichtfelder aus (Vorname, Nachname, E-Mail, Zahlungsart-Bezeichnung).", "danger")
                return render_template("members/form.html", member=member, game=game, today=date.today())

            if member.payment_method is None:
                member.payment_method = PaymentMethod(label=pm_label, reference=pm_ref, member=member)
            else:
                member.payment_method.label = pm_label
                member.payment_method.reference = pm_ref

            db.commit()
            flash("Mitglied wurde aktualisiert.", "success")
            return redirect(url_for("members.edit", member_id=member.id))

        # 2) Siege-Status hinzufügen (ohne Stammdaten zu prüfen)
        elif action == "add_victory":
            if not request.form.get("new_victories"):
                flash("Bitte einen Wert für Siege angeben.", "danger")
                return redirect(url_for("members.edit", member_id=member.id))
            try:
                victories_val = float(request.form.get("new_victories"))
                v_date_str = request.form.get("new_victories_date") or str(date.today())
                v_date = date.fromisoformat(v_date_str)
                db.add(VictoryStatus(member=member, victories=victories_val, date=v_date))
                db.commit()
                flash("Neuer Siege-Status hinzugefügt.", "success")
            except Exception:
                db.rollback()
                flash("Ungültiger Wert für Siege/Datum.", "danger")
            return redirect(url_for("members.edit", member_id=member.id))

        # 3) Punkte-Status hinzufügen (ohne Stammdaten zu prüfen)
        elif action == "add_points":
            if not request.form.get("new_points"):
                flash("Bitte einen Wert für Punkte angeben.", "danger")
                return redirect(url_for("members.edit", member_id=member.id))
            try:
                points_val = int(request.form.get("new_points"))
                p_date_str = request.form.get("new_points_date") or str(date.today())
                p_date = date.fromisoformat(p_date_str)
                db.add(PointsStatus(member=member, points=points_val, date=p_date))
                db.commit()
                flash("Neuer Punkte-Status hinzugefügt.", "success")
            except Exception:
                db.rollback()
                flash("Ungültiger Wert für Punkte/Datum.", "danger")
            return redirect(url_for("members.edit", member_id=member.id))

        # Fallback: zurück zur Bearbeitungsseite
        return redirect(url_for("members.edit", member_id=member.id))

    # GET
    return render_template("members/form.html", member=member, game=game, today=date.today())

@members_bp.route("/delete/<int:member_id>", methods=["POST"])
def delete(member_id):
    db = get_db()
    member = db.get(Member, member_id)
    if not member:
        flash("Mitglied nicht gefunden.", "warning")
        return redirect(url_for("main.index"))
    game_id = member.game_id
    db.delete(member)
    db.commit()
    flash("Mitglied wurde gelöscht.", "info")
    return redirect(url_for("games.detail", game_id=game_id))
