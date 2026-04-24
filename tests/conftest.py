from pathlib import Path

import pytest

import db


@pytest.fixture()
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point db module to a temporary sqlite file for each test."""
    test_db = tmp_path / "test_payglobal.db"
    monkeypatch.setattr(db, "DB_PATH", str(test_db))
    db.init_db()
    return test_db
