import argparse
import sys
from pathlib import Path

# Ensure project root is on sys.path when running from scripts/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from auth import hash_password  # noqa: E402
from db2 import create_user, get_conn, get_user, init_db  # noqa: E402


def upsert_admin(username: str, password: str, email: str) -> None:
    username = username.strip().lower()
    init_db()

    existing = get_user(username)
    new_hash = hash_password(password)

    if not existing:
        create_user(username=username, password_hash=new_hash, email=email, role="admin")
        return

    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ?, role = 'admin' WHERE username = ?",
            (new_hash, username),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset (or create) the admin user for PayGlobal AI Assistant.")
    parser.add_argument("--username", default="admin", help="Admin username (default: admin)")
    parser.add_argument("--password", required=True, help="New admin password")
    parser.add_argument("--email", default="admin@payglobal.local", help="Admin email (default: admin@payglobal.local)")
    args = parser.parse_args()

    upsert_admin(args.username, args.password, args.email)
    print(f"OK: Admin user '{args.username}' password updated (role=admin).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

