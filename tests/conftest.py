from pathlib import Path

import pytest

import db2 as db


@pytest.fixture()
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point db module to a temporary sqlite file for each test."""
    test_db = tmp_path / "test_payglobal.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{test_db}")
    db.reset_engine_for_tests()
    db.init_db()
    return test_db
