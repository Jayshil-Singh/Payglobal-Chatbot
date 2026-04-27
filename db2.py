"""
SQLAlchemy database layer (SQLite + Postgres).

This module is the enterprise-ready DB backend. It mirrors the public API of `db.py`
used by the app, but is powered by SQLAlchemy so we can:
- run on Postgres using DATABASE_URL
- use Alembic migrations cleanly
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    func,
    select,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from config import DB_PATH
from utils.logger import get_logger

log = get_logger(__name__)


def _default_database_url() -> str:
    url = (os.getenv("DATABASE_URL") or "").strip()
    if url:
        return url
    # default: local sqlite file
    return f"sqlite:///{DB_PATH}"


NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(String, default="user")
    must_change_password: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_ip: Mapped[str | None] = mapped_column(String, nullable=True)
    last_location: Mapped[str | None] = mapped_column(String, nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    conversations: Mapped[list[Conversation]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String, default="New Chat")
    module: Mapped[str] = mapped_column(String, default="All Modules")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped[User] = relationship(back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (UniqueConstraint("message_id", "user_id", name="uq_feedback_message_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class SessionToken(Base):
    __tablename__ = "sessions"

    token: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AdminAuditEvent(Base):
    __tablename__ = "admin_audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor_username: Mapped[str | None] = mapped_column(String, nullable=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    target_type: Mapped[str | None] = mapped_column(String, nullable=True)
    target_id: Mapped[str | None] = mapped_column(String, nullable=True)
    target_label: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def reset_engine_for_tests() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is not None:
        return _engine
    url = _default_database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite:///") else {}
    _engine = create_engine(url, future=True, pool_pre_ping=True, connect_args=connect_args)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
    return _engine


@contextmanager
def get_conn():
    """
    Backward-compatibility helper for legacy call-sites/tests that expect a DB-API
    connection object (sqlite-style execute/fetchone).
    """
    engine = get_engine()
    raw = engine.raw_connection()
    try:
        # SQLite-specific convenience for row access by key.
        try:
            import sqlite3

            if isinstance(raw, sqlite3.Connection):
                raw.row_factory = sqlite3.Row
        except Exception:
            pass
        yield raw
        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()


@contextmanager
def get_session() -> Session:
    if _SessionLocal is None:
        get_engine()
    assert _SessionLocal is not None
    db = _SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    log.info("Database initialized.")


# ── Sessions ──────────────────────────────────────────────────────────────


def create_session(user_id: int, token: str, hours: int = 72) -> None:
    expires = datetime.now(timezone.utc) + timedelta(hours=hours)
    with get_session() as s:
        s.merge(SessionToken(token=token, user_id=user_id, expires_at=expires))


def get_session_user(token: str) -> dict | None:
    with get_session() as s:
        row = s.execute(
            select(User).join(SessionToken, SessionToken.user_id == User.id).where(
                SessionToken.token == token, SessionToken.expires_at > datetime.now(timezone.utc)
            )
        ).scalar_one_or_none()
        if not row:
            return None
        u = row
        return {"id": u.id, "username": u.username, "email": u.email, "role": u.role}


def delete_session(token: str) -> None:
    with get_session() as s:
        s.execute(text("DELETE FROM sessions WHERE token = :t"), {"t": token})


# ── Users ─────────────────────────────────────────────────────────────────


def create_user(username: str, password_hash: str, email: str = "", role: str = "user") -> int:
    username = username.strip().lower()
    with get_session() as s:
        u = User(username=username, password_hash=password_hash, email=email or None, role=role)
        s.add(u)
        s.flush()
        return int(u.id)


def get_user(username: str) -> dict | None:
    username = username.strip().lower()
    with get_session() as s:
        u = s.execute(select(User).where(User.username == username)).scalar_one_or_none()
        return _user_to_dict(u) if u else None


def get_user_by_email(email: str) -> dict | None:
    email = (email or "").strip().lower()
    if not email:
        return None
    with get_session() as s:
        u = s.execute(select(User).where(func.lower(User.email) == email)).scalar_one_or_none()
        return _user_to_dict(u) if u else None


def update_last_login(user_id: int) -> None:
    with get_session() as s:
        s.execute(text("UPDATE users SET last_login = :t WHERE id = :id"), {"t": datetime.now(timezone.utc), "id": user_id})


def update_user_network(user_id: int, ip: str, location: str) -> None:
    with get_session() as s:
        s.execute(
            text("UPDATE users SET last_ip=:ip, last_location=:loc, last_seen_at=:t WHERE id=:id"),
            {"ip": (ip or "").strip(), "loc": (location or "").strip(), "t": datetime.now(timezone.utc), "id": user_id},
        )


def reset_user_password(user_id: int, new_password_hash: str) -> None:
    with get_session() as s:
        s.execute(text("UPDATE users SET password_hash = :h WHERE id = :id"), {"h": new_password_hash, "id": user_id})


def set_password_and_change_flag(user_id: int, new_password_hash: str, must_change_password: bool) -> None:
    with get_session() as s:
        s.execute(
            text("UPDATE users SET password_hash = :h, must_change_password = :f WHERE id = :id"),
            {"h": new_password_hash, "f": 1 if must_change_password else 0, "id": user_id},
        )


def set_must_change_password(user_id: int, must_change_password: bool) -> None:
    with get_session() as s:
        s.execute(
            text("UPDATE users SET must_change_password = :f WHERE id = :id"),
            {"f": 1 if must_change_password else 0, "id": user_id},
        )


def record_failed_login_attempt(user_id: int, lock_until: str | None = None) -> None:
    with get_session() as s:
        if lock_until:
            s.execute(
                text(
                    "UPDATE users SET failed_login_attempts = COALESCE(failed_login_attempts, 0) + 1, locked_until = :lu WHERE id = :id"
                ),
                {"lu": lock_until, "id": user_id},
            )
        else:
            s.execute(
                text("UPDATE users SET failed_login_attempts = COALESCE(failed_login_attempts, 0) + 1 WHERE id = :id"),
                {"id": user_id},
            )


def clear_failed_login_state(user_id: int) -> None:
    with get_session() as s:
        s.execute(text("UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE id = :id"), {"id": user_id})


def set_user_active(user_id: int, is_active: bool) -> None:
    with get_session() as s:
        s.execute(text("UPDATE users SET is_active = :a WHERE id = :id"), {"a": 1 if is_active else 0, "id": user_id})


def unlock_user(user_id: int) -> None:
    clear_failed_login_state(user_id)


def get_all_users() -> list[dict]:
    with get_session() as s:
        rows = s.execute(select(User).order_by(User.created_at.desc())).scalars().all()
        return [_user_to_dict(u) for u in rows]


def _user_to_dict(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "password_hash": u.password_hash,
        "email": u.email,
        "role": u.role,
        "must_change_password": u.must_change_password,
        "is_active": u.is_active,
        "failed_login_attempts": u.failed_login_attempts,
        "locked_until": u.locked_until.strftime("%Y-%m-%d %H:%M:%S") if u.locked_until else None,
        "last_ip": u.last_ip,
        "last_location": u.last_location,
        "last_seen_at": u.last_seen_at.strftime("%Y-%m-%d %H:%M:%S") if u.last_seen_at else None,
        "created_at": u.created_at.strftime("%Y-%m-%d %H:%M:%S") if u.created_at else None,
        "last_login": u.last_login.strftime("%Y-%m-%d %H:%M:%S") if u.last_login else None,
    }


# ── Conversations / Messages ───────────────────────────────────────────────


def create_conversation(user_id: int, title: str = "New Chat", module: str = "All Modules") -> int:
    with get_session() as s:
        c = Conversation(user_id=user_id, title=title, module=module)
        s.add(c)
        s.flush()
        return int(c.id)


def get_user_conversations(user_id: int) -> list[dict]:
    with get_session() as s:
        rows = s.execute(select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc())).scalars().all()
        return [_conv_to_dict(c) for c in rows]


def get_all_conversations_admin() -> list[dict]:
    with get_session() as s:
        rows = s.execute(select(Conversation, User.username).join(User, Conversation.user_id == User.id).order_by(Conversation.updated_at.desc())).all()
        out = []
        for c, uname in rows:
            d = _conv_to_dict(c)
            d["username"] = uname
            out.append(d)
        return out


def update_conversation_title(conv_id: int, title: str) -> None:
    with get_session() as s:
        s.execute(text("UPDATE conversations SET title = :t, updated_at = :u WHERE id = :id"), {"t": title[:60], "u": datetime.now(timezone.utc), "id": conv_id})


def delete_conversation(conv_id: int) -> None:
    with get_session() as s:
        s.execute(text("DELETE FROM conversations WHERE id = :id"), {"id": conv_id})


def save_message(conv_id: int, role: str, content: str, sources=None) -> int:
    with get_session() as s:
        m = Message(conversation_id=conv_id, role=role, content=content, sources=json.dumps(sources or []))
        s.add(m)
        s.flush()
        s.execute(text("UPDATE conversations SET updated_at = :u WHERE id = :id"), {"u": datetime.now(timezone.utc), "id": conv_id})
        return int(m.id)


def get_messages(conv_id: int) -> list[dict]:
    with get_session() as s:
        rows = s.execute(select(Message).where(Message.conversation_id == conv_id).order_by(Message.timestamp.asc())).scalars().all()
        out = []
        for m in rows:
            out.append(
                {
                    "id": m.id,
                    "conversation_id": m.conversation_id,
                    "role": m.role,
                    "content": m.content,
                    "sources": json.loads(m.sources or "[]"),
                    "timestamp": m.timestamp.strftime("%Y-%m-%d %H:%M:%S") if m.timestamp else None,
                }
            )
        return out


def purge_data_older_than(days: int) -> dict:
    days = int(days)
    if days <= 0:
        return {"deleted_messages": 0, "deleted_conversations": 0}
    with get_session() as s:
        dm = s.execute(text("DELETE FROM messages WHERE timestamp < (CURRENT_TIMESTAMP - INTERVAL :d)"), {"d": f"{days} days"})
        dc = s.execute(text("DELETE FROM conversations WHERE updated_at < (CURRENT_TIMESTAMP - INTERVAL :d)"), {"d": f"{days} days"})
        # SQLite doesn’t support INTERVAL; fall back
        if get_engine().url.get_backend_name().startswith("sqlite"):
            dm = s.execute(text("DELETE FROM messages WHERE timestamp < DATETIME('now', :d)"), {"d": f"-{days} days"})
            dc = s.execute(text("DELETE FROM conversations WHERE updated_at < DATETIME('now', :d)"), {"d": f"-{days} days"})
        return {"deleted_messages": dm.rowcount or 0, "deleted_conversations": dc.rowcount or 0}


def _conv_to_dict(c: Conversation) -> dict:
    return {
        "id": c.id,
        "user_id": c.user_id,
        "title": c.title,
        "module": c.module,
        "created_at": c.created_at.strftime("%Y-%m-%d %H:%M:%S") if c.created_at else None,
        "updated_at": c.updated_at.strftime("%Y-%m-%d %H:%M:%S") if c.updated_at else None,
    }


# ── Feedback ───────────────────────────────────────────────────────────────


def save_feedback(message_id: int, user_id: int, rating: int, comment: str = "") -> None:
    with get_session() as s:
        # upsert
        backend = get_engine().url.get_backend_name()
        if backend.startswith("sqlite"):
            s.execute(
                text(
                    """
                    INSERT INTO feedback (message_id, user_id, rating, comment)
                    VALUES (:m, :u, :r, :c)
                    ON CONFLICT(message_id, user_id) DO UPDATE SET
                        rating = excluded.rating,
                        comment = excluded.comment,
                        timestamp = CURRENT_TIMESTAMP
                    """
                ),
                {"m": message_id, "u": user_id, "r": rating, "c": comment},
            )
        else:
            s.execute(
                text(
                    """
                    INSERT INTO feedback (message_id, user_id, rating, comment)
                    VALUES (:m, :u, :r, :c)
                    ON CONFLICT (message_id, user_id) DO UPDATE SET
                        rating = EXCLUDED.rating,
                        comment = EXCLUDED.comment,
                        timestamp = CURRENT_TIMESTAMP
                    """
                ),
                {"m": message_id, "u": user_id, "r": rating, "c": comment},
            )


def get_feedback_stats() -> dict:
    with get_session() as s:
        row = s.execute(
            text(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN rating = 1  THEN 1 ELSE 0 END) AS thumbs_up,
                    SUM(CASE WHEN rating = -1 THEN 1 ELSE 0 END) AS thumbs_down
                FROM feedback
                """
            )
        ).mappings().first()
        return dict(row) if row else {"total": 0, "thumbs_up": 0, "thumbs_down": 0}


