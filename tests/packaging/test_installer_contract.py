from pathlib import Path


def test_installer_accepts_external_private_seed():
    text = Path("packaging/installer.iss").read_text(encoding="utf-8")
    assert "FinanceiroPessoalDr.initial-seed.json" in text
    assert "Flags: external" in text
    assert "skipifsourcedoesntexist" in text
    assert "{localappdata}\\FinanceiroPessoalDr" in text
    assert 'DestName: "initial-seed.json"' in text
