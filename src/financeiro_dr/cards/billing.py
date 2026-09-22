from calendar import monthrange
from datetime import date

def invoice_period_for(purchase_date:date,closing_day:int)->tuple[int,int]:
    if not 1<=closing_day<=31:raise ValueError('Dia de fechamento inválido.')
    if purchase_date.day<=closing_day:return purchase_date.year,purchase_date.month
    return (purchase_date.year+1,1) if purchase_date.month==12 else (purchase_date.year,purchase_date.month+1)
def next_period(year:int,month:int)->tuple[int,int]:return (year+1,1) if month==12 else (year,month+1)
def invoice_due_date(year:int,month:int,closing_day:int,due_day:int)->date:
    dy,dm=(year,month) if due_day>closing_day else next_period(year,month)
    return date(dy,dm,min(due_day,monthrange(dy,dm)[1]))
def split_cents(total:int,count:int)->list[int]:
    if total<=0 or count<=0:raise ValueError('Compra e parcelas devem ser maiores que zero.')
    base,extra=divmod(total,count);return [base+(1 if i<extra else 0) for i in range(count)]
