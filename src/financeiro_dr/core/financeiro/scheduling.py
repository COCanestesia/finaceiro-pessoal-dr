from __future__ import annotations

from calendar import monthrange
from dataclasses import replace
from datetime import date
import sqlite3
from financeiro_dr.core.financeiro.models import CreateEntry
from financeiro_dr.core.financeiro.repository import FinancialRepository
from financeiro_dr.core.financeiro.service import FinancialService


def next_monthly_date(current: date, preferred_day: int) -> date:
    if not 1 <= preferred_day <= 31:
        raise ValueError("O dia preferido deve estar entre 1 e 31.")
    if current.month == 12:
        year, month = current.year + 1, 1
    else:
        year, month = current.year, current.month + 1
    return date(year, month, min(preferred_day, monthrange(year, month)[1]))


def generate_installment_dates(first_due: date, count: int) -> list[date]:
    if count <= 0:
        raise ValueError("A quantidade de parcelas deve ser maior que zero.")
    preferred_day = first_due.day
    result = [first_due]
    current = first_due
    for _ in range(1, count):
        current = next_monthly_date(current, preferred_day)
        result.append(current)
    return result


class SchedulingService:
    def __init__(self, connection: sqlite3.Connection, finance_service: FinancialService, repository: FinancialRepository):
        self.connection = connection
        self.finance_service = finance_service
        self.repository = repository

    def create_installments(self, base: CreateEntry, count: int) -> list[int]:
        if base.due_date is None:
            raise ValueError("Informe a primeira data de vencimento.")
        dates = generate_installment_dates(base.due_date, count)
        owns = not self.connection.in_transaction
        if owns:
            self.connection.execute("BEGIN IMMEDIATE")
        try:
            cursor = self.connection.execute("INSERT INTO installment_group(original_description, total_installments) VALUES (?, ?)", (base.description, count))
            group_id = int(cursor.lastrowid)
            commands = [replace(base, competence_date=due, due_date=due, installment_number=index, installment_total=count, installment_group_id=group_id, allow_duplicate=True) for index, due in enumerate(dates, start=1)]
            ids = self.finance_service.create_entries(commands)
            if owns:
                self.connection.commit()
            return ids
        except Exception:
            if owns and self.connection.in_transaction:
                self.connection.rollback()
            raise

    def create_monthly_recurrence(self, base: CreateEntry) -> int:
        if base.due_date is None:
            raise ValueError("Informe a primeira data de vencimento.")
        owns = not self.connection.in_transaction
        if owns:
            self.connection.execute("BEGIN IMMEDIATE")
        try:
            next_due = next_monthly_date(base.due_date, base.due_date.day)
            cursor = self.connection.execute("INSERT INTO recurrence_rule(preferred_day, next_due_date, active) VALUES (?, ?, 1)", (base.due_date.day, next_due.isoformat()))
            rule_id = int(cursor.lastrowid)
            command = replace(base, is_recurring=True, recurrence_rule_id=rule_id, allow_duplicate=True)
            entry_id = self.finance_service.create_entries([command])[0]
            if owns:
                self.connection.commit()
            return entry_id
        except Exception:
            if owns and self.connection.in_transaction:
                self.connection.rollback()
            raise

    def materialize_recurrences_until(self, until: date) -> list[int]:
        rules = self.connection.execute("SELECT id, preferred_day, next_due_date FROM recurrence_rule WHERE active=1 AND next_due_date IS NOT NULL AND next_due_date <= ? ORDER BY id", (until.isoformat(),)).fetchall()
        if not rules:
            return []
        owns = not self.connection.in_transaction
        if owns:
            self.connection.execute("BEGIN IMMEDIATE")
        try:
            created_ids = []
            for rule in rules:
                rule_id = int(rule["id"]); preferred_day = int(rule["preferred_day"])
                template = self.repository.first_for_recurrence_rule(rule_id)
                if template is None:
                    raise RuntimeError("Regra de recorrência sem lançamento modelo.")
                current = date.fromisoformat(rule["next_due_date"]); commands = []
                while current <= until:
                    commands.append(CreateEntry(description=template.description, amount_cents=template.amount_cents, entry_type=template.entry_type, status="PENDENTE", competence_date=current, due_date=current, payment_method=template.payment_method, notes=template.notes, is_recurring=True, recurrence_rule_id=rule_id, beneficiary_id=template.beneficiary_id, category_id=template.category_id, subcategory_id=template.subcategory_id, cost_center_id=template.cost_center_id, bank_account_id=template.bank_account_id, card_id=template.card_id, allow_duplicate=True))
                    current = next_monthly_date(current, preferred_day)
                if commands:
                    created_ids.extend(self.finance_service.create_entries(commands))
                self.connection.execute("UPDATE recurrence_rule SET next_due_date=?, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?", (current.isoformat(), rule_id))
            if owns:
                self.connection.commit()
            return created_ids
        except Exception:
            if owns and self.connection.in_transaction:
                self.connection.rollback()
            raise
