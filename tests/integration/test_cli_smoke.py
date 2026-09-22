from financeiro_dr.main import main


def test_smoke_mode_initializes_database_and_exits(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    assert main(["--smoke-test"]) == 0
    assert (tmp_path / "local" / "FinanceiroPessoalDr" / "financeiro.db").exists()
