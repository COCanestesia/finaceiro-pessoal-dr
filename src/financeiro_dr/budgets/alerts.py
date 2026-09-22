from __future__ import annotations
from .models import BudgetAlert

class _Threshold:
    def __init__(self,level): self.level=level

def classify_budget_percent(percent:float):
    if percent > 100: return _Threshold("OVER")
    if percent >= 100: return _Threshold("LIMIT")
    if percent >= 80: return _Threshold("WARNING")
    return None

class BudgetAlertService:
    def __init__(self,budget_service): self.budget_service=budget_service
    def for_month(self,year:int,month:int)->list[BudgetAlert]:
        out=[]
        for snap in self.budget_service.month_summary(year,month):
            t=classify_budget_percent(snap.percent_used)
            if t: out.append(BudgetAlert(snap.id,t.level,snap.percent_used,snap.amount_cents,snap.spent_cents))
        return out
