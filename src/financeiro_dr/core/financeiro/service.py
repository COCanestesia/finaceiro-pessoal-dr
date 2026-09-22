from __future__ import annotations

from datetime import date
import sqlite3
import unicodedata
from financeiro_dr.audit.audit_service import AuditService
from financeiro_dr.core.financeiro.models import CreateEntry, ENTRY_STATUSES, ENTRY_TYPES, FinancialEntry
from financeiro_dr.core.financeiro.repository import FinancialRepository, MUTABLE_FIELDS

class EntryNotFoundError(RuntimeError): pass
class PossibleDuplicateError(RuntimeError): pass

def _normalize_description(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())

def _within_one_day(left: date | None, right: date | None) -> bool:
    return left is not None and right is not None and abs((left-right).days) <= 1

class FinancialService:
    def __init__(self, connection: sqlite3.Connection, repository: FinancialRepository | None=None, audit_service: AuditService | None=None):
        self.connection=connection; self.repository=repository or FinancialRepository(connection); self.audit_service=audit_service or AuditService(connection)
    def _validate_command(self, command: CreateEntry) -> None:
        if not command.description.strip(): raise ValueError("Informe a descrição do lançamento.")
        if command.amount_cents < 0: raise ValueError("O valor não pode ser negativo.")
        if command.entry_type not in ENTRY_TYPES: raise ValueError("Tipo de lançamento inválido.")
        if command.status not in ENTRY_STATUSES: raise ValueError("Status de lançamento inválido.")
    def _begin(self): self.connection.execute("BEGIN IMMEDIATE")
    def _rollback(self):
        if self.connection.in_transaction: self.connection.rollback()
    def create_entry(self, command: CreateEntry) -> int: return self.create_entries([command])[0]
    def create_entries(self, commands: list[CreateEntry]) -> list[int]:
        if not commands: return []
        for command in commands: self._validate_command(command)
        owns=not self.connection.in_transaction
        if owns: self._begin()
        try:
            ids=[]
            for command in commands:
                if not command.allow_duplicate and self.find_possible_duplicate(command) is not None: raise PossibleDuplicateError("Possível lançamento duplicado encontrado.")
                entry_id=self.repository.insert(command); snapshot=self.repository.snapshot(entry_id); assert snapshot is not None
                self.audit_service.record_create("financial_entry",entry_id,snapshot); ids.append(entry_id)
            if owns: self.connection.commit()
            return ids
        except Exception:
            if owns: self._rollback()
            raise
    def update_entry(self, entry_id:int, changes:dict)->None:
        unknown=set(changes)-MUTABLE_FIELDS
        if unknown: raise ValueError(f"Campo de lançamento não editável: {sorted(unknown)[0]}")
        if "amount_cents" in changes and int(changes["amount_cents"]) < 0: raise ValueError("O valor não pode ser negativo.")
        if "entry_type" in changes and changes["entry_type"] not in ENTRY_TYPES: raise ValueError("Tipo de lançamento inválido.")
        if "status" in changes and changes["status"] not in ENTRY_STATUSES: raise ValueError("Status de lançamento inválido.")
        self._begin()
        try:
            before=self.repository.snapshot(entry_id,False)
            if before is None: raise EntryNotFoundError("Lançamento não encontrado.")
            self.repository.update(entry_id,changes); after=self.repository.snapshot(entry_id,False); assert after is not None
            self.audit_service.record_update("financial_entry",entry_id,{k:before.get(k) for k in changes},{k:after.get(k) for k in changes}); self.connection.commit()
        except Exception: self._rollback(); raise
    def soft_delete(self, entry_id:int)->None:
        self._begin()
        try:
            before=self.repository.snapshot(entry_id,False)
            if before is None: raise EntryNotFoundError("Lançamento não encontrado.")
            self.repository.soft_delete(entry_id); self.audit_service.record_delete("financial_entry",entry_id,before); self.connection.commit()
        except Exception: self._rollback(); raise
    def find_possible_duplicate(self, command:CreateEntry)->FinancialEntry|None:
        normalized=_normalize_description(command.description)
        for candidate in self.repository.candidates_by_amount(command.amount_cents):
            if _normalize_description(candidate.description)!=normalized: continue
            if _within_one_day(candidate.competence_date,command.competence_date) or _within_one_day(candidate.due_date,command.due_date): return candidate
        return None
    def duplicate_entry(self, entry_id:int, due_date:date|None=None)->int:
        source=self.repository.get(entry_id)
        if source is None: raise EntryNotFoundError("Lançamento não encontrado.")
        command=CreateEntry(description=source.description,amount_cents=source.amount_cents,entry_type=source.entry_type,status=source.status,competence_date=source.competence_date,due_date=due_date if due_date is not None else source.due_date,settled_date=source.settled_date,payment_method=source.payment_method,notes=source.notes,is_recurring=source.is_recurring,installment_number=source.installment_number,installment_total=source.installment_total,recurrence_rule_id=source.recurrence_rule_id,installment_group_id=source.installment_group_id,beneficiary_id=source.beneficiary_id,category_id=source.category_id,subcategory_id=source.subcategory_id,cost_center_id=source.cost_center_id,bank_account_id=source.bank_account_id,card_id=source.card_id,allow_duplicate=True)
        return self.create_entry(command)
