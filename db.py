"""
SQLite database layer.
Tables: users, conversations, messages, feedback
"""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

from config import DB_PATH
from utils.logger import get_logger

log = get_logger(__name__)


# ── Connection ─────────────────────────────────────────────────────────────

@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Schema ─────────────────────────────────────────────────────────────────

def init_db():
    """Create tables if they don't exist."""
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                email         TEXT,
                role          TEXT DEFAULT 'user',
                must_change_password INTEGER DEFAULT 0,
                is_active     INTEGER DEFAULT 1,
                failed_login_attempts INTEGER DEFAULT 0,
                locked_until  TIMESTAMP,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login    TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                title      TEXT DEFAULT 'New Chat',
                module     TEXT DEFAULT 'All Modules',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS messages (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role            TEXT NOT NULL,
                content         TEXT NOT NULL,
                sources         TEXT,
                timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS feedback (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                user_id    INTEGER NOT NULL,
                rating     INTEGER NOT NULL,  -- 1 = thumbs up, -1 = thumbs down
                comment    TEXT,
                timestamp  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
                UNIQUE (message_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token      TEXT PRIMARY KEY,
                user_id    INTEGER NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS admin_audit_events (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_user_id  INTEGER,
                actor_username TEXT,
                action         TEXT NOT NULL,
                target_type    TEXT,
                target_id      TEXT,
                target_label   TEXT,
                metadata_json  TEXT,
                ip             TEXT,
                created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            DELETE FROM feedback
            WHERE id NOT IN (
                SELECT MAX(id)
                FROM feedback
                GROUP BY message_id, user_id
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_feedback_message_user
            ON feedback (message_id, user_id);
        """)
        cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
        if "must_change_password" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN must_change_password INTEGER DEFAULT 0")
        if "is_active" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN is_active INTEGER DEFAULT 1")
            conn.execute("UPDATE users SET is_active = 1 WHERE is_active IS NULL")
        if "failed_login_attempts" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0")
            conn.execute("UPDATE users SET failed_login_attempts = 0 WHERE failed_login_attempts IS NULL")
        if "locked_until" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN locked_until TIMESTAMP")
    log.info("Database initialized.")


# ── Sessions (persistent login) ────────────────────────────────────────────

def create_session(user_id: int, token: str, hours: int = 72) -> None:
    expires = (datetime.now(timezone.utc) + timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires),
        )


def get_session_user(token: str) -> dict | None:
    """Return the user dict if the session token is valid & not expired, else None."""
    with get_conn() as conn:
        row = conn.execute(
            """SELECT u.id, u.username, u.email, u.role
               FROM sessions s JOIN users u ON s.user_id = u.id
               WHERE s.token = ? AND s.expires_at > CURRENT_TIMESTAMP""",
            (token,),
        ).fetchone()
    return dict(row) if row else None


def delete_session(token: str) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


# ── Users ──────────────────────────────────────────────────────────────────

def create_user(username: str, password_hash: str, email: str = "", role: str = "user") -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, email, role) VALUES (?, ?, ?, ?)",
            (username, password_hash, email, role),
        )
        return cur.lastrowid


def get_user(username: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None


def update_last_login(user_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), user_id),
        )


# ── Conversations ──────────────────────────────────────────────────────────

def create_conversation(user_id: int, title: str = "New Chat", module: str = "All Modules") -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO conversations (user_id, title, module) VALUES (?, ?, ?)",
            (user_id, title, module),
        )
        return cur.lastrowid


def get_user_conversations(user_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_conversations_admin() -> list[dict]:
    """Admin-only: all conversations across all users, with username attached."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT c.*, u.username
            FROM conversations c
            JOIN users u ON c.user_id = u.id
            ORDER BY c.updated_at DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]


def update_conversation_title(conv_id: int, title: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ?",
            (title[:60], datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), conv_id),
        )


def delete_conversation(conv_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))


# ── Messages ───────────────────────────────────────────────────────────────

def save_message(conv_id: int, role: str, content: str, sources=None) -> int:
    """Save a message and return its row id."""
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO messages (conversation_id, role, content, sources) VALUES (?, ?, ?, ?)",
            (conv_id, role, content, json.dumps(sources or [])),
        )
        msg_id = cur.lastrowid
    # Bump conversation updated_at
    with get_conn() as conn:
        conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), conv_id),
        )
    return msg_id


