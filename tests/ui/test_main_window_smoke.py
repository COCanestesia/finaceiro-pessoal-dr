import pytest

pytest.importorskip("PySide6")

from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.main import build_window


def test_build_window_registers_daily_finance_pages(qtbot, tmp_path):
    con = Database(tmp_path / "window.db").connect()
    MigrationRunner().apply_all(con)
    try:
        window = build_window(con)
        qtbot.addWidget(window)
        assert window.stack.count() == 7
        assert set(window._page_indexes) == {
            "dashboard",
            "entries",
            "payables",
            "receivables",
            "agenda",
            "history",
            "settings",
        }
    finally:
        con.close()
