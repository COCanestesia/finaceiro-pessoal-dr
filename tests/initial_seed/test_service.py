from datetime import date

import pytest

from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.initial_seed.loader import InitialSeedError
from financeiro_dr.initial_seed.models import (
    ExpectedTotals,
    InitialSeedManifest,
    InitialSeedRecord,
)
from financeiro_dr.initial_seed.service import InitialDataSeedService


def _open_db(tmp_path):
    con = Database(tmp_path / "seed.db").connect()
    MigrationRunner().apply_all(con)
    return con


def _record(
    source_row: int,
    *,
    classification: str = "DESPESA",
    amount_cents: int = 10000,
    description: str = "Despesa teste",
    category: str | None = "MORADIA",
    raw_type: str | None = "MENSAL RECORRENTE",
) -> InitialSeedRecord:
    return InitialSeedRecord(
        source_row=source_row,
        holder="PESSOA TESTE",
        date=date(2026, 1, source_row),
        description=description,
        payment_method="TRANSFERÊNCIA BANCÁRIA",
        amount_cents=amount_cents,
        category=category,
        raw_type=raw_type,
        classification=classification,
        warning=None,
    )


def _manifest(*records: InitialSeedRecord, seed_id: str = "synthetic-v1") -> InitialSeedManifest:
    incomes = [r for r in records if r.classification == "RECEITA"]
    expenses = [r for r in records if r.classification == "DESPESA"]
    return InitialSeedManifest(
        schema_version=1,
        seed_id=seed_id,
        source_label="fixture",
        source_sha256="0" * 64,
        expected=ExpectedTotals(
            record_count=len(records),
            income_count=len(incomes),
            expense_count=len(expenses),
            income_cents=sum(r.amount_cents for r in incomes),
            expense_cents=sum(r.amount_cents for r in expenses),
        ),
        records=tuple(records),
    )


def test_applies_paid_expense_received_income_and_is_idempotent(tmp_path):
    con = _open_db(tmp_path)
    try:
        expense = _record(2)
        income = _record(
            3,
            classification="RECEITA",
            amount_cents=50000,
            description="Receita teste",
            category=None,
            raw_type=None,
        )
        manifest = _manifest(expense, income)

        result = InitialDataSeedService(con).apply(manifest)
        assert result.inserted == 2
        assert result.reused == 0
        assert con.execute("SELECT COUNT(*) FROM financial_entry").fetchone()[0] == 2
        assert con.execute("SELECT COUNT(*) FROM initial_seed_batch").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 0

        expense_row = con.execute(
            "SELECT * FROM financial_entry WHERE entry_type='DESPESA'"
        ).fetchone()
        assert expense_row["status"] == "PAGO"
        assert expense_row["settled_date"] == expense.date.isoformat()
        assert expense_row["due_date"] is None
        assert expense_row["expense_nature"] == "FIXA"
        assert expense_row["is_recurring"] == 1
        assert expense_row["recurrence_rule_id"] is None

        income_row = con.execute(
            "SELECT * FROM financial_entry WHERE entry_type='RECEITA'"
        ).fetchone()
        assert income_row["status"] == "RECEBIDO"
        assert income_row["settled_date"] == income.date.isoformat()
        assert income_row["expense_nature"] is None
        assert income_row["is_recurring"] == 0

        again = InitialDataSeedService(con).apply(manifest)
        assert again.inserted == 0
        assert again.reused == 0
        assert con.execute("SELECT COUNT(*) FROM financial_entry").fetchone()[0] == 2
    finally:
        con.close()


def _insert_exact_existing(con, record: InitialSeedRecord) -> int:
    person_id = con.execute("INSERT INTO person(name) VALUES (?)", (record.holder,)).lastrowid
    category_id = con.execute("INSERT INTO category(name) VALUES (?)", (record.category,)).lastrowid
    return int(
        con.execute(
            """
            INSERT INTO financial_entry(
                competence_date, settled_date, description, amount_cents,
                entry_type, status, payment_method, is_recurring,
                beneficiary_id, category_id, expense_nature
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                record.date.isoformat(),
                record.date.isoformat(),
                record.description,
                record.amount_cents,
                "DESPESA",
                "PAGO",
                record.payment_method,
                1,
                person_id,
                category_id,
                "FIXA",
            ),
        ).lastrowid
    )


def test_reuses_one_exact_existing_entry(tmp_path):
    con = _open_db(tmp_path)
    try:
        record = _record(2)
        existing_id = _insert_exact_existing(con, record)

        result = InitialDataSeedService(con).apply(_manifest(record))

        assert result.inserted == 0
        assert result.reused == 1
        assert con.execute("SELECT COUNT(*) FROM financial_entry").fetchone()[0] == 1
        seed_row = con.execute("SELECT * FROM initial_seed_record").fetchone()
        assert seed_row["financial_entry_id"] == existing_id
        assert seed_row["action"] == "REUSED_EXISTING"
    finally:
        con.close()


def test_multiple_exact_existing_entries_are_not_collapsed(tmp_path):
    con = _open_db(tmp_path)
    try:
        record = _record(2)
        existing_id = _insert_exact_existing(con, record)
        row = con.execute("SELECT * FROM financial_entry WHERE id=?", (existing_id,)).fetchone()
        fields = [
            "competence_date", "settled_date", "description", "amount_cents",
            "entry_type", "status", "payment_method", "is_recurring",
            "beneficiary_id", "category_id", "expense_nature",
        ]
        con.execute(
            f"INSERT INTO financial_entry({','.join(fields)}) VALUES ({','.join('?' for _ in fields)})",
            tuple(row[field] for field in fields),
        )

        result = InitialDataSeedService(con).apply(_manifest(record))

        assert result.inserted == 1
        assert result.reused == 0
        assert con.execute("SELECT COUNT(*) FROM financial_entry").fetchone()[0] == 3
        assert con.execute("SELECT action FROM initial_seed_record").fetchone()[0] == "INSERTED"
    finally:
        con.close()


def test_known_category_alias_and_daily_type_are_normalized(tmp_path):
    con = _open_db(tmp_path)
    try:
        record = _record(
            2,
            category="CARTAO DE CREDITO",
            raw_type="DESPESA DIARIA ",
        )
        InitialDataSeedService(con).apply(_manifest(record))
        row = con.execute(
            """
            SELECT f.expense_nature, f.is_recurring, c.name
            FROM financial_entry f
            JOIN category c ON c.id=f.category_id
            """
        ).fetchone()
        assert row["expense_nature"] == "VARIAVEL"
        assert row["is_recurring"] == 0
        assert row["name"] == "CARTÃO DE CRÉDITO"
    finally:
        con.close()


def test_failure_midway_rolls_back_everything(tmp_path):
    con = _open_db(tmp_path)
    try:
        good = _record(2)
        invalid = _record(3, classification="DESCONHECIDO")
        manifest = _manifest(good, invalid, seed_id="rollback-v1")

        with pytest.raises(InitialSeedError):
            InitialDataSeedService(con).apply(manifest)

        assert con.execute("SELECT COUNT(*) FROM financial_entry").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM initial_seed_record").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM initial_seed_batch").fetchone()[0] == 0
    finally:
        con.close()
