import datetime
from decimal import Decimal

from sqlalchemy import (
    Integer,
    String,
    Numeric,
    Float,
    ForeignKey,
    Date,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.ext.hybrid import hybrid_property

from db import Base


class TippingGame(Base):
    __tablename__ = "tipping_games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    stake_per_person: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    url: Mapped[str] = mapped_column(String(500), nullable=True)

    # Beziehungen
    members: Mapped[list["Member"]] = relationship(
        "Member",
        back_populates="game",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    config: Mapped["GameConfig"] = relationship(
        "GameConfig",
        back_populates="game",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )

    placement_payouts: Mapped[list["PlacementPayout"]] = relationship(
        "PlacementPayout",
        back_populates="game",
        cascade="all, delete-orphan",
        order_by="PlacementPayout.rank.asc()",
        lazy="selectin",
    )

    @hybrid_property
    def total_stake(self) -> Decimal:
        count = len(self.members) if self.members is not None else 0
        return (self.stake_per_person or Decimal("0")) * Decimal(count)


class Member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("tipping_games.id", ondelete="CASCADE"), nullable=False)
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[str] = mapped_column(String(120))

    game: Mapped["TippingGame"] = relationship("TippingGame", back_populates="members")

    payment_method: Mapped["PaymentMethod"] = relationship(
        "PaymentMethod",
        back_populates="member",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin",
    )

    victory_statuses: Mapped[list["VictoryStatus"]] = relationship(
        "VictoryStatus",
        back_populates="member",
        cascade="all, delete-orphan",
        order_by="VictoryStatus.date.desc()",
        lazy="selectin",
    )

    points_statuses: Mapped[list["PointsStatus"]] = relationship(
        "PointsStatus",
        back_populates="member",
        cascade="all, delete-orphan",
        order_by="PointsStatus.date.desc()",
        lazy="selectin",
    )

    @property
    def latest_victory(self) -> "VictoryStatus | None":
        return self.victory_statuses[0] if self.victory_statuses else None

    @property
    def latest_points(self) -> "PointsStatus | None":
        return self.points_statuses[0] if self.points_statuses else None


class PaymentMethod(Base):
    __tablename__ = "payment_methods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str] = mapped_column(String(120), nullable=False)  # Bezeichnung
    reference: Mapped[str] = mapped_column(String(255))       # Referenz
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), unique=True)

    member: Mapped["Member"] = relationship("Member", back_populates="payment_method")


class VictoryStatus(Base):
    __tablename__ = "victory_statuses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    victories: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)

    member: Mapped["Member"] = relationship("Member", back_populates="victory_statuses")


class PointsStatus(Base):
    __tablename__ = "points_statuses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)

    member: Mapped["Member"] = relationship("Member", back_populates="points_statuses")


# ------------------------------
#  Erweiterung: Spiel-Konfiguration
# ------------------------------
class GameConfig(Base):
    __tablename__ = "game_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("tipping_games.id", ondelete="CASCADE"), unique=True)
    # Anteile in Prozent (0..100)
    victory_share_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=50)
    placement_share_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=50)
    # Für Siege
    num_matchdays: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    game: Mapped["TippingGame"] = relationship("TippingGame", back_populates="config")


class PlacementPayout(Base):
    __tablename__ = "placement_payouts"
    __table_args__ = (UniqueConstraint("game_id", "rank", name="uq_game_rank"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("tipping_games.id", ondelete="CASCADE"), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 = Sieger, 2 = Platz 2, ...
    percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)  # Anteil vom Platzierungs-Topf

    game: Mapped["TippingGame"] = relationship("TippingGame", back_populates="placement_payouts")
