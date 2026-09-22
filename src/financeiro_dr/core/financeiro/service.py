from __future__ import annotations
from datetime import date
import sqlite3,unicodedata
from financeiro_dr.audit.audit_service import AuditService
from financeiro_dr.core.financeiro.models import CreateEntry,ENTRY_STATUSES,ENTRY_TYPES,EXPENSE_NATURES,FinancialEntry
from financeiro_dr.core.financeiro.repository import FinancialRepository,MUTABLE_FIELDS
class EntryNotFoundError(RuntimeError):pass
class PossibleDuplicateError(RuntimeError):pass
def _normalize_description(v:str)->str:return ' '.join(unicodedata.normalize('NFKC',v).casefold().split())
def _within_one_day(a,b):return a is not None and b is not None and abs((a-b).days)<=1
class FinancialService:
    def __init__(self,connection:sqlite3.Connection,repository:FinancialRepository|None=None,audit_service:AuditService|None=None):self.connection=connection;self.repository=repository or FinancialRepository(connection);self.audit_service=audit_service or AuditService(connection)
    def _exists_active(self,table,item_id):return item_id is None or self.connection.execute(f'SELECT 1 FROM {table} WHERE id=? AND active=1',(item_id,)).fetchone() is not None
    def _validate_command(self,c:CreateEntry)->None:
        if not c.description.strip():raise ValueError('Informe a descrição do lançamento.')
        if c.amount_cents<0:raise ValueError('O valor não pode ser negativo.')
        if c.entry_type not in ENTRY_TYPES:raise ValueError('Tipo de lançamento inválido.')
        if c.status not in ENTRY_STATUSES:raise ValueError('Status de lançamento inválido.')
        if c.entry_type=='DESPESA' and c.expense_nature not in EXPENSE_NATURES:raise ValueError('Informe se a despesa é Fixa ou Variável.')
        if c.beneficiary_id is not None and not self._exists_active('person',c.beneficiary_id):raise ValueError('Pessoa/beneficiário não encontrado ou inativo.')
        if c.category_id is not None and not self._exists_active('category',c.category_id):raise ValueError('Categoria não encontrada ou inativa.')
        if c.subcategory_id is not None:
            r=self.connection.execute('SELECT category_id,active FROM subcategory WHERE id=?',(c.subcategory_id,)).fetchone()
            if r is None or not r['active'] or c.category_id is None or r['category_id']!=c.category_id:raise ValueError('Subcategoria não pertence à categoria selecionada.')
        for table,item,msg in [('cost_center',c.cost_center_id,'Centro de custo'),('bank_account',c.bank_account_id,'Conta bancária'),('credit_card',c.card_id,'Cartão'),('asset',c.asset_id,'Patrimônio')]:
            if item is not None and not self._exists_active(table,item):raise ValueError(f'{msg} não encontrado ou inativo.')
        if c.income_source_id is not None and not self.connection.execute('SELECT 1 FROM income_source WHERE id=?',(c.income_source_id,)).fetchone():raise ValueError('Origem da receita não encontrada.')
    def _begin(self):self.connection.execute('BEGIN IMMEDIATE')
    def _rollback(self):
        if self.connection.in_transaction:self.connection.rollback()
    def create_entry(self,c:CreateEntry)->int:return self.create_entries([c])[0]
    def create_entries(self,commands:list[CreateEntry])->list[int]:
        if not commands:return []
        for c in commands:self._validate_command(c)
        owns=not self.connection.in_transaction
        if owns:self._begin()
        try:
            ids=[]
            for c in commands:
                if not c.allow_duplicate and self.find_possible_duplicate(c) is not None:raise PossibleDuplicateError('Possível lançamento duplicado encontrado.')
                eid=self.repository.insert(c);snap=self.repository.snapshot(eid);self.audit_service.record_create('financial_entry',eid,snap or {});ids.append(eid)
            if owns:self.connection.commit()
            return ids
        except Exception:
            if owns:self._rollback()
            raise
    def update_entry(self,entry_id:int,changes:dict)->None:
        unknown=set(changes)-MUTABLE_FIELDS
        if unknown:raise ValueError(f'Campo de lançamento não editável: {sorted(unknown)[0]}')
        self._begin()
        try:
            before=self.repository.snapshot(entry_id,False)
            if before is None:raise EntryNotFoundError('Lançamento não encontrado.')
            merged=dict(before);merged.update(changes)
            if merged.get('entry_type')=='DESPESA' and merged.get('expense_nature') not in EXPENSE_NATURES:raise ValueError('Informe se a despesa é Fixa ou Variável.')
            self.repository.update(entry_id,changes);after=self.repository.snapshot(entry_id,False);self.audit_service.record_update('financial_entry',entry_id,{k:before.get(k) for k in changes},{k:(after or {}).get(k) for k in changes});self.connection.commit()
        except Exception:self._rollback();raise
    def soft_delete(self,entry_id:int)->None:
        self._begin()
        try:
            before=self.repository.snapshot(entry_id,False)
            if before is None:raise EntryNotFoundError('Lançamento não encontrado.')
            self.repository.soft_delete(entry_id);self.audit_service.record_delete('financial_entry',entry_id,before);self.connection.commit()
        except Exception:self._rollback();raise
    def find_possible_duplicate(self,c:CreateEntry)->FinancialEntry|None:
        n=_normalize_description(c.description)
        for x in self.repository.candidates_by_amount(c.amount_cents):
            if _normalize_description(x.description)==n and (_within_one_day(x.competence_date,c.competence_date) or _within_one_day(x.due_date,c.due_date)):return x
        return None
    def duplicate_entry(self,entry_id:int,due_date:date|None=None)->int:
        s=self.repository.get(entry_id)
        if s is None:raise EntryNotFoundError('Lançamento não encontrado.')
        return self.create_entry(CreateEntry(description=s.description,amount_cents=s.amount_cents,entry_type=s.entry_type,status=s.status,competence_date=s.competence_date,due_date=due_date if due_date is not None else s.due_date,settled_date=s.settled_date,payment_method=s.payment_method,notes=s.notes,is_recurring=s.is_recurring,installment_number=s.installment_number,installment_total=s.installment_total,recurrence_rule_id=s.recurrence_rule_id,installment_group_id=s.installment_group_id,beneficiary_id=s.beneficiary_id,category_id=s.category_id,subcategory_id=s.subcategory_id,cost_center_id=s.cost_center_id,bank_account_id=s.bank_account_id,card_id=s.card_id,asset_id=s.asset_id,expense_nature=s.expense_nature,income_source_id=s.income_source_id,allow_duplicate=True))
