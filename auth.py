"""
Authentication: bcrypt-based password hashing + login/register logic.
"""
import secrets
import string
from datetime import datetime, timedelta, timezone

import bcrypt

from config import (
    DEFAULT_ADMIN_PASS,
    DEFAULT_ADMIN_USER,
    LOGIN_LOCKOUT_MINUTES,
    MAX_FAILED_LOGIN_ATTEMPTS,
    PASSWORD_MIN_LENGTH,
)
from db2 import (
    clear_failed_login_state,
    create_user,
    get_user,
    init_db,
    record_failed_login_attempt,
    reset_user_password,
    set_must_change_password,
    update_last_login,
)
from utils.logger import get_logger

log = get_logger(__name__)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def validate_password_strength(password: str) -> None:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters.")
    if not any(ch.islower() for ch in password):
        raise ValueError("Password must include at least one lowercase letter.")
    if not any(ch.isupper() for ch in password):
        raise ValueError("Password must include at least one uppercase letter.")
    if not any(ch.isdigit() for ch in password):
        raise ValueError("Password must include at least one number.")
    if not any(ch in "!@#$%^&*()_+-=[]{}|;:,.<>?/" for ch in password):
        raise ValueError("Password must include at least one special character.")


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


def login(username: str, password: str) -> dict | None:
    """
    Validate credentials.
    Returns user dict on success, None on failure.
    """
    user = get_user(username.strip().lower())
    if not user:
        return None
    if not user.get("is_active", 1):
        log.warning("Login blocked for disabled account: %s", username)
        return None
    locked_until = user.get("locked_until")
    if locked_until:
        try:
            lock_time = datetime.strptime(str(locked_until), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            if lock_time > datetime.now(timezone.utc):
                log.warning("Login blocked for locked account: %s", username)
                return None
        except ValueError:
            # Defensive: ignore malformed lockout value and allow normal auth flow.
            pass
    if not verify_password(password, user["password_hash"]):
        failed_attempts = int(user.get("failed_login_attempts") or 0) + 1
        lock_until_ts = None
        if failed_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
            lock_until_ts = (datetime.now(timezone.utc) + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            log.warning(
                "User locked due to failed logins: username=%s lockout_minutes=%s",
                username,
                LOGIN_LOCKOUT_MINUTES,
            )
        record_failed_login_attempt(user["id"], lock_until=lock_until_ts)
        return None
    clear_failed_login_state(user["id"])
    update_last_login(user["id"])
    log.info(f"Login successful: {username}")
    return get_user(username.strip().lower())


def register(username: str, password: str, email: str = "", role: str = "user") -> dict:
    """Register a new user. Raises ValueError if username taken."""
    username = username.strip().lower()
    if get_user(username):
        raise ValueError(f"Username '{username}' is already taken.")
    validate_password_strength(password)
    uid = create_user(
        username=username,
        password_hash=hash_password(password),
        email=email,
        role=role,
    )
    log.info(f"New user registered: {username} (id={uid}, role={role})")
    return get_user(username)


def generate_temp_password(length: int = 12) -> str:
    if length < 8:
        length = 8
    lower = secrets.choice(string.ascii_lowercase)
    upper = secrets.choice(string.ascii_uppercase)
    digit = secrets.choice(string.digits)
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?/"
    special = secrets.choice(special_chars)
    alphabet = string.ascii_letters + string.digits + special_chars
    remaining = [secrets.choice(alphabet) for _ in range(length - 4)]
    chars = [lower, upper, digit, special, *remaining]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def set_new_password(user_id: int, new_password: str, require_change_on_next_login: bool = False) -> None:
    validate_password_strength(new_password)
    reset_user_password(user_id, hash_password(new_password))
    set_must_change_password(user_id, require_change_on_next_login)
    log.info(
        "Password changed for user_id=%s; must_change_password=%s",
        user_id,
        1 if require_change_on_next_login else 0,
    )

