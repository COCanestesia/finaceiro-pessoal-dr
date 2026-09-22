from dataclasses import dataclass
from datetime import date
import sqlite3
@dataclass(frozen=True)
class ChartPoint:
    label:str;value_cents:int;entry_ids:tuple[int,...]
@dataclass(frozen=True)
class ChartData:
    title:str;points:tuple[ChartPoint,...]
class DashboardChartService:
    def __init__(self,connection:sqlite3.Connection):self.connection=connection
    def _group(self,year,month,join,label_expr,group_expr):
        rows=self.connection.execute(f"SELECT {label_expr} label,SUM(f.amount_cents) total,GROUP_CONCAT(f.id) ids FROM financial_entry f {join} WHERE f.entry_type='DESPESA' AND f.status<>'CANCELADO' AND f.deleted_at IS NULL AND f.competence_date LIKE ? GROUP BY {group_expr} ORDER BY total DESC",(f'{year:04d}-{month:02d}-%',)).fetchall();return tuple(ChartPoint(r['label'] or 'Sem classificação',int(r['total']),tuple(int(x) for x in (r['ids'] or '').split(',') if x)) for r in rows)
    def monthly_expense_by_category(self,year:int,month:int)->ChartData:return ChartData('Despesas por categoria',self._group(year,month,'LEFT JOIN category c ON c.id=f.category_id',"COALESCE(c.name,'Sem categoria')","f.category_id"))
    def monthly_expense_by_person(self,year:int,month:int)->ChartData:return ChartData('Despesas por pessoa',self._group(year,month,'LEFT JOIN person p ON p.id=f.beneficiary_id',"COALESCE(p.name,'Dr.')","f.beneficiary_id"))
    def cash_flow_6_months(self,end_month:date)->ChartData:
        points=[];y=end_month.year;m=end_month.month
        months=[]
        for _ in range(6):months.append((y,m));m-=1; y-=1 if m==0 else 0; m=12 if m==0 else m
        for y,m in reversed(months):
            rows=self.connection.execute("SELECT id,entry_type,amount_cents FROM financial_entry WHERE competence_date LIKE ? AND deleted_at IS NULL AND status<>'CANCELADO'",(f'{y:04d}-{m:02d}-%',)).fetchall();value=sum((r['amount_cents'] if r['entry_type']=='RECEITA' else -r['amount_cents'] if r['entry_type']=='DESPESA' else 0) for r in rows);points.append(ChartPoint(f'{m:02d}/{y}',value,tuple(r['id'] for r in rows)))
        return ChartData('Fluxo de caixa - 6 meses',tuple(points))
