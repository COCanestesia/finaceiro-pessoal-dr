from dataclasses import dataclass
from datetime import date
@dataclass(frozen=True)
class ReportFilters:
    start:date
    end:date
    person_id:int|None=None
    category_id:int|None=None
    subcategory_id:int|None=None
    cost_center_id:int|None=None
    bank_account_id:int|None=None
    card_id:int|None=None
    status:str|None=None
    expense_nature:str|None=None
    income_source_id:int|None=None
@dataclass(frozen=True)
class ReportTable:
    title:str
    columns:tuple[str,...]
    rows:tuple[tuple[object,...],...]
    total_cents:int|None
    detail_entry_ids:tuple[int,...]=()
    filters_text:str=''
