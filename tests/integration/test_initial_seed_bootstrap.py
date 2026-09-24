import json

import pytest

from financeiro_dr.app_paths import AppPaths
from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.initial_seed.loader import InitialSeedError
from financeiro_dr.main import _apply_initial_seed, main


def _write_seed(path):
    payload = {
        "schema_version": 1,
        "seed_id": "bootstrap-synthetic-v1",
        "source_label": "fixture",
        "source_sha256": "0" * 64,
        "expected": {
            "record_count": 1,
            "income_count": 0,
            "expense_count": 1,
            "income_cents": 0,
            "expense_cents": 2500,
        },
        "records": [
            {
                "source_row": 2,
                "holder": "PESSOA BOOTSTRAP",
                "date": "2026-02-01",
                "description": "Despesa bootstrap",
                "payment_method": "TRANSFERÊNCIA",
                "amount_cents": 2500,
                "category": "MORADIA",
                "raw_type": "MENSAL RECORRENTE",
                "classification": "DESPESA",
                "warning": None,
            }
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_app_paths_exposes_private_initial_seed_file(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    paths = AppPaths.from_environment()
    assert paths.initial_seed_file == paths.data_dir / "initial-seed.json"


def test_apply_initial_seed_loads_once_removes_file_and_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    paths = AppPaths.from_environment()
    con = Database(paths.database_file).connect()
    try:
        MigrationRunner().apply_all(con)
        _write_seed(paths.initial_seed_file)

        result = _apply_initial_seed(paths, con)
        assert result.inserted == 1
        assert not paths.initial_seed_file.exists()
        assert con.execute("SELECT COUNT(*) FROM financial_entry").fetchone()[0] == 1

        _write_seed(paths.initial_seed_file)
        again = _apply_initial_seed(paths, con)
        assert again.inserted == 0
        assert not paths.initial_seed_file.exists()
        assert con.execute("SELECT COUNT(*) FROM financial_entry").fetchone()[0] == 1
    finally:
        con.close()


def test_apply_initial_seed_is_noop_when_file_is_absent(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    paths = AppPaths.from_environment()
    con = Database(paths.database_file).connect()
    try:
        MigrationRunner().apply_all(con)
        assert _apply_initial_seed(paths, con) is None
        assert con.execute("SELECT COUNT(*) FROM financial_entry").fetchone()[0] == 0
    finally:
        con.close()


def test_malformed_seed_raises_without_batch_or_partial_entries(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    paths = AppPaths.from_environment()
    con = Database(paths.database_file).connect()
    try:
        MigrationRunner().apply_all(con)
        paths.initial_seed_file.write_text('{"schema_version":99}', encoding="utf-8")
        with pytest.raises(InitialSeedError):
            _apply_initial_seed(paths, con)
        assert paths.initial_seed_file.exists()
        assert con.execute("SELECT COUNT(*) FROM financial_entry").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM initial_seed_batch").fetchone()[0] == 0
    finally:
        con.close()


def test_smoke_test_returns_nonzero_for_invalid_seed_without_gui(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    paths = AppPaths.from_environment()
    paths.initial_seed_file.write_text('{"schema_version":99}', encoding="utf-8")
    assert main(["--smoke-test"]) == 3
