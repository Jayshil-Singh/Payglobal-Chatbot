"""
SQLite database layer.
Tables: users, conversations, messages, feedback
"""
import sqlite3
import json
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
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
                FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
            );
        """)
    log.info("Database initialized.")


# ── Users ──────────────────────────────────────────────────────────────────

def create_user(username: str, password_hash: str, email: str = "", role: str = "user") -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, email, role) VALUES (?, ?, ?, ?)",
            (username, password_hash, email, role),
        )
        return cur.lastrowid


def get_user(username: str) -> Optional[Dict]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None


def update_last_login(user_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), user_id),
        )


# ── Conversations ──────────────────────────────────────────────────────────

def create_conversation(user_id: int, title: str = "New Chat", module: str = "All Modules") -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO conversations (user_id, title, module) VALUES (?, ?, ?)",
            (user_id, title, module),
        )
        return cur.lastrowid


def get_user_conversations(user_id: int) -> List[Dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_conversations_admin() -> List[Dict]:
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
            (title[:60], datetime.utcnow().isoformat(), conv_id),
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
            (datetime.utcnow().isoformat(), conv_id),
        )
    return msg_id


def get_messages(conv_id: int) -> List[Dict]:
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
            ON CONFLICT DO NOTHING
            """,
            (message_id, user_id, rating, comment),
        )


def get_feedback_stats() -> Dict:
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
    since = (datetime.utcnow() - timedelta(hours=1)).isoformat()
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

def get_all_users() -> List[Dict]:
    """Admin-only: return all registered users."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, username, email, role, created_at, last_login FROM users ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_analytics_data() -> Dict:
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
