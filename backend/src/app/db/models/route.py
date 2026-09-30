import time
import uuid

from sqlalchemy import JSON, BigInteger, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def new_id() -> str:
    return uuid.uuid4().hex


class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    max_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    profile: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class LoginSession(Base):
    __tablename__ = "login_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    expires_at: Mapped[float] = mapped_column(Float)


class TrackItem(Base):
    __tablename__ = "track_items"
    __table_args__ = (UniqueConstraint("user_id", "olympiad_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    olympiad_id: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default="planned")
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


class Reminder(Base):
    __tablename__ = "reminders"
    __table_args__ = (UniqueConstraint("user_id", "dedup_key"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    olympiad_id: Mapped[str] = mapped_column(String(80))
    dedup_key: Mapped[str] = mapped_column(String(180))
    kind: Mapped[str] = mapped_column(String(30))
    due_at: Mapped[float] = mapped_column(Float, index=True)
    deadline: Mapped[float] = mapped_column(Float)
    state: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    content: Mapped[dict] = mapped_column(JSON)
    is_demo: Mapped[bool] = mapped_column(default=False)
    sent_at: Mapped[float | None] = mapped_column(Float)
    claimed_at: Mapped[float | None] = mapped_column(Float)
    error: Mapped[str | None] = mapped_column(String(300))
