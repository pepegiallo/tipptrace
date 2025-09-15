"""
kicktipp_sync.py
----------------
Synchronisiert Mitglieder (Spieler) eines Tippspiels und aktualisiert deren
Punkte- und Siegstände anhand der Kicktipp-Seite.

NEU: Es wird nur dann ein neuer PointsStatus/VictoryStatus angelegt, wenn sich
der Wert gegenüber dem letzten Wert (neuester Status <= Datum) geändert hat.
Existiert bereits ein Status am Datum und der Wert ist unterschiedlich, wird
dieser aktualisiert; ist er identisch, passiert nichts.

Voraussetzungen:
- Modelle in models.py (TippingGame, Member, PointsStatus, VictoryStatus)
- Scraper-Funktion `scrape_kicktipp_players(base_url)` aus kicktipp.py
"""

from __future__ import annotations

import datetime
import re
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from ..models import (
    TippingGame,
    Member,
    PointsStatus,
    VictoryStatus,
)
from ..kicktipp import scrape_kicktipp_players  # type: ignore


# -------------------------------
# Hilfsfunktionen
# -------------------------------

def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^\w]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "user"


def _get_or_create_member_by_nickname(db: Session, game: TippingGame, nickname: str) -> Member:
    member = (
        db.query(Member)
        .filter(Member.game_id == game.id, Member.nickname == nickname)
        .first()
    )
    if member:
        return member

    base = _slugify(nickname) if nickname else "spieler"
    email = f"{base}@placeholder.local"

    member = Member(
        game_id=game.id,
        first_name=nickname or "Spieler",
        last_name="",
        email=email,
        nickname=nickname or base,
    )
    db.add(member)
    db.flush()
    return member


def _latest_points_status_on_or_before(db: Session, member_id: int, date: datetime.date) -> Optional[PointsStatus]:
    return (
        db.query(PointsStatus)
        .filter(and_(PointsStatus.member_id == member_id, PointsStatus.date <= date))
        .order_by(desc(PointsStatus.date))
        .first()
    )


def _latest_victory_status_on_or_before(db: Session, member_id: int, date: datetime.date) -> Optional[VictoryStatus]:
    return (
        db.query(VictoryStatus)
        .filter(and_(VictoryStatus.member_id == member_id, VictoryStatus.date <= date))
        .order_by(desc(VictoryStatus.date))
        .first()
    )


def _upsert_points_status_if_changed(
    db: Session,
    member: Member,
    points: int,
    date: datetime.date,
) -> str:
    """
    - Falls es an `date` schon einen PointsStatus gibt:
        * Wert unterschiedlich -> Update
        * Wert gleich          -> keine Änderung
    - Falls es an `date` keinen Status gibt:
        * letzter Wert (<= date) identisch -> kein Insert
        * sonst -> Insert
    Returns: "created" | "updated" | "skipped"
    """
    existing_today = (
        db.query(PointsStatus)
        .filter(PointsStatus.member_id == member.id, PointsStatus.date == date)
        .first()
    )
    if existing_today:
        if int(existing_today.points) != int(points):
            existing_today.points = int(points)
            return "updated"
        return "skipped"

    latest_before_or_today = _latest_points_status_on_or_before(db, member.id, date)
    if latest_before_or_today and int(latest_before_or_today.points) == int(points):
        return "skipped"

    ps = PointsStatus(member_id=member.id, points=int(points), date=date)
    db.add(ps)
    return "created"


def _upsert_victory_status_if_changed(
    db: Session,
    member: Member,
    victories: float,
    date: datetime.date,
) -> str:
    """
    Logik analog zu Punkten, aber für Siege (float).
    Returns: "created" | "updated" | "skipped"
    """
    existing_today = (
        db.query(VictoryStatus)
        .filter(VictoryStatus.member_id == member.id, VictoryStatus.date == date)
        .first()
    )
    if existing_today:
        if float(existing_today.victories) != float(victories):
            existing_today.victories = float(victories)
            return "updated"
        return "skipped"

    latest_before_or_today = _latest_victory_status_on_or_before(db, member.id, date)
    if latest_before_or_today and float(latest_before_or_today.victories) == float(victories):
        return "skipped"

    vs = VictoryStatus(member_id=member.id, victories=float(victories), date=date)
    db.add(vs)
    return "created"


# -------------------------------
# Öffentliche Funktionen
# -------------------------------

def sync_kicktipp_players_for_game(
    db: Session,
    game: TippingGame,
    scrape_base_url: Optional[str] = None,
    as_of_date: Optional[datetime.date] = None,
) -> dict:
    """
    Synchronisiert alle Spieler, Punkte und Siege eines Tipp-Spiels.

    Es werden nur dann neue Status-Objekte angelegt, wenn sich der Wert ggü. dem
    zuletzt bekannten Status (<= Datum) geändert hat. Bereits vorhandene Einträge
    am selben Datum werden nur bei Wertänderung aktualisiert.
    """
    if not scrape_base_url:
        scrape_base_url = (game.url or "").strip()
    if not scrape_base_url:
        raise ValueError("Es wurde keine gültige Kicktipp-URL gefunden (game.url ist leer).")

    today = as_of_date or datetime.date.today()

    scraped = scrape_kicktipp_players(scrape_base_url)
    created_members = 0
    created_points = 0
    updated_points = 0
    skipped_points = 0
    created_victories = 0
    updated_victories = 0
    skipped_victories = 0

    for entry in scraped:
        nickname = str(entry.get("nickname") or "").strip()
        points = int(entry.get("points") or 0)
        victories = float(entry.get("victories") or 0.0)

        member = (
            db.query(Member)
            .filter(Member.game_id == game.id, Member.nickname == nickname)
            .first()
        )
        if not member:
            member = _get_or_create_member_by_nickname(db, game, nickname)
            created_members += 1

        # Punkte
        res_p = _upsert_points_status_if_changed(db, member, points, today)
        if res_p == "created":
            created_points += 1
        elif res_p == "updated":
            updated_points += 1
        else:
            skipped_points += 1

        # Siege
        res_v = _upsert_victory_status_if_changed(db, member, victories, today)
        if res_v == "created":
            created_victories += 1
        elif res_v == "updated":
            updated_victories += 1
        else:
            skipped_victories += 1

    return {
        "date": today.isoformat(),
        "scraped_count": len(scraped),
        "created_members": created_members,
        "points": {
            "created": created_points,
            "updated": updated_points,
            "skipped": skipped_points,
        },
        "victories": {
            "created": created_victories,
            "updated": updated_victories,
            "skipped": skipped_victories,
        },
    }


def sync_kicktipp_by_game_id(
    db: Session,
    game_id: int,
    as_of_date: Optional[datetime.date] = None,
    scrape_base_url: Optional[str] = None,
) -> dict:
    game = db.query(TippingGame).get(game_id)  # type: ignore[attr-defined]
    if not game:
        raise ValueError(f"TippingGame mit id={game_id} nicht gefunden.")
    if scrape_base_url is None:
        scrape_base_url = game.url
    return sync_kicktipp_players_for_game(db, game, scrape_base_url, as_of_date)
