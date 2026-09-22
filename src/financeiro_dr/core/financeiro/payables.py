from __future__ import annotations
from dataclasses import dataclass
from datetime import date,timedelta
from financeiro_dr.core.financeiro.models import FinancialEntry
from financeiro_dr.core.financeiro.repository import FinancialRepository
from financeiro_dr.core.financeiro.service import EntryNotFoundError,FinancialService

@dataclass(frozen=True)
class PayableBuckets:
    overdue: tuple[FinancialEntry,...]; today: tuple[FinancialEntry,...]; tomorrow: tuple[FinancialEntry,...]; next_7_days: tuple[FinancialEntry,...]; next_30_days: tuple[FinancialEntry,...]

def _bucket(entries:list[FinancialEntry], today:date)->PayableBuckets:
    overdue=[]; today_items=[]; tomorrow=[]; next_7=[]; next_30=[]
    for entry in entries:
        if entry.due_date is None: continue
        delta=(entry.due_date-today).days
        if delta<0: overdue.append(entry)
        elif delta==0: today_items.append(entry)
        elif delta==1: tomorrow.append(entry)
        elif 2<=delta<=7: next_7.append(entry)
        elif 8<=delta<=30: next_30.append(entry)
    return PayableBuckets(tuple(overdue),tuple(today_items),tuple(tomorrow),tuple(next_7),tuple(next_30))

class PayablesService:
    def __init__(self,repository:FinancialRepository,finance_service:FinancialService): self.repository=repository; self.finance_service=finance_service
    def buckets(self,today:date)->PayableBuckets: return _bucket(self.repository.list_unsettled_due("DESPESA",today+timedelta(days=30)),today)
    def receivable_buckets(self,today:date)->PayableBuckets: return _bucket(self.repository.list_unsettled_due("RECEITA",today+timedelta(days=30)),today)
    def settle(self,entry_id:int,settled_date:date)->None:
        entry=self.repository.get(entry_id)
        if entry is None: raise EntryNotFoundError("Lançamento não encontrado.")
        if entry.entry_type=="DESPESA": status="PAGO"
        elif entry.entry_type=="RECEITA": status="RECEBIDO"
        else: raise ValueError("Somente receitas e despesas podem ser baixadas por esta tela.")
        self.finance_service.update_entry(entry_id,{"status":status,"settled_date":settled_date})
