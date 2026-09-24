from __future__ import annotations

import hashlib
import json
import re
import sqlite3

from financeiro_dr.core.financeiro.models import CreateEntry
from financeiro_dr.core.financeiro.repository import FinancialRepository

from .loader import InitialSeedError
from .models import InitialSeedManifest, InitialSeedRecord, SeedApplyResult


_FIXED_TYPES = {"MENSAL RECORRENTE", "ANUAL"}
_CATEGORY_ALIASES = {
    "CARTAO DE CREDITO": "CARTÃO DE CRÉDITO",
}


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value).strip())
    return text or None


def _norm_key(value: str | None) -> str:
    return (_clean_text(value) or "").casefold()


def _canonical_category(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    if cleaned is None:
        return None
    return _CATEGORY_ALIASES.get(cleaned.upper(), cleaned)


def _raw_type_key(value: str | None) -> str:
    cleaned = (_clean_text(value) or "").upper()
    if cleaned == "DESPESA DIARIA":
        return "DESPESA DIÁRIA"
    return cleaned


def _record_hash(record: InitialSeedRecord) -> str:
    payload = {
        "source_row": record.source_row,
        "holder": _clean_text(record.holder),
        "date": record.date.isoformat(),
        "description": _clean_text(record.description),
        "payment_method": _clean_text(record.payment_method),
        "amount_cents": record.amount_cents,
        "category": _canonical_category(record.category),
        "raw_type": _raw_type_key(record.raw_type),
        "classification": (_clean_text(record.classification) or "").upper(),
        "warning": _clean_text(record.warning),
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class InitialDataSeedService:
    def __init__(self, connection: sqlite3.Connection):
        self.connection = connection
        self.repository = FinancialRepository(connection)

    def apply(self, manifest: InitialSeedManifest) -> SeedApplyResult:
        previous = self.connection.execute(
            "SELECT warning_count FROM initial_seed_batch WHERE seed_id=?",
            (manifest.seed_id,),
        ).fetchone()
        if previous is not None:
            return SeedApplyResult(inserted=0, reused=0, warnings=int(previous[0]))

        if manifest.schema_version != 1:
            raise InitialSeedError("A versão da base inicial não é suportada.")
        if manifest.expected.record_count != len(manifest.records):
            raise InitialSeedError("A quantidade de registros da base inicial não confere.")

        owns_transaction = not self.connection.in_transaction
        savepoint = "initial_seed_apply"
        try:
            if owns_transaction:
                self.connection.execute("BEGIN IMMEDIATE")
            else:
                self.connection.execute(f"SAVEPOINT {savepoint}")

            self.connection.execute(
                """
                INSERT INTO initial_seed_batch(
                    seed_id, source_label, source_sha256,
                    expected_count, applied_count, warning_count
                ) VALUES (?,?,?,?,0,0)
                """,
                (
                    manifest.seed_id,
                    manifest.source_label,
                    manifest.source_sha256,
                    manifest.expected.record_count,
                ),
            )

            inserted = 0
            reused = 0
            warnings = 0
            for record in manifest.records:
                entry_type, status, expense_nature, is_recurring = self._semantics(record)
                person_id = self._resolve_person(record.holder)
                category_id = self._resolve_category(record.category)
                existing_id = self._find_exact_existing(
                    record,
                    entry_type=entry_type,
                    status=status,
                    expense_nature=expense_nature,
                    is_recurring=is_recurring,
                    person_id=person_id,
                    category_id=category_id,
                )
                if existing_id is None:
                    entry_id = self.repository.insert(
                        CreateEntry(
                            description=_clean_text(record.description) or "",
                            amount_cents=record.amount_cents,
                            entry_type=entry_type,
                            status=status,
                            competence_date=record.date,
                            due_date=None,
                            settled_date=record.date,
                            payment_method=_clean_text(record.payment_method),
                            notes=None,
                            is_recurring=is_recurring,
                            beneficiary_id=person_id,
                            category_id=category_id,
                            expense_nature=expense_nature,
                            allow_duplicate=True,
                        )
                    )
                    action = "INSERTED"
                    inserted += 1
                else:
                    entry_id = existing_id
                    action = "REUSED_EXISTING"
                    reused += 1

                warning = _clean_text(record.warning)
                if warning:
                    warnings += 1
                self.connection.execute(
                    """
                    INSERT INTO initial_seed_record(
                        seed_id, source_row, record_hash,
                        financial_entry_id, action, warning_code
                    ) VALUES (?,?,?,?,?,?)
                    """,
                    (
                        manifest.seed_id,
                        record.source_row,
                        _record_hash(record),
                        entry_id,
                        action,
                        warning,
                    ),
                )

            if inserted + reused != manifest.expected.record_count:
                raise InitialSeedError("A carga inicial não contabilizou todos os registros.")

            self.connection.execute(
                """
                UPDATE initial_seed_batch
                SET applied_count=?, warning_count=?
                WHERE seed_id=?
                """,
                (inserted + reused, warnings, manifest.seed_id),
            )

            if owns_transaction:
                self.connection.commit()
            else:
                self.connection.execute(f"RELEASE SAVEPOINT {savepoint}")
            return SeedApplyResult(inserted=inserted, reused=reused, warnings=warnings)
        except Exception as exc:
            try:
                if owns_transaction:
                    if self.connection.in_transaction:
                        self.connection.rollback()
                else:
                    self.connection.execute(f"ROLLBACK TO SAVEPOINT {savepoint}")
                    self.connection.execute(f"RELEASE SAVEPOINT {savepoint}")
            except sqlite3.Error:
                pass
            if isinstance(exc, InitialSeedError):
                raise
            raise InitialSeedError(
                "Não foi possível aplicar a base inicial. Nenhuma carga parcial foi mantida."
            ) from exc

    @staticmethod
    def _semantics(record: InitialSeedRecord) -> tuple[str, str, str | None, bool]:
        classification = (_clean_text(record.classification) or "").upper()
        if classification == "RECEITA":
            return "RECEITA", "RECEBIDO", None, False
        if classification != "DESPESA":
            raise InitialSeedError("Existe uma classificação desconhecida na base inicial.")
        fixed = _raw_type_key(record.raw_type) in _FIXED_TYPES
        return "DESPESA", "PAGO", "FIXA" if fixed else "VARIAVEL", fixed

    def _resolve_person(self, holder: str) -> int:
        name = _clean_text(holder)
        if not name:
            raise InitialSeedError("Existe um titular vazio na base inicial.")
        target = _norm_key(name)
        for row in self.connection.execute("SELECT id,name FROM person"):
            if _norm_key(row["name"]) == target:
                return int(row["id"])
        cur = self.connection.execute("INSERT INTO person(name) VALUES (?)", (name,))
        return int(cur.lastrowid)

    def _resolve_category(self, category: str | None) -> int | None:
        name = _canonical_category(category)
        if name is None:
            return None
        target = _norm_key(name)
        for row in self.connection.execute("SELECT id,name FROM category"):
            if _norm_key(row["name"]) == target:
                return int(row["id"])
        cur = self.connection.execute("INSERT INTO category(name) VALUES (?)", (name,))
        return int(cur.lastrowid)

    def _find_exact_existing(
        self,
        record: InitialSeedRecord,
        *,
        entry_type: str,
        status: str,
        expense_nature: str | None,
        is_recurring: bool,
        person_id: int,
        category_id: int | None,
    ) -> int | None:
        candidates = self.connection.execute(
            """
            SELECT * FROM financial_entry
            WHERE competence_date=?
              AND amount_cents=?
              AND entry_type=?
              AND beneficiary_id=?
              AND deleted_at IS NULL
            """,
            (record.date.isoformat(), record.amount_cents, entry_type, person_id),
        ).fetchall()
        expected_description = _norm_key(record.description)
        expected_payment = _norm_key(record.payment_method)
        matches = []
        for row in candidates:
            if _norm_key(row["description"]) != expected_description:
                continue
            if _norm_key(row["payment_method"]) != expected_payment:
                continue
            if row["status"] != status:
                continue
            if row["settled_date"] != record.date.isoformat():
                continue
            if row["due_date"] is not None:
                continue
            if row["category_id"] != category_id:
                continue
            if row["expense_nature"] != expense_nature:
                continue
            if bool(row["is_recurring"]) != bool(is_recurring):
                continue
            if row["recurrence_rule_id"] is not None:
                continue
            matches.append(int(row["id"]))
        return matches[0] if len(matches) == 1 else None
