import auth
import db


def test_register_and_login_success(isolated_db):
    user = auth.register("alice", "strong-password-123", "alice@example.com")
    assert user["username"] == "alice"

    logged_in = auth.login("alice", "strong-password-123")
    assert logged_in is not None
    assert logged_in["id"] == user["id"]


def test_register_rejects_short_password(isolated_db):
    try:
        auth.register("bob", "short", "bob@example.com")
        assert False, "Expected ValueError for short password"
    except ValueError as exc:
        assert "at least 8 characters" in str(exc)


def test_bootstrap_admin_skips_when_password_empty(isolated_db, monkeypatch):
    monkeypatch.setattr(auth, "DEFAULT_ADMIN_USER", "admin")
    monkeypatch.setattr(auth, "DEFAULT_ADMIN_PASS", "")

    auth.bootstrap_admin()
    assert db.get_user("admin") is None
