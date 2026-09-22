from __future__ import annotations

from datetime import date
import sqlite3
from typing import Any
from financeiro_dr.core.financeiro.models import CreateEntry, FinancialEntry, MonthTotals

_INSERT_FIELDS = ("competence_date","due_date","settled_date","description","amount_cents","entry_type","status","payment_method","notes","is_recurring","installment_number","installment_total","recurrence_rule_id","installment_group_id","beneficiary_id","category_id","subcategory_id","cost_center_id","bank_account_id","card_id")
MUTABLE_FIELDS = set(_INSERT_FIELDS)

def _date_to_db(value: date | None) -> str | None:
    return value.isoformat() if isinstance(value, date) else value

def _row_to_entry(row: sqlite3.Row) -> FinancialEntry:
    def as_date(value: str | None) -> date | None:
        return date.fromisoformat(value) if value else None
    return FinancialEntry(id=row["id"], competence_date=date.fromisoformat(row["competence_date"]), due_date=as_date(row["due_date"]), settled_date=as_date(row["settled_date"]), description=row["description"], amount_cents=row["amount_cents"], entry_type=row["entry_type"], status=row["status"], payment_method=row["payment_method"], notes=row["notes"], is_recurring=bool(row["is_recurring"]), installment_number=row["installment_number"], installment_total=row["installment_total"], recurrence_rule_id=row["recurrence_rule_id"], installment_group_id=row["installment_group_id"], beneficiary_id=row["beneficiary_id"], category_id=row["category_id"], subcategory_id=row["subcategory_id"], cost_center_id=row["cost_center_id"], bank_account_id=row["bank_account_id"], card_id=row["card_id"], created_at=row["created_at"], updated_at=row["updated_at"], deleted_at=row["deleted_at"])

class FinancialRepository:
    def __init__(self, connection: sqlite3.Connection): self.connection = connection
    def insert(self, command: CreateEntry) -> int:
        values = {field: _date_to_db(getattr(command, field)) for field in _INSERT_FIELDS}; values["is_recurring"] = 1 if command.is_recurring else 0
        cursor = self.connection.execute(f"INSERT INTO financial_entry({', '.join(_INSERT_FIELDS)}) VALUES ({', '.join(':'+f for f in _INSERT_FIELDS)})", values)
        return int(cursor.lastrowid)
    def get(self, entry_id: int, include_deleted: bool=False) -> FinancialEntry | None:
        sql="SELECT * FROM financial_entry WHERE id=?" + ("" if include_deleted else " AND deleted_at IS NULL"); row=self.connection.execute(sql,(entry_id,)).fetchone(); return _row_to_entry(row) if row else None
    def first_for_recurrence_rule(self, rule_id: int) -> FinancialEntry | None:
        row=self.connection.execute("SELECT * FROM financial_entry WHERE recurrence_rule_id=? AND deleted_at IS NULL ORDER BY id LIMIT 1",(rule_id,)).fetchone(); return _row_to_entry(row) if row else None
    def snapshot(self, entry_id: int, include_deleted: bool=True) -> dict[str,Any] | None:
        sql="SELECT * FROM financial_entry WHERE id=?" + ("" if include_deleted else " AND deleted_at IS NULL"); row=self.connection.execute(sql,(entry_id,)).fetchone(); return dict(row) if row else None
    def update(self, entry_id: int, changes: dict[str,Any]) -> None:
        if not changes: return
        converted={}
        for key,value in changes.items():
            if key not in MUTABLE_FIELDS: raise ValueError(f"Campo de lançamento não editável: {key}")
            if isinstance(value,date): value=value.isoformat()
            if key=="is_recurring" and value is not None: value=1 if bool(value) else 0
            converted[key]=value
        setters=", ".join(f"{key} = :{key}" for key in converted); converted["entry_id"]=entry_id
        self.connection.execute(f"UPDATE financial_entry SET {setters}, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=:entry_id AND deleted_at IS NULL",converted)
    def soft_delete(self, entry_id:int)->None:
        self.connection.execute("UPDATE financial_entry SET deleted_at=strftime('%Y-%m-%dT%H:%M:%fZ','now'), updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=? AND deleted_at IS NULL",(entry_id,))
    def month_totals(self, year:int, month:int)->MonthTotals:
        row=self.connection.execute("SELECT COALESCE(SUM(CASE WHEN entry_type='RECEITA' THEN amount_cents ELSE 0 END),0), COALESCE(SUM(CASE WHEN entry_type='DESPESA' THEN amount_cents ELSE 0 END),0) FROM financial_entry WHERE competence_date LIKE ? AND deleted_at IS NULL AND status <> 'CANCELADO'",(f"{year:04d}-{month:02d}-%",)).fetchone(); return MonthTotals(int(row[0]),int(row[1]))
    def list_unsettled_due(self, entry_type:str, end_date:date|None=None)->list[FinancialEntry]:
        params=[entry_type]; sql="SELECT * FROM financial_entry WHERE entry_type=? AND due_date IS NOT NULL AND deleted_at IS NULL AND status IN ('PENDENTE','ATRASADO')"
        if end_date is not None: sql += " AND due_date <= ?"; params.append(end_date.isoformat())
        sql += " ORDER BY due_date, id"; return [_row_to_entry(r) for r in self.connection.execute(sql,params).fetchall()]
    def list_due_between(self,start_date:date,end_date:date)->list[FinancialEntry]:
        rows=self.connection.execute("SELECT * FROM financial_entry WHERE due_date BETWEEN ? AND ? AND deleted_at IS NULL AND status IN ('PENDENTE','ATRASADO') ORDER BY due_date,id",(start_date.isoformat(),end_date.isoformat())).fetchall(); return [_row_to_entry(r) for r in rows]
    def candidates_by_amount(self,amount_cents:int)->list[FinancialEntry]:
        rows=self.connection.execute("SELECT * FROM financial_entry WHERE amount_cents=? AND deleted_at IS NULL AND status <> 'CANCELADO' ORDER BY id",(amount_cents,)).fetchall(); return [_row_to_entry(r) for r in rows]
