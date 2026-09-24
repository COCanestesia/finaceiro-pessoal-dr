from datetime import date
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook

from financeiro_dr.initial_seed.loader import load_manifest
from tools.build_private_seed import build_seed


def _write_fixture(path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Entrada_dados"
    ws.append([
        "TITULAR",
        "DATA",
        "MÊS",
        "DESCRIÇÃO",
        "CONTA",
        "VALOR",
        "CATEGORIA",
        "TIPO DE DESPESA",
        "CLASSIFICAÇÃO",
    ])
    ws.append([
        "PESSOA TESTE",
        date(2026, 1, 2),
        "JANEIRO",
        "Despesa decimal",
        "TRANSFERÊNCIA BANCÁRIA",
        Decimal("12.34"),
        "CARTAO DE CREDITO",
        "DESPESA DIARIA ",
        "DESPESA ",
    ])
    ws.append([
        "PESSOA TESTE",
        date(2026, 1, 3),
        "JANEIRO",
        "Despesa sem valor",
        "ESPÉCIE",
        None,
        None,
        "MENSAL RECORRENTE",
        "DESPESA",
    ])
    wb.save(path)


def test_build_seed_converts_excel_to_valid_manifest(tmp_path):
    source = tmp_path / "fixture.xlsx"
    output = tmp_path / "fixture.initial-seed.json"
    _write_fixture(source)

    payload = build_seed(
        source,
        output,
        seed_id="synthetic-builder-v1",
        sheet_name="Entrada_dados",
    )
    manifest = load_manifest(output)

    assert payload["expected"]["record_count"] == 2
    assert manifest.records[0].amount_cents == 1234
    assert manifest.records[0].classification == "DESPESA"
    assert manifest.records[0].category == "CARTÃO DE CRÉDITO"
    assert manifest.records[0].raw_type == "DESPESA DIÁRIA"
    assert manifest.records[1].amount_cents == 0
    assert manifest.records[1].warning == "MISSING_AMOUNT"


def test_gitignore_blocks_private_seed_outputs():
    text = Path(".gitignore").read_text(encoding="utf-8")
    assert "*.initial-seed.json" in text
    assert "private-seed/" in text
    assert "private-release/" in text