# ── Analytics / Audit ─────────────────────────────────────────────────────


def get_request_count_last_hour(user_id: int) -> int:
    with get_session() as s:
        backend = get_engine().url.get_backend_name()
        if backend.startswith("sqlite"):
            row = s.execute(
                text(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM messages m
                    JOIN conversations c ON m.conversation_id = c.id
                    WHERE c.user_id = :uid AND m.role = 'user' AND m.timestamp >= DATETIME('now', '-1 hour')
                    """
                ),
                {"uid": user_id},
            ).mappings().first()
        else:
            row = s.execute(
                text(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM messages m
                    JOIN conversations c ON m.conversation_id = c.id
                    WHERE c.user_id = :uid AND m.role = 'user' AND m.timestamp >= (NOW() - INTERVAL '1 hour')
                    """
                ),
                {"uid": user_id},
            ).mappings().first()
        return int(row["cnt"] or 0) if row else 0


def get_analytics_data() -> dict:
    with get_session() as s:
        totals = s.execute(
            text(
                """
                SELECT
                    (SELECT COUNT(*) FROM users)         AS total_users,
                    (SELECT COUNT(*) FROM conversations) AS total_conversations,
                    (SELECT COUNT(*) FROM messages)      AS total_messages,
                    (SELECT COUNT(*) FROM messages WHERE role='user') AS total_questions
                """
            )
        ).mappings().first()
        data = dict(totals) if totals else {}
        data["feedback"] = get_feedback_stats()
        return data


