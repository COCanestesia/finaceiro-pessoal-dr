from __future__ import annotations

from dataclasses import dataclass
from datetime import date

ENTRY_TYPES = {"RECEITA", "DESPESA", "TRANSFERENCIA", "INVESTIMENTO"}
ENTRY_STATUSES = {"PENDENTE", "PAGO", "RECEBIDO", "ATRASADO", "CANCELADO"}

@dataclass(frozen=True)
class CreateEntry:
    description: str
    amount_cents: int
    entry_type: str
    status: str
    competence_date: date
    due_date: date | None = None
    settled_date: date | None = None
    payment_method: str | None = None
    notes: str | None = None
    is_recurring: bool = False
    installment_number: int | None = None
    installment_total: int | None = None
    recurrence_rule_id: int | None = None
    installment_group_id: int | None = None
    beneficiary_id: int | None = None
    category_id: int | None = None
    subcategory_id: int | None = None
    cost_center_id: int | None = None
    bank_account_id: int | None = None
    card_id: int | None = None
    allow_duplicate: bool = False

@dataclass(frozen=True)
class FinancialEntry:
    id: int
    competence_date: date
    due_date: date | None
    settled_date: date | None
    description: str
    amount_cents: int
    entry_type: str
    status: str
    payment_method: str | None
    notes: str | None
    is_recurring: bool
    installment_number: int | None
    installment_total: int | None
    recurrence_rule_id: int | None
    installment_group_id: int | None
    beneficiary_id: int | None
    category_id: int | None
    subcategory_id: int | None
    cost_center_id: int | None
    bank_account_id: int | None
    card_id: int | None
    created_at: str
    updated_at: str
    deleted_at: str | None

@dataclass(frozen=True)
class MonthTotals:
    income_cents: int
    expense_cents: int
    @property
    def result_cents(self) -> int:
        return self.income_cents - self.expense_cents