def get_messages(conv_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC",
            (conv_id,),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["sources"] = json.loads(d.get("sources") or "[]")
            result.append(d)
        return result


# ── Feedback ───────────────────────────────────────────────────────────────

def save_feedback(message_id: int, user_id: int, rating: int, comment: str = ""):
    """Save thumbs up (1) or thumbs down (-1) for a message."""
    with get_conn() as conn:
        # Upsert: one feedback per user per message
        conn.execute(
            """
            INSERT INTO feedback (message_id, user_id, rating, comment)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(message_id, user_id)
            DO UPDATE SET
                rating = excluded.rating,
                comment = excluded.comment,
                timestamp = CURRENT_TIMESTAMP
            """,
            (message_id, user_id, rating, comment),
        )


def get_feedback_stats() -> dict:
    """Return aggregate feedback stats for admin/analytics."""
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN rating = 1  THEN 1 ELSE 0 END) AS thumbs_up,
                SUM(CASE WHEN rating = -1 THEN 1 ELSE 0 END) AS thumbs_down
            FROM feedback
            """
        ).fetchone()
        return dict(row) if row else {"total": 0, "thumbs_up": 0, "thumbs_down": 0}


# ── Rate Limiting ──────────────────────────────────────────────────────────

def get_request_count_last_hour(user_id: int) -> int:
    """Count how many user messages this user sent in the last 60 minutes."""
    since = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM messages m
            JOIN conversations c ON m.conversation_id = c.id
            WHERE c.user_id = ? AND m.role = 'user' AND m.timestamp >= ?
            """,
            (user_id, since),
        ).fetchone()
        return row["cnt"] if row else 0


# ── Admin / Analytics ──────────────────────────────────────────────────────

def get_all_users() -> list[dict]:
    """Admin-only: return all registered users."""
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT
                id, username, email, role,
                is_active, must_change_password, failed_login_attempts, locked_until,
                created_at, last_login
            FROM users
            ORDER BY created_at DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]


def get_analytics_data() -> dict:
    """Comprehensive analytics for the admin dashboard."""
    with get_conn() as conn:
        # Totals
        totals = dict(conn.execute("""
            SELECT
                (SELECT COUNT(*) FROM users)         AS total_users,
                (SELECT COUNT(*) FROM conversations) AS total_conversations,
                (SELECT COUNT(*) FROM messages)      AS total_messages,
                (SELECT COUNT(*) FROM messages WHERE role='user') AS total_questions
        """).fetchone())

        # Messages per day (last 14 days)
        daily_rows = conn.execute("""
            SELECT DATE(timestamp) AS day, COUNT(*) AS cnt
            FROM messages
            WHERE role = 'user'
              AND timestamp >= DATE('now', '-14 days')
            GROUP BY day
            ORDER BY day ASC
        """).fetchall()
        totals["daily_messages"] = [dict(r) for r in daily_rows]

        # Module usage distribution
        module_rows = conn.execute("""
            SELECT module, COUNT(*) AS cnt
            FROM conversations
            GROUP BY module
            ORDER BY cnt DESC
        """).fetchall()
        totals["module_usage"] = [dict(r) for r in module_rows]

        # Top 10 most active users
        top_users = conn.execute("""
            SELECT u.username, COUNT(m.id) AS msg_count
            FROM messages m
            JOIN conversations c ON m.conversation_id = c.id
            JOIN users u ON c.user_id = u.id
            WHERE m.role = 'user'
            GROUP BY u.id
            ORDER BY msg_count DESC
            LIMIT 10
        """).fetchall()
        totals["top_users"] = [dict(r) for r in top_users]

        # Feedback stats
        fb = conn.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN rating =  1 THEN 1 ELSE 0 END) AS thumbs_up,
                SUM(CASE WHEN rating = -1 THEN 1 ELSE 0 END) AS thumbs_down
            FROM feedback
        """).fetchone()
        totals["feedback"] = dict(fb) if fb else {"total": 0, "thumbs_up": 0, "thumbs_down": 0}

        return totals


# ── Admin User Management ──────────────────────────────────────────────────

def delete_user(user_id: int) -> None:
    """Delete a user and all associated conversations/messages/feedback."""
    with get_conn() as conn:
        # Cascade: feedback → messages → conversations → user
        conn.execute("DELETE FROM feedback WHERE user_id = ?", (user_id,))
        conv_ids = [
            r[0] for r in conn.execute(
                "SELECT id FROM conversations WHERE user_id = ?", (user_id,)
            ).fetchall()
        ]
        for cid in conv_ids:
            conn.execute("DELETE FROM messages WHERE conversation_id = ?", (cid,))
        conn.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))


def update_user_role(user_id: int, new_role: str) -> None:
    """Promote or demote a user's role ('user' | 'admin')."""
    with get_conn() as conn:
        conn.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))


