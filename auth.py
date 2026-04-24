"""
Authentication: bcrypt-based password hashing + login/register logic.
"""
import bcrypt
from typing import Optional, Dict
from db import init_db, create_user, get_user, update_last_login
from config import DEFAULT_ADMIN_USER, DEFAULT_ADMIN_PASS
from utils.logger import get_logger

log = get_logger(__name__)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def bootstrap_admin():
    """Create bootstrap admin account if configured and not present."""
    init_db()
    if not DEFAULT_ADMIN_PASS:
        log.info("Admin bootstrap skipped (ADMIN_BOOTSTRAP_PASSWORD is empty).")
        return
    existing = get_user(DEFAULT_ADMIN_USER)
    if not existing:
        create_user(
            username=DEFAULT_ADMIN_USER,
            password_hash=hash_password(DEFAULT_ADMIN_PASS),
            email="admin@payglobal.local",
            role="admin",
        )
        log.info(f"Default admin account created: '{DEFAULT_ADMIN_USER}'")


def login(username: str, password: str) -> Optional[Dict]:
    """
    Validate credentials.
    Returns user dict on success, None on failure.
    """
    user = get_user(username.strip().lower())
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    update_last_login(user["id"])
    log.info(f"Login successful: {username}")
    return user


def register(username: str, password: str, email: str = "", role: str = "user") -> Dict:
    """Register a new user. Raises ValueError if username taken."""
    username = username.strip().lower()
    if get_user(username):
        raise ValueError(f"Username '{username}' is already taken.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    uid = create_user(
        username=username,
        password_hash=hash_password(password),
        email=email,
        role=role,
    )
    log.info(f"New user registered: {username} (id={uid}, role={role})")
    return get_user(username)

