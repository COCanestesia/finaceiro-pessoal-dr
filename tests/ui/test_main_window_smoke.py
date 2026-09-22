import pytest

pytest.importorskip("PySide6")

from financeiro_dr.app_paths import AppPaths
from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.main import build_window


def test_build_window_registers_complete_v1_pages(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    con = Database(tmp_path / "window.db").connect()
    MigrationRunner().apply_all(con)
    try:
        window = build_window(con, AppPaths.from_environment())
        qtbot.addWidget(window)
        assert window.stack.count() == 18
        assert set(window._page_indexes) == {
            "dashboard",
            "entries",
            "payables",
            "receivables",
            "agenda",
            "people",
            "classification",
            "budgets",
            "banks",
            "cards",
            "reconciliation",
            "assets",
            "investments",
            "documents",
            "reports",
            "history",
            "backup",
            "settings",
        }
    finally:
        con.close()
