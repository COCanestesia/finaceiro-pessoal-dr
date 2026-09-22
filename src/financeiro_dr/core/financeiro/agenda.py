from __future__ import annotations
from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from financeiro_dr.core.financeiro.repository import FinancialRepository

@dataclass(frozen=True)
class AgendaDay:
    day:date; pay_cents:int; receive_cents:int; entry_ids:tuple[int,...]

class AgendaService:
    def __init__(self,repository:FinancialRepository): self.repository=repository
    def month(self,year:int,month:int)->list[AgendaDay]:
        entries=self.repository.list_due_between(date(year,month,1),date(year,month,monthrange(year,month)[1])); grouped={}
        for entry in entries:
            if entry.due_date is None or entry.entry_type not in {"DESPESA","RECEITA"}: continue
            item=grouped.setdefault(entry.due_date,{"pay":0,"receive":0,"ids":[]})
            if entry.entry_type=="DESPESA": item["pay"]+=entry.amount_cents
            else: item["receive"]+=entry.amount_cents
            item["ids"].append(entry.id)
        return [AgendaDay(day,int(v["pay"]),int(v["receive"]),tuple(v["ids"])) for day,v in sorted(grouped.items())]
