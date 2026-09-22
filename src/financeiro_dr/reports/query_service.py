from __future__ import annotations
from datetime import date
import sqlite3
from financeiro_dr.budgets import BudgetService
from financeiro_dr.cards import invoice_due_date
from financeiro_dr.networth import NetWorthService
from .models import ReportFilters,ReportTable

class ReportQueryService:
    def __init__(self,connection:sqlite3.Connection):self.connection=connection
    def _filters(self,f:ReportFilters,alias='f',date_col='competence_date',with_dates=True):
        clauses=[];params=[]
        if with_dates:clauses += [f'{alias}.{date_col}>=?',f'{alias}.{date_col}<=?'];params += [f.start.isoformat(),f.end.isoformat()]
        mapping=[('beneficiary_id',f.person_id),('category_id',f.category_id),('subcategory_id',f.subcategory_id),('cost_center_id',f.cost_center_id),('bank_account_id',f.bank_account_id),('card_id',f.card_id),('status',f.status),('expense_nature',f.expense_nature),('income_source_id',f.income_source_id)]
        for col,val in mapping:
            if val is not None:clauses.append(f'{alias}.{col}=?');params.append(val)
        return clauses,params
    def _filter_text(self,f):return f'{f.start:%d/%m/%Y} a {f.end:%d/%m/%Y}'
    def _entries(self,f:ReportFilters,entry_type:str)->ReportTable:
        q="""SELECT f.id,f.competence_date,f.due_date,f.description,f.amount_cents,f.status,
        COALESCE(p.name,'') person,COALESCE(c.name,'') category,COALESCE(sc.name,'') subcategory,
        COALESCE(cc.name,'') cost_center,COALESCE(b.institution||' - '||b.name,'') bank,
        COALESCE(cr.issuer||' - '||COALESCE(cr.name,cr.holder),'') card,
        COALESCE(src.name,'') income_source,COALESCE(f.expense_nature,'') expense_nature
        FROM financial_entry f LEFT JOIN person p ON p.id=f.beneficiary_id LEFT JOIN category c ON c.id=f.category_id
        LEFT JOIN subcategory sc ON sc.id=f.subcategory_id LEFT JOIN cost_center cc ON cc.id=f.cost_center_id
        LEFT JOIN bank_account b ON b.id=f.bank_account_id LEFT JOIN credit_card cr ON cr.id=f.card_id
        LEFT JOIN income_source src ON src.id=f.income_source_id WHERE f.entry_type=? AND f.deleted_at IS NULL AND f.status<>'CANCELADO'""";params=[entry_type];clauses,p=self._filters(f);q+=' AND '+' AND '.join(clauses);params+=p;q+=' ORDER BY f.competence_date,f.id';found=list(self.connection.execute(q,params));rows=tuple((r['competence_date'],r['due_date'] or '',r['description'],r['person'],r['category'],r['subcategory'],r['cost_center'],r['bank'],r['card'],r['status'],r['expense_nature'] if entry_type=='DESPESA' else r['income_source'],r['amount_cents']/100) for r in found);title='Despesas' if entry_type=='DESPESA' else 'Receitas';return ReportTable(title,('Competência','Vencimento','Descrição','Pessoa','Categoria','Subcategoria','Centro de Custo','Conta','Cartão','Status','Natureza/Origem','Valor'),rows,sum(int(r['amount_cents']) for r in found),tuple(int(r['id']) for r in found),self._filter_text(f))
    def expenses(self,f):return self._entries(f,'DESPESA')
    def income(self,f):return self._entries(f,'RECEITA')
    def _expense_group(self,f:ReportFilters,title:str,join:str,label:str,group:str)->ReportTable:
        q=f"SELECT {label} label,SUM(f.amount_cents) total,GROUP_CONCAT(f.id) ids FROM financial_entry f {join} WHERE f.entry_type='DESPESA' AND f.deleted_at IS NULL AND f.status<>'CANCELADO'";clauses,p=self._filters(f);q+=' AND '+' AND '.join(clauses)+f' GROUP BY {group} ORDER BY total DESC';rows=list(self.connection.execute(q,p));ids=[]
        for r in rows:ids.extend(int(x) for x in (r['ids'] or '').split(',') if x)
        return ReportTable(title,('Grupo','Total'),tuple((r['label'] or 'Sem classificação',r['total']/100) for r in rows),sum(int(r['total']) for r in rows),tuple(ids),self._filter_text(f))
    def expenses_by_person(self,f):return self._expense_group(f,'Despesas por Pessoa','LEFT JOIN person p ON p.id=f.beneficiary_id',"COALESCE(p.name,'Dr./Sem pessoa')",'f.beneficiary_id')
    def expenses_by_category(self,f):return self._expense_group(f,'Despesas por Categoria','LEFT JOIN category c ON c.id=f.category_id',"COALESCE(c.name,'Sem categoria')",'f.category_id')
    def expenses_by_subcategory(self,f):return self._expense_group(f,'Despesas por Subcategoria','LEFT JOIN subcategory s ON s.id=f.subcategory_id',"COALESCE(s.name,'Sem subcategoria')",'f.subcategory_id')
    def expenses_by_cost_center(self,f):return self._expense_group(f,'Despesas por Centro de Custo','LEFT JOIN cost_center c ON c.id=f.cost_center_id',"COALESCE(c.name,'Sem centro')",'f.cost_center_id')
    def expenses_by_bank(self,f):return self._expense_group(f,'Despesas por Conta','LEFT JOIN bank_account b ON b.id=f.bank_account_id',"COALESCE(b.institution||' - '||b.name,'Sem conta')",'f.bank_account_id')
    def expenses_by_card(self,f):return self._expense_group(f,'Despesas por Cartão','LEFT JOIN credit_card c ON c.id=f.card_id',"COALESCE(c.issuer||' - '||COALESCE(c.name,c.holder),'Sem cartão')",'f.card_id')
    def expenses_by_status(self,f):return self._expense_group(f,'Pagas x Pendentes','',"f.status",'f.status')
    def fixed_vs_variable(self,f):return self._expense_group(f,'Despesas Fixas x Variáveis','',"COALESCE(f.expense_nature,'Sem classificação')",'f.expense_nature')
    def income_by_source(self,f:ReportFilters)->ReportTable:
        q="SELECT COALESCE(s.name,'Sem origem') label,SUM(f.amount_cents) total,GROUP_CONCAT(f.id) ids FROM financial_entry f LEFT JOIN income_source s ON s.id=f.income_source_id WHERE f.entry_type='RECEITA' AND f.deleted_at IS NULL AND f.status<>'CANCELADO'";clauses,p=self._filters(f);q+=' AND '+' AND '.join(clauses)+' GROUP BY f.income_source_id ORDER BY total DESC';rows=list(self.connection.execute(q,p));ids=[]
        for r in rows:ids.extend(int(x) for x in (r['ids'] or '').split(',') if x)
        return ReportTable('Receitas por Origem',('Origem','Total'),tuple((r['label'],r['total']/100) for r in rows),sum(int(r['total']) for r in rows),tuple(ids),self._filter_text(f))
    def cash_flow(self,f:ReportFilters)->ReportTable:
        q="SELECT f.id,f.competence_date,f.entry_type,f.description,f.amount_cents FROM financial_entry f WHERE f.deleted_at IS NULL AND f.status<>'CANCELADO' AND f.entry_type IN ('RECEITA','DESPESA')";clauses,p=self._filters(f);q+=' AND '+' AND '.join(clauses)+' ORDER BY f.competence_date,f.id';rows=list(self.connection.execute(q,p));out=tuple((r['competence_date'],r['entry_type'],r['description'],(r['amount_cents'] if r['entry_type']=='RECEITA' else -r['amount_cents'])/100) for r in rows);total=sum(r['amount_cents'] if r['entry_type']=='RECEITA' else -r['amount_cents'] for r in rows);return ReportTable('Fluxo de Caixa',('Data','Tipo','Descrição','Valor'),out,total,tuple(r['id'] for r in rows),self._filter_text(f))
    def _due(self,f:ReportFilters,kind:str,title:str)->ReportTable:
        q="SELECT f.id,f.due_date,f.description,f.status,f.amount_cents FROM financial_entry f WHERE f.entry_type=? AND f.due_date IS NOT NULL AND f.deleted_at IS NULL";params=[kind];clauses,p=self._filters(f,date_col='due_date');q+=' AND '+' AND '.join(clauses)+' ORDER BY f.due_date,f.id';params+=p;rows=list(self.connection.execute(q,params));return ReportTable(title,('Vencimento','Descrição','Status','Valor'),tuple((r['due_date'],r['description'],r['status'],r['amount_cents']/100) for r in rows),sum(int(r['amount_cents']) for r in rows),tuple(int(r['id']) for r in rows),self._filter_text(f))
    def payables(self,f):return self._due(f,'DESPESA','Contas a Pagar')
    def receivables(self,f):return self._due(f,'RECEITA','Contas a Receber')
    def budget_vs_actual(self,f:ReportFilters)->ReportTable:
        yms=f.start.year*100+f.start.month,f.end.year*100+f.end.month;q="SELECT b.*,COALESCE(p.name,'Todos') person,COALESCE(c.name,'Todas') category,COALESCE(cc.name,'Todos') cost FROM budget b LEFT JOIN person p ON p.id=b.person_id LEFT JOIN category c ON c.id=b.category_id LEFT JOIN cost_center cc ON cc.id=b.cost_center_id WHERE b.active=1 AND (b.year*100+b.month) BETWEEN ? AND ?";params=[*yms]
        for col,val in [('b.person_id',f.person_id),('b.category_id',f.category_id),('b.cost_center_id',f.cost_center_id)]:
            if val is not None:q+=f' AND {col}=?';params.append(val)
        budgets=list(self.connection.execute(q+' ORDER BY b.year,b.month,b.id',params));service=BudgetService(self.connection);rows=[];ids=[];total_plan=total_actual=0
        for b in budgets:
            snap=service.snapshot(int(b['id']));month=f"{b['year']:04d}-{b['month']:02d}";sql="SELECT id FROM financial_entry WHERE entry_type='DESPESA' AND status<>'CANCELADO' AND deleted_at IS NULL AND competence_date LIKE ?";ps=[month+'-%']
            for col,val in [('beneficiary_id',b['person_id']),('category_id',b['category_id']),('cost_center_id',b['cost_center_id'])]:
                if val is not None:sql+=f' AND {col}=?';ps.append(val)
            ids.extend(int(r[0]) for r in self.connection.execute(sql,ps));rows.append((month,b['person'],b['category'],b['cost'],snap.amount_cents/100,snap.spent_cents/100,snap.remaining_cents/100,f'{snap.percent_used:.1f}%'));total_plan+=snap.amount_cents;total_actual+=snap.spent_cents
        return ReportTable('Orçamento Previsto x Realizado',('Mês','Pessoa','Categoria','Centro','Previsto','Realizado','Saldo','Uso'),tuple(rows),total_actual,tuple(dict.fromkeys(ids)),self._filter_text(f)+f' | Previsto total R$ {total_plan/100:,.2f}')
    def reconciliation(self,f:ReportFilters)->ReportTable:
        rows=[];ids=[]
        bank=self.connection.execute("SELECT sr.*,b.institution||' - '||b.name account,COALESCE(rl.status,'PENDENTE') status,rl.entry_id,fe.amount_cents system_amount FROM statement_row sr JOIN bank_account b ON b.id=sr.account_id LEFT JOIN reconciliation_link rl ON rl.id=(SELECT id FROM reconciliation_link x WHERE x.statement_row_id=sr.id ORDER BY id DESC LIMIT 1) LEFT JOIN financial_entry fe ON fe.id=rl.entry_id WHERE sr.posted_date BETWEEN ? AND ? AND sr.ignored=0 ORDER BY sr.posted_date,sr.id",(f.start.isoformat(),f.end.isoformat())).fetchall()
        for r in bank:
            if f.status and r['status']!=f.status:continue
            system=int(r['system_amount'] or 0);diff=abs(int(r['amount_cents']))-system;rows.append(('Banco',r['account'],r['posted_date'],r['description'],r['amount_cents']/100,system/100,diff/100,r['status']));
            if r['entry_id']:ids.append(int(r['entry_id']))
        card=self.connection.execute("SELECT sr.*,c.issuer||' - '||COALESCE(c.name,c.holder) account,COALESCE(rl.status,'PENDENTE') status,rl.purchase_id,cp.total_cents system_amount FROM card_statement_row sr JOIN credit_card c ON c.id=sr.card_id LEFT JOIN card_reconciliation_link rl ON rl.id=(SELECT id FROM card_reconciliation_link x WHERE x.statement_row_id=sr.id ORDER BY id DESC LIMIT 1) LEFT JOIN card_purchase cp ON cp.id=rl.purchase_id WHERE sr.posted_date BETWEEN ? AND ? AND sr.ignored=0 ORDER BY sr.posted_date,sr.id",(f.start.isoformat(),f.end.isoformat())).fetchall()
        for r in card:
            if f.status and r['status']!=f.status:continue
            system=int(r['system_amount'] or 0);diff=abs(int(r['amount_cents']))-system;rows.append(('Cartão',r['account'],r['posted_date'],r['description'],r['amount_cents']/100,system/100,diff/100,r['status']));
            if r['purchase_id']:ids.extend(int(x[0]) for x in self.connection.execute('SELECT entry_id FROM card_installment WHERE purchase_id=?',(r['purchase_id'],)))
        return ReportTable('Conciliação Financeira',('Origem','Conta/Cartão','Data','Descrição','Extrato/Fatura','Sistema','Diferença','Status'),tuple(rows),None,tuple(dict.fromkeys(ids)),self._filter_text(f))
    def card_invoices(self,f:ReportFilters)->ReportTable:
        periods=self.connection.execute("SELECT c.id card_id,c.issuer,c.holder,c.name,c.closing_day,c.due_day,ci.invoice_year,ci.invoice_month,SUM(ci.amount_cents) total,GROUP_CONCAT(ci.entry_id) ids FROM card_installment ci JOIN card_purchase cp ON cp.id=ci.purchase_id JOIN credit_card c ON c.id=cp.card_id JOIN financial_entry fe ON fe.id=ci.entry_id WHERE fe.deleted_at IS NULL AND fe.status<>'CANCELADO' GROUP BY c.id,ci.invoice_year,ci.invoice_month ORDER BY ci.invoice_year,ci.invoice_month,c.id").fetchall();rows=[];ids=[];total=0
        for r in periods:
            if f.card_id is not None and int(r['card_id'])!=int(f.card_id):continue
            due=invoice_due_date(int(r['invoice_year']),int(r['invoice_month']),int(r['closing_day']),int(r['due_day']))
            if not(f.start<=due<=f.end):continue
            paid=int(self.connection.execute('SELECT COALESCE(SUM(amount_cents),0) FROM card_invoice_payment WHERE card_id=? AND invoice_year=? AND invoice_month=?',(r['card_id'],r['invoice_year'],r['invoice_month'])).fetchone()[0]);openv=int(r['total'])-paid;rows.append((f"{r['issuer']} - {r['name'] or r['holder']}",f"{r['invoice_month']:02d}/{r['invoice_year']}",due.isoformat(),r['total']/100,paid/100,openv/100,'PAGA' if openv<=0 else 'ABERTA'));ids.extend(int(x) for x in (r['ids'] or '').split(',') if x);total+=int(r['total'])
        return ReportTable('Faturas de Cartão',('Cartão','Fatura','Vencimento','Total','Pago','Aberto','Status'),tuple(rows),total,tuple(ids),self._filter_text(f))
    def monthly_evolution(self,f:ReportFilters)->ReportTable:
        q="SELECT substr(f.competence_date,1,7) month,SUM(CASE WHEN f.entry_type='RECEITA' THEN f.amount_cents ELSE 0 END) income,SUM(CASE WHEN f.entry_type='DESPESA' THEN f.amount_cents ELSE 0 END) expense,GROUP_CONCAT(f.id) ids FROM financial_entry f WHERE f.entry_type IN ('RECEITA','DESPESA') AND f.deleted_at IS NULL AND f.status<>'CANCELADO'";clauses,p=self._filters(f);q+=' AND '+' AND '.join(clauses)+' GROUP BY substr(f.competence_date,1,7) ORDER BY month';data=list(self.connection.execute(q,p));ids=[];rows=[]
        for r in data:ids.extend(int(x) for x in (r['ids'] or '').split(',') if x);rows.append((r['month'],r['income']/100,r['expense']/100,(r['income']-r['expense'])/100))
        return ReportTable('Evolução Mensal',('Mês','Receitas','Despesas','Resultado'),tuple(rows),None,tuple(ids),self._filter_text(f))
    def assets(self)->ReportTable:
        rows=self.connection.execute('SELECT asset_type,description,acquisition_value_cents,estimated_value_cents FROM asset WHERE active=1 ORDER BY asset_type,description').fetchall();return ReportTable('Patrimônio',('Tipo','Descrição','Aquisição','Valor Atual'),tuple((r['asset_type'],r['description'],r['acquisition_value_cents']/100,r['estimated_value_cents']/100) for r in rows),sum(r['estimated_value_cents'] for r in rows))
    def investments(self)->ReportTable:
        rows=self.connection.execute("SELECT ia.id,ia.institution,ia.account_name,ia.investment_type,COALESCE(SUM(CASE im.movement_type WHEN 'RESGATE' THEN -im.amount_cents ELSE im.amount_cents END),0) balance FROM investment_account ia LEFT JOIN investment_movement im ON im.investment_id=ia.id WHERE ia.active=1 GROUP BY ia.id ORDER BY ia.institution,ia.account_name").fetchall();return ReportTable('Investimentos',('Instituição','Aplicação','Tipo','Saldo'),tuple((r['institution'],r['account_name'],r['investment_type'],r['balance']/100) for r in rows),sum(r['balance'] for r in rows))
    def net_worth(self,at_date:date)->ReportTable:
        n=NetWorthService(self.connection).snapshot(at_date);rows=(('Saldos bancários',n.bank_balances_cents/100),('Investimentos',n.investments_cents/100),('Patrimônio',n.assets_cents/100),('Obrigações',-n.obligations_cents/100),('Patrimônio líquido',n.net_worth_cents/100));return ReportTable('Patrimônio Líquido',('Componente','Valor'),rows,n.net_worth_cents,(),f'Posição em {at_date:%d/%m/%Y}')