def reset_user_password(user_id: int, new_password_hash: str) -> None:
    """Overwrite a user's password hash (pre-hashed with bcrypt)."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_password_hash, user_id),
        )


def set_password_and_change_flag(user_id: int, new_password_hash: str, must_change_password: bool) -> None:
    """Overwrite password hash and update first-login password-change requirement."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ?, must_change_password = ? WHERE id = ?",
            (new_password_hash, 1 if must_change_password else 0, user_id),
        )


def set_must_change_password(user_id: int, must_change_password: bool) -> None:
    """Update first-login password-change requirement flag only."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET must_change_password = ? WHERE id = ?",
            (1 if must_change_password else 0, user_id),
        )


def record_failed_login_attempt(user_id: int, lock_until: str | None = None) -> None:
    """Increment failed login attempts and optionally set lockout expiration."""
    with get_conn() as conn:
        if lock_until:
            conn.execute(
                """
                UPDATE users
                SET failed_login_attempts = COALESCE(failed_login_attempts, 0) + 1,
                    locked_until = ?
                WHERE id = ?
                """,
                (lock_until, user_id),
            )
        else:
            conn.execute(
                """
                UPDATE users
                SET failed_login_attempts = COALESCE(failed_login_attempts, 0) + 1
                WHERE id = ?
                """,
                (user_id,),
            )


def clear_failed_login_state(user_id: int) -> None:
    """Reset lockout and failed login state after successful authentication."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET failed_login_attempts = 0, locked_until = NULL WHERE id = ?",
            (user_id,),
        )


def set_user_active(user_id: int, is_active: bool) -> None:
    """Enable or disable a user account."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET is_active = ? WHERE id = ?",
            (1 if is_active else 0, user_id),
        )


def unlock_user(user_id: int) -> None:
    """Manually clear lockout counters for a user account."""
    clear_failed_login_state(user_id)


# ── Admin Audit Events ──────────────────────────────────────────────────────


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
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO admin_audit_events
            (actor_user_id, actor_username, action, target_type, target_id, target_label, metadata_json, ip)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                actor_user_id,
                (actor_username or "").strip().lower(),
                action,
                target_type,
                str(target_id) if target_id is not None else "",
                target_label,
                json.dumps(metadata or {}, ensure_ascii=False),
                ip,
            ),
        )


def get_admin_audit_events(limit: int = 200) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM admin_audit_events
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        out: list[dict] = []
        for r in rows:
            d = dict(r)
            try:
                d["metadata"] = json.loads(d.get("metadata_json") or "{}")
            except Exception:
                d["metadata"] = {}
            out.append(d)
        return out


def get_recent_audit_log(limit: int = 100) -> list[dict]:
    """Return the most recent user messages across all conversations for audit."""
    with get_conn() as conn:
        rows = conn.execute(
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
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
