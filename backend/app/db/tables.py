"""SQLAlchemy ORM table mappings for persisted race data."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import func
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from backend.app.db.base import Base


class SessionRecord(Base):
    """Persist a loaded FastF1 session."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    event_name: Mapped[str] = mapped_column(String, nullable=False)
    session_name: Mapped[str] = mapped_column(String, nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )


class LapRecord(Base):
    """Persist normalized lap-level data for a session."""

    __tablename__ = "laps"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    session_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("sessions.id"),
        nullable=False,
    )
    driver_code: Mapped[str] = mapped_column(String, nullable=False)
    lap_number: Mapped[int] = mapped_column(Integer, nullable=False)
    lap_time_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    compound: Mapped[str | None] = mapped_column(String, nullable=True)
    tyre_life_laps: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    stint_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)


class StintRecord(Base):
    """Persist aggregated stint-level metrics for a session."""

    __tablename__ = "stints"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    session_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("sessions.id"),
        nullable=False,
    )
    driver_code: Mapped[str] = mapped_column(String, nullable=False)
    stint_number: Mapped[int] = mapped_column(Integer, nullable=False)
    tyre_compound: Mapped[str | None] = mapped_column(String, nullable=True)
    start_lap: Mapped[int] = mapped_column(Integer, nullable=False)
    end_lap: Mapped[int] = mapped_column(Integer, nullable=False)
    stint_length: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_lap_time_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    degradation_slope: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
