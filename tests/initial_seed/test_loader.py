import json

import pytest

from financeiro_dr.initial_seed.loader import InitialSeedError, load_manifest


def _valid_payload():
    return {
        "schema_version": 1,
        "seed_id": "synthetic-v1",
        "source_label": "fixture",
        "source_sha256": "0" * 64,
        "expected": {
            "record_count": 1,
            "income_count": 0,
            "expense_count": 1,
            "income_cents": 0,
            "expense_cents": 1250,
        },
        "records": [
            {
                "source_row": 2,
                "holder": "PESSOA TESTE",
                "date": "2026-01-02",
                "description": "Despesa teste",
                "payment_method": "TRANSFERÊNCIA",
                "amount_cents": 1250,
                "category": "MORADIA",
                "raw_type": "MENSAL RECORRENTE",
                "classification": "DESPESA",
                "warning": None,
            }
        ],
    }


def test_rejects_unknown_schema(tmp_path):
    path = tmp_path / "seed.json"
    path.write_text(json.dumps({"schema_version": 99}), encoding="utf-8")
    with pytest.raises(InitialSeedError, match="versão"):
        load_manifest(path)


def test_loads_valid_synthetic_manifest(tmp_path):
    path = tmp_path / "seed.json"
    path.write_text(json.dumps(_valid_payload()), encoding="utf-8")
    manifest = load_manifest(path)
    assert manifest.seed_id == "synthetic-v1"
    assert manifest.records[0].amount_cents == 1250
    assert manifest.records[0].classification == "DESPESA"


def test_rejects_totals_that_do_not_match_records(tmp_path):
    payload = _valid_payload()
    payload["expected"]["expense_cents"] = 9999
    path = tmp_path / "seed.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(InitialSeedError, match="totais"):
        load_manifest(path)
