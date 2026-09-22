from __future__ import annotations
from datetime import date
import sqlite3
from .models import ReportFilters,ReportTable

class ReportQueryService:
    def __init__(self,connection:sqlite3.Connection):self.connection=connection
    def _entries(self,filters:ReportFilters,entry_type:str)->ReportTable:
        q="""SELECT f.id,f.competence_date,f.due_date,f.description,f.amount_cents,f.status,
        COALESCE(p.name,'') person,COALESCE(c.name,'') category,COALESCE(sc.name,'') subcategory,
        COALESCE(cc.name,'') cost_center,COALESCE(b.institution||' - '||b.name,'') bank,
        COALESCE(cr.issuer||' - '||COALESCE(cr.name,cr.holder),'') card,
        COALESCE(src.name,'') income_source,COALESCE(f.expense_nature,'') expense_nature
        FROM financial_entry f LEFT JOIN person p ON p.id=f.beneficiary_id LEFT JOIN category c ON c.id=f.category_id
        LEFT JOIN subcategory sc ON sc.id=f.subcategory_id LEFT JOIN cost_center cc ON cc.id=f.cost_center_id
        LEFT JOIN bank_account b ON b.id=f.bank_account_id LEFT JOIN credit_card cr ON cr.id=f.card_id
        LEFT JOIN income_source src ON src.id=f.income_source_id
        WHERE f.entry_type=? AND f.competence_date BETWEEN ? AND ? AND f.deleted_at IS NULL AND f.status<>'CANCELADO'"""
        params=[entry_type,filters.start.isoformat(),filters.end.isoformat()]
        mapping=[('f.beneficiary_id',filters.person_id),('f.category_id',filters.category_id),('f.subcategory_id',filters.subcategory_id),('f.cost_center_id',filters.cost_center_id),('f.bank_account_id',filters.bank_account_id),('f.card_id',filters.card_id),('f.status',filters.status),('f.expense_nature',filters.expense_nature),('f.income_source_id',filters.income_source_id)]
        for col,val in mapping:
            if val is not None:q+=f' AND {col}=?';params.append(val)
        q+=' ORDER BY f.competence_date,f.id'
        found=list(self.connection.execute(q,params)); rows=tuple((r['competence_date'],r['due_date'] or '',r['description'],r['person'],r['category'],r['subcategory'],r['cost_center'],r['bank'],r['card'],r['status'],r['expense_nature'] if entry_type=='DESPESA' else r['income_source'],r['amount_cents']/100) for r in found)
        title='Despesas' if entry_type=='DESPESA' else 'Receitas'; return ReportTable(title,('Competência','Vencimento','Descrição','Pessoa','Categoria','Subcategoria','Centro de Custo','Conta','Cartão','Status','Natureza/Origem','Valor'),rows,sum(int(r['amount_cents']) for r in found),tuple(int(r['id']) for r in found),f'{filters.start:%d/%m/%Y} a {filters.end:%d/%m/%Y}')
    def expenses(self,filters):return self._entries(filters,'DESPESA')
    def income(self,filters):return self._entries(filters,'RECEITA')
    def cash_flow(self,filters:ReportFilters)->ReportTable:
        rows=self.connection.execute("SELECT competence_date,entry_type,description,amount_cents,id FROM financial_entry WHERE competence_date BETWEEN ? AND ? AND deleted_at IS NULL AND status<>'CANCELADO' AND entry_type IN ('RECEITA','DESPESA') ORDER BY competence_date,id",(filters.start.isoformat(),filters.end.isoformat())).fetchall(); out=tuple((r['competence_date'],r['entry_type'],r['description'],(r['amount_cents'] if r['entry_type']=='RECEITA' else -r['amount_cents'])/100) for r in rows); total=sum(r['amount_cents'] if r['entry_type']=='RECEITA' else -r['amount_cents'] for r in rows);return ReportTable('Fluxo de Caixa',('Data','Tipo','Descrição','Valor'),out,total,tuple(r['id'] for r in rows),f'{filters.start:%d/%m/%Y} a {filters.end:%d/%m/%Y}')
    def fixed_vs_variable(self,filters:ReportFilters)->ReportTable:
        rows=self.connection.execute("SELECT COALESCE(expense_nature,'SEM CLASSIFICAÇÃO') label,SUM(amount_cents) total,GROUP_CONCAT(id) ids FROM financial_entry WHERE entry_type='DESPESA' AND competence_date BETWEEN ? AND ? AND deleted_at IS NULL AND status<>'CANCELADO' GROUP BY expense_nature ORDER BY total DESC",(filters.start.isoformat(),filters.end.isoformat())).fetchall(); ids=[]
        for r in rows:ids.extend(int(x) for x in (r['ids'] or '').split(',') if x)
        return ReportTable('Despesas Fixas x Variáveis',('Natureza','Total'),tuple((r['label'],r['total']/100) for r in rows),sum(int(r['total']) for r in rows),tuple(ids),f'{filters.start:%d/%m/%Y} a {filters.end:%d/%m/%Y}')
    def income_by_source(self,filters:ReportFilters)->ReportTable:
        rows=self.connection.execute("SELECT COALESCE(s.name,'Sem origem') label,SUM(f.amount_cents) total,GROUP_CONCAT(f.id) ids FROM financial_entry f LEFT JOIN income_source s ON s.id=f.income_source_id WHERE f.entry_type='RECEITA' AND f.competence_date BETWEEN ? AND ? AND f.deleted_at IS NULL AND f.status<>'CANCELADO' GROUP BY f.income_source_id ORDER BY total DESC",(filters.start.isoformat(),filters.end.isoformat())).fetchall();ids=[]
        for r in rows:ids.extend(int(x) for x in (r['ids'] or '').split(',') if x)
        return ReportTable('Receitas por Origem',('Origem','Total'),tuple((r['label'],r['total']/100) for r in rows),sum(int(r['total']) for r in rows),tuple(ids),f'{filters.start:%d/%m/%Y} a {filters.end:%d/%m/%Y}')
    def payables(self,filters:ReportFilters)->ReportTable:
        rows=self.connection.execute("SELECT id,due_date,description,status,amount_cents FROM financial_entry WHERE entry_type='DESPESA' AND due_date BETWEEN ? AND ? AND status IN ('PENDENTE','ATRASADO') AND deleted_at IS NULL ORDER BY due_date",(filters.start.isoformat(),filters.end.isoformat())).fetchall();return ReportTable('Contas a Pagar',('Vencimento','Descrição','Status','Valor'),tuple((r['due_date'],r['description'],r['status'],r['amount_cents']/100) for r in rows),sum(r['amount_cents'] for r in rows),tuple(r['id'] for r in rows))
    def receivables(self,filters:ReportFilters)->ReportTable:
        rows=self.connection.execute("SELECT id,due_date,description,status,amount_cents FROM financial_entry WHERE entry_type='RECEITA' AND due_date BETWEEN ? AND ? AND status IN ('PENDENTE','ATRASADO') AND deleted_at IS NULL ORDER BY due_date",(filters.start.isoformat(),filters.end.isoformat())).fetchall();return ReportTable('Contas a Receber',('Vencimento','Descrição','Status','Valor'),tuple((r['due_date'],r['description'],r['status'],r['amount_cents']/100) for r in rows),sum(r['amount_cents'] for r in rows),tuple(r['id'] for r in rows))
    def assets(self)->ReportTable:
        rows=self.connection.execute('SELECT asset_type,description,acquisition_value_cents,estimated_value_cents FROM asset WHERE active=1 ORDER BY asset_type,description').fetchall();return ReportTable('Patrimônio',('Tipo','Descrição','Aquisição','Valor Atual'),tuple((r['asset_type'],r['description'],r['acquisition_value_cents']/100,r['estimated_value_cents']/100) for r in rows),sum(r['estimated_value_cents'] for r in rows))
    def investments(self)->ReportTable:
        rows=self.connection.execute("SELECT ia.id,ia.institution,ia.account_name,ia.investment_type,COALESCE(SUM(CASE im.movement_type WHEN 'RESGATE' THEN -im.amount_cents ELSE im.amount_cents END),0) balance FROM investment_account ia LEFT JOIN investment_movement im ON im.investment_id=ia.id WHERE ia.active=1 GROUP BY ia.id ORDER BY ia.institution,ia.account_name").fetchall();return ReportTable('Investimentos',('Instituição','Aplicação','Tipo','Saldo'),tuple((r['institution'],r['account_name'],r['investment_type'],r['balance']/100) for r in rows),sum(r['balance'] for r in rows))
