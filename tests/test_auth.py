import pytest

import auth
import db


def test_register_and_login_success(isolated_db):
    user = auth.register("alice", "Strong-password-123", "alice@example.com")
    assert user["username"] == "alice"

    logged_in = auth.login("alice", "Strong-password-123")
    assert logged_in is not None
    assert logged_in["id"] == user["id"]


def test_register_rejects_short_password(isolated_db):
    with pytest.raises(ValueError) as exc:
        auth.register("bob", "short", "bob@example.com")
    assert "at least" in str(exc.value)


def test_register_rejects_password_without_complexity(isolated_db):
    with pytest.raises(ValueError) as exc:
        auth.register("bob2", "alllowercase123", "bob2@example.com")
    assert "uppercase" in str(exc.value).lower()


def test_bootstrap_admin_skips_when_password_empty(isolated_db, monkeypatch):
    monkeypatch.setattr(auth, "DEFAULT_ADMIN_USER", "admin")
    monkeypatch.setattr(auth, "DEFAULT_ADMIN_PASS", "")

    auth.bootstrap_admin()
    assert db.get_user("admin") is None


def test_login_lockout_after_repeated_failures(isolated_db, monkeypatch):
    monkeypatch.setattr(auth, "MAX_FAILED_LOGIN_ATTEMPTS", 3)
    monkeypatch.setattr(auth, "LOGIN_LOCKOUT_MINUTES", 10)
    auth.register("lockme", "Strong-password-123", "lock@example.com")

    assert auth.login("lockme", "wrong-1") is None
    assert auth.login("lockme", "wrong-2") is None
    assert auth.login("lockme", "wrong-3") is None

    user = db.get_user("lockme")
    assert user is not None
    assert int(user.get("failed_login_attempts") or 0) >= 3
    assert user.get("locked_until")
    assert auth.login("lockme", "Strong-password-123") is None


def test_disabled_user_cannot_login(isolated_db):
    auth.register("disabled", "Strong-password-123", "disabled@example.com")
    user = db.get_user("disabled")
    assert user is not None

    db.set_user_active(user["id"], False)
    assert auth.login("disabled", "Strong-password-123") is None

    db.set_user_active(user["id"], True)
    assert auth.login("disabled", "Strong-password-123") is not None
