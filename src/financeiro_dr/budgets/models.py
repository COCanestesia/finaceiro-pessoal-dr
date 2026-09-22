from dataclasses import dataclass

@dataclass(frozen=True)
class BudgetSnapshot:
    id:int; year:int; month:int; amount_cents:int; person_id:int|None; category_id:int|None; cost_center_id:int|None; spent_cents:int
    @property
    def remaining_cents(self)->int: return self.amount_cents-self.spent_cents
    @property
    def percent_used(self)->float: return 0.0 if self.amount_cents == 0 else self.spent_cents*100.0/self.amount_cents

@dataclass(frozen=True)
class BudgetAlert:
    budget_id:int; level:str; percent:float; amount_cents:int; spent_cents:int