def add_admin_audit_event(
    *,
    actor_user_id: int | None,
    actor_username: str,
    action: str,
    target_type: str = "",
    target_id: str = "",
    target_label: str = "",
    metadata: dict[str, Any] | None = None,
    ip: str = "",
) -> None:
    with get_session() as s:
        ev = AdminAuditEvent(
            actor_user_id=actor_user_id,
            actor_username=(actor_username or "").strip().lower(),
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            target_label=target_label,
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
            ip=ip,
        )
        s.add(ev)


def get_admin_audit_events(limit: int = 200) -> list[dict]:
    with get_session() as s:
        rows = (
            s.execute(select(AdminAuditEvent).order_by(AdminAuditEvent.created_at.desc(), AdminAuditEvent.id.desc()).limit(limit))
            .scalars()
            .all()
        )
        out = []
        for r in rows:
            d = {
                "id": r.id,
                "actor_user_id": r.actor_user_id,
                "actor_username": r.actor_username,
                "action": r.action,
                "target_type": r.target_type,
                "target_id": r.target_id,
                "target_label": r.target_label,
                "metadata_json": r.metadata_json,
                "ip": r.ip,
                "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else None,
            }
            out.append(d)
        return out


def get_recent_audit_log(limit: int = 100) -> list[dict]:
    with get_session() as s:
        rows = s.execute(
            text(
                """
                SELECT
                    u.username,
                    c.title      AS conversation,
                    c.module,
                    m.role,
                    m.content,
                    m.timestamp
                FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                JOIN users u ON c.user_id = u.id
                WHERE m.role = 'user'
                ORDER BY m.timestamp DESC
                LIMIT :lim
                """
            ),
            {"lim": limit},
        ).mappings().all()
        return [dict(r) for r in rows]


def delete_user(user_id: int) -> None:
    with get_session() as s:
        s.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})


def update_user_role(user_id: int, new_role: str) -> None:
    with get_session() as s:
        s.execute(text("UPDATE users SET role = :r WHERE id = :id"), {"r": new_role, "id": user_id})

