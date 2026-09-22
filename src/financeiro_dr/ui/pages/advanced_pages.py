from __future__ import annotations
from datetime import date
from pathlib import Path
import sqlite3
from PySide6.QtCore import QDate,QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QComboBox,QDateEdit,QDialog,QFileDialog,QFormLayout,QHBoxLayout,QHeaderView,QInputDialog,QLabel,QLineEdit,QMessageBox,QPushButton,QSpinBox,QTableWidget,QTableWidgetItem,QVBoxLayout,QWidget
from financeiro_dr.cards import CardService
from financeiro_dr.documents import DocumentFilters,DocumentService
from financeiro_dr.reconciliation import ImportService,ReconciliationService,CardStatementImportService,CardReconciliationService
from financeiro_dr.reports import ReportFilters,ReportQueryService,export_pdf,export_xlsx
from financeiro_dr.ui.widgets.money_edit import MoneyEdit

def _title(l,t):x=QLabel(t);x.setStyleSheet('font-size:24px;font-weight:700;');l.addWidget(x)
def _fill(t,headers,rows):
    t.clear();t.setColumnCount(len(headers));t.setHorizontalHeaderLabels(headers);t.setRowCount(len(rows))
    for i,row in enumerate(rows):
        for j,v in enumerate(row):t.setItem(i,j,QTableWidgetItem('' if v is None else str(v)))
    t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents);t.horizontalHeader().setStretchLastSection(True)
def _combo(c,rows,label,optional=True):
    c.clear()
    if optional:c.addItem('Todos / Não informado',None)
    for r in rows:c.addItem(label(r),r['id'])
def _d(w):q=w.date();return date(q.year(),q.month(),q.day())

class AdvancedCardsPage(QWidget):
    def __init__(self,connection:sqlite3.Connection,parent=None):
        super().__init__(parent);self.connection=connection;self.service=CardService(connection);l=QVBoxLayout(self);_title(l,'Cartões de Crédito');form=QFormLayout();self.issuer=QLineEdit();self.holder=QLineEdit();self.name=QLineEdit();self.limit=MoneyEdit();self.close=QSpinBox();self.close.setRange(1,31);self.close.setValue(10);self.due=QSpinBox();self.due.setRange(1,31);self.due.setValue(20)
        for label,w in [('Banco/Emissor:',self.issuer),('Titular:',self.holder),('Nome:',self.name),('Limite:',self.limit),('Dia de fechamento:',self.close),('Dia de vencimento:',self.due)]:form.addRow(label,w)
        b=QPushButton('Cadastrar cartão');b.clicked.connect(self.add_card);form.addRow('',b);l.addLayout(form);bar=QHBoxLayout();self.card=QComboBox();self.card.currentIndexChanged.connect(self.refresh_invoices);bar.addWidget(QLabel('Cartão:'));bar.addWidget(self.card);l.addLayout(bar);self.cards_table=QTableWidget();l.addWidget(self.cards_table)
        pf=QFormLayout();self.pdesc=QLineEdit();self.pamount=MoneyEdit();self.pinstall=QSpinBox();self.pinstall.setRange(1,60);self.pdate=QDateEdit(QDate.currentDate());self.person=QComboBox();self.category=QComboBox();self.subcategory=QComboBox();self.cost=QComboBox();self.category.currentIndexChanged.connect(self.load_subcategories)
        for label,w in [('Compra:',self.pdesc),('Valor total:',self.pamount),('Parcelas:',self.pinstall),('Data:',self.pdate),('Pessoa:',self.person),('Categoria:',self.category),('Subcategoria:',self.subcategory),('Centro de custo:',self.cost)]:pf.addRow(label,w)
        bp=QPushButton('Adicionar compra');bp.clicked.connect(self.add_purchase);pf.addRow('',bp);l.addLayout(pf);l.addWidget(QLabel('Fatura atual e próximas faturas'));self.invoice_table=QTableWidget();l.addWidget(self.invoice_table);pay=QHBoxLayout();self.bank=QComboBox();btn=QPushButton('Pagar fatura selecionada');btn.clicked.connect(self.pay_invoice);pay.addWidget(QLabel('Pagar pela conta:'));pay.addWidget(self.bank);pay.addWidget(btn);l.addLayout(pay);self.refresh()
    def add_card(self):
        try:self.service.create_card(self.issuer.text(),self.holder.text(),self.limit.cents(),self.close.value(),self.due.value(),self.name.text() or None);self.refresh()
        except Exception as e:QMessageBox.warning(self,'Cartões',str(e))
    def add_purchase(self):
        try:self.service.add_purchase(self.card.currentData(),_d(self.pdate),self.pdesc.text(),self.pamount.cents(),self.pinstall.value(),self.person.currentData(),self.category.currentData(),self.subcategory.currentData(),self.cost.currentData());self.pdesc.clear();self.pamount.clear();self.refresh()
        except Exception as e:QMessageBox.warning(self,'Compra',str(e))
    def pay_invoice(self):
        row=self.invoice_table.currentRow()
        if row<0:return
        try:
            year=int(self.invoice_table.item(row,6).text());month=int(self.invoice_table.item(row,7).text());self.service.pay_invoice(self.card.currentData(),year,month,self.bank.currentData(),date.today());self.refresh()
        except Exception as e:QMessageBox.warning(self,'Fatura',str(e))
    def load_subcategories(self):
        self.subcategory.clear();self.subcategory.addItem('Não informado',None);cid=self.category.currentData()
        if cid:
            for r in self.connection.execute('SELECT id,name FROM subcategory WHERE category_id=? AND active=1 ORDER BY name',(cid,)):self.subcategory.addItem(r['name'],r['id'])
    def refresh_invoices(self):
        cid=self.card.currentData()
        if cid is None:_fill(self.invoice_table,['Fatura','Vencimento','Total','Pago','Aberto','Status','Ano','Mês'],[]);return
        invs=self.service.list_invoices(cid,True);_fill(self.invoice_table,['Fatura','Vencimento','Total','Pago','Aberto','Status','Ano','Mês'],[(f'{i.month:02d}/{i.year}',i.due_date.isoformat(),i.total_cents/100,i.paid_cents/100,i.open_cents/100,'PAGA' if i.open_cents<=0 else 'ABERTA',i.year,i.month) for i in invs])
    def refresh(self):
        rows=list(self.connection.execute('SELECT * FROM credit_card ORDER BY active DESC,issuer,holder'));current=self.card.currentData();_combo(self.card,[r for r in rows if r['active']],lambda r:f"{r['issuer']} - {r['name'] or r['holder']}",False)
        if current is not None:
            idx=self.card.findData(current)
            if idx>=0:self.card.setCurrentIndex(idx)
        out=[]
        for r in rows:
            used=self.service.used_limit_cents(r['id']);pct=0 if not r['limit_cents'] else used*100/r['limit_cents'];out.append((r['id'],r['issuer'],r['name'] or r['holder'],r['limit_cents']/100,used/100,(r['limit_cents']-used)/100,f'{pct:.1f}%',r['closing_day'],r['due_day'],'ATENÇÃO' if pct>=85 else 'OK'))
        _fill(self.cards_table,['ID','Emissor','Cartão','Limite','Usado','Disponível','Uso','Fecha','Vence','Alerta'],out);_combo(self.bank,list(self.connection.execute('SELECT id,institution,name FROM bank_account WHERE active=1 ORDER BY institution,name')),lambda r:f"{r['institution']} - {r['name']}",False);_combo(self.person,list(self.connection.execute('SELECT id,name FROM person WHERE active=1 ORDER BY name')),lambda r:r['name']);_combo(self.category,list(self.connection.execute('SELECT id,name FROM category WHERE active=1 ORDER BY name')),lambda r:r['name']);_combo(self.cost,list(self.connection.execute('SELECT id,name FROM cost_center WHERE active=1 ORDER BY name')),lambda r:r['name']);self.load_subcategories();self.refresh_invoices()

class AdvancedReconciliationPage(QWidget):
    def __init__(self,connection:sqlite3.Connection,parent=None):
        super().__init__(parent);self.connection=connection;self.bank_import=ImportService(connection);self.bank_service=ReconciliationService(connection);self.card_import=CardStatementImportService(connection);self.card_service=CardReconciliationService(connection);l=QVBoxLayout(self);_title(l,'Conciliação Financeira');bar=QHBoxLayout();self.mode=QComboBox();self.mode.addItem('Banco','bank');self.mode.addItem('Cartão','card');self.source=QComboBox();self.status=QComboBox();[(self.status.addItem(a,b)) for a,b in [('Todos',None),('Pendente','PENDENTE'),('Conciliado','CONCILIADO'),('Divergente','DIVERGENTE')]];self.mode.currentIndexChanged.connect(self.load_sources);self.status.currentIndexChanged.connect(self.refresh);bi=QPushButton('Importar OFX / CSV / Excel');bi.clicked.connect(self.import_file);bc=QPushButton('Confirmar melhor');bc.clicked.connect(self.confirm);bo=QPushButton('Escolher outro');bo.clicked.connect(self.choose_other);bd=QPushButton('Marcar divergente');bd.clicked.connect(self.divergent);bg=QPushButton('Ignorar');bg.clicked.connect(self.ignore)
        for w in (QLabel('Origem:'),self.mode,self.source,QLabel('Status:'),self.status,bi,bc,bo,bd,bg):bar.addWidget(w);l.addLayout(bar);self.table=QTableWidget();l.addWidget(self.table,1);self.load_sources()
    def load_sources(self):
        if self.mode.currentData()=='bank':_combo(self.source,list(self.connection.execute('SELECT id,institution,name FROM bank_account WHERE active=1 ORDER BY institution,name')),lambda r:f"{r['institution']} - {r['name']}",False)
        else:_combo(self.source,list(self.connection.execute('SELECT id,issuer,holder,name FROM credit_card WHERE active=1 ORDER BY issuer,holder')),lambda r:f"{r['issuer']} - {r['name'] or r['holder']}",False)
        self.refresh()
    def import_file(self):
        path,_=QFileDialog.getOpenFileName(self,'Importar extrato/fatura','','Arquivos (*.ofx *.qfx *.csv *.xlsx *.xlsm)')
        if not path:return
        try:
            svc=self.bank_import if self.mode.currentData()=='bank' else self.card_import;r=svc.import_file(self.source.currentData(),Path(path));QMessageBox.information(self,'Importação',f'{r.created} novos; {r.duplicates} duplicados.');self.refresh()
        except Exception as e:QMessageBox.warning(self,'Importação',str(e))
    def _id(self):
        row=self.table.currentRow();return int(self.table.item(row,0).text()) if row>=0 else None
    def _suggest(self,rid):return (self.bank_service if self.mode.currentData()=='bank' else self.card_service).suggest(rid)
    def confirm(self):
        rid=self._id()
        if rid is None:return
        try:
            result=self._suggest(rid)
            if not result.candidates:raise ValueError('Nenhum candidato encontrado.')
            candidate=result.candidates[0];svc=self.bank_service if self.mode.currentData()=='bank' else self.card_service;svc.confirm(rid,candidate.entry_id if hasattr(candidate,'entry_id') else candidate.purchase_id);self.refresh()
        except Exception as e:QMessageBox.warning(self,'Conciliação',str(e))
    def choose_other(self):
        rid=self._id()
        if rid is None:return
        try:
            result=self._suggest(rid);items=[];ids=[]
            for c in result.candidates:
                ident=c.entry_id if hasattr(c,'entry_id') else c.purchase_id;items.append(f'#{ident} — score {c.score}');ids.append(ident)
            if not items:raise ValueError('Nenhum candidato encontrado.')
            text,ok=QInputDialog.getItem(self,'Escolher candidato','Lançamento/Compra:',items,0,False)
            if ok:
                idx=items.index(text);svc=self.bank_service if self.mode.currentData()=='bank' else self.card_service;svc.confirm(rid,ids[idx]);self.refresh()
        except Exception as e:QMessageBox.warning(self,'Conciliação',str(e))
    def divergent(self):
        rid=self._id()
        if rid is None:return
        (self.bank_service if self.mode.currentData()=='bank' else self.card_service).mark_divergent(rid,'Marcado manualmente');self.refresh()
    def ignore(self):
        rid=self._id()
        if rid is None:return
        (self.bank_service if self.mode.currentData()=='bank' else self.card_service).ignore(rid);self.refresh()
    def refresh(self):
        if not hasattr(self,'table'):return
        wanted=self.status.currentData();rows=[]
        if self.mode.currentData()=='bank':
            data=self.connection.execute("SELECT sr.*,COALESCE((SELECT status FROM reconciliation_link x WHERE x.statement_row_id=sr.id ORDER BY id DESC LIMIT 1),'PENDENTE') status FROM statement_row sr WHERE sr.ignored=0 ORDER BY posted_date DESC,id DESC").fetchall()
            for r in data:
                if wanted and r['status']!=wanted:continue
                result=self.bank_service.suggest(r['id']);best=result.candidates[0] if result.candidates else None;entry=self.connection.execute('SELECT description,amount_cents FROM financial_entry WHERE id=?',(best.entry_id,)).fetchone() if best else None;system=entry['amount_cents'] if entry else 0;rows.append((r['id'],r['posted_date'],r['description'],r['amount_cents']/100,(entry['description'] if entry else ''),system/100,(abs(r['amount_cents'])-system)/100,(best.score if best else ''),r['status']))
        else:
            data=self.connection.execute("SELECT sr.*,COALESCE((SELECT status FROM card_reconciliation_link x WHERE x.statement_row_id=sr.id ORDER BY id DESC LIMIT 1),'PENDENTE') status FROM card_statement_row sr WHERE sr.ignored=0 ORDER BY posted_date DESC,id DESC").fetchall()
            for r in data:
                if wanted and r['status']!=wanted:continue
                result=self.card_service.suggest(r['id']);best=result.candidates[0] if result.candidates else None;p=self.connection.execute('SELECT description,total_cents FROM card_purchase WHERE id=?',(best.purchase_id,)).fetchone() if best else None;system=p['total_cents'] if p else 0;rows.append((r['id'],r['posted_date'],r['description'],r['amount_cents']/100,(p['description'] if p else ''),system/100,(abs(r['amount_cents'])-system)/100,(best.score if best else ''),r['status']))
        _fill(self.table,['ID','Data','Extrato/Fatura','Valor','Candidato','Valor sistema','Diferença','Score','Status'],rows)

class AdvancedDocumentsPage(QWidget):
    def __init__(self,connection:sqlite3.Connection,service:DocumentService,parent=None):
        super().__init__(parent);self.connection=connection;self.service=service;l=QVBoxLayout(self);_title(l,'Documentos e Comprovantes');bar=QHBoxLayout();self.person=QComboBox();self.category=QComboBox();self.dtype=QLineEdit();self.start=QDateEdit(QDate(date.today().year,1,1));self.end=QDateEdit(QDate.currentDate());search=QPushButton('Pesquisar');search.clicked.connect(self.refresh);attach=QPushButton('Anexar');attach.clicked.connect(self.attach);openb=QPushButton('Abrir selecionado');openb.clicked.connect(self.open_selected)
        for w in (QLabel('Pessoa:'),self.person,QLabel('Categoria:'),self.category,QLabel('Tipo:'),self.dtype,self.start,self.end,search,attach,openb):bar.addWidget(w);l.addLayout(bar);self.table=QTableWidget();l.addWidget(self.table,1);self.refresh_refs();self.refresh()
    def refresh_refs(self):_combo(self.person,list(self.connection.execute('SELECT id,name FROM person WHERE active=1 ORDER BY name')),lambda r:r['name']);_combo(self.category,list(self.connection.execute('SELECT id,name FROM category WHERE active=1 ORDER BY name')),lambda r:r['name'])
    def attach(self):
        path,_=QFileDialog.getOpenFileName(self,'Selecionar documento')
        if not path:return
        entry,ok=QInputDialog.getInt(self,'Vincular lançamento','ID do lançamento (0 = nenhum):',0,0,999999999)
        if not ok:return
        try:self.service.attach(Path(path),self.dtype.text().strip() or 'DOCUMENTO',entry_id=entry or None,person_id=self.person.currentData());self.refresh()
        except Exception as e:QMessageBox.warning(self,'Documentos',str(e))
    def open_selected(self):
        row=self.table.currentRow()
        if row<0:return
        did=int(self.table.item(row,0).text());path=self.service.resolve_path(did)
        if path is None:QMessageBox.warning(self,'Documento','O arquivo não foi encontrado no disco.');return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
    def refresh(self):
        f=DocumentFilters(start=_d(self.start),end=_d(self.end),person_id=self.person.currentData(),category_id=self.category.currentData(),document_type=self.dtype.text().strip() or None);rows=self.service.search(f);_fill(self.table,['ID','Arquivo','Tipo','Status','Data'],[(r.id,r.original_name,r.document_type,'AUSENTE' if r.missing else 'OK',r.created_at) for r in rows])

class AdvancedReportsPage(QWidget):
    def __init__(self,connection:sqlite3.Connection,parent=None):
        super().__init__(parent);self.connection=connection;self.service=ReportQueryService(connection);self.current=None;l=QVBoxLayout(self);_title(l,'Relatórios');top=QHBoxLayout();self.kind=QComboBox();options=[('Despesas detalhadas','expenses'),('Despesas por pessoa','expenses_by_person'),('Despesas por categoria','expenses_by_category'),('Despesas por subcategoria','expenses_by_subcategory'),('Despesas por centro de custo','expenses_by_cost_center'),('Despesas por conta','expenses_by_bank'),('Despesas por cartão','expenses_by_card'),('Pagas x pendentes','expenses_by_status'),('Fixas x variáveis','fixed_vs_variable'),('Receitas detalhadas','income'),('Receitas por origem','income_by_source'),('Contas a pagar','payables'),('Contas a receber','receivables'),('Orçamento previsto x realizado','budget_vs_actual'),('Conciliação financeira','reconciliation'),('Faturas de cartão','card_invoices'),('Fluxo de caixa','cash_flow'),('Evolução mensal','monthly_evolution'),('Patrimônio','assets'),('Investimentos','investments'),('Patrimônio líquido','net_worth')];[(self.kind.addItem(a,b)) for a,b in options];self.start=QDateEdit(QDate(date.today().year,date.today().month,1));self.start.setCalendarPopup(True);self.end=QDateEdit(QDate.currentDate());self.end.setCalendarPopup(True);top.addWidget(self.kind);top.addWidget(self.start);top.addWidget(self.end);l.addLayout(top);filters=QHBoxLayout();self.person=QComboBox();self.category=QComboBox();self.cost=QComboBox();self.bank=QComboBox();self.card=QComboBox();self.status=QComboBox();[(self.status.addItem(a,b)) for a,b in [('Todos',None),('Pendente','PENDENTE'),('Pago','PAGO'),('Recebido','RECEBIDO'),('Atrasado','ATRASADO'),('Conciliado','CONCILIADO'),('Divergente','DIVERGENTE')]]
        for label,w in [('Pessoa',self.person),('Categoria',self.category),('Centro',self.cost),('Conta',self.bank),('Cartão',self.card),('Status',self.status)]:filters.addWidget(QLabel(label));filters.addWidget(w)
        l.addLayout(filters);actions=QHBoxLayout();generate=QPushButton('Gerar');generate.clicked.connect(self.generate);detail=QPushButton('Ver lançamentos');detail.clicked.connect(self.show_detail);xlsx=QPushButton('Exportar Excel');xlsx.clicked.connect(self.xlsx);pdf=QPushButton('Exportar PDF');pdf.clicked.connect(self.pdf);[actions.addWidget(x) for x in (generate,detail,xlsx,pdf)];l.addLayout(actions);self.total=QLabel('');l.addWidget(self.total);self.table=QTableWidget();l.addWidget(self.table,1);self.load_refs();self.generate()
    def load_refs(self):_combo(self.person,list(self.connection.execute('SELECT id,name FROM person WHERE active=1 ORDER BY name')),lambda r:r['name']);_combo(self.category,list(self.connection.execute('SELECT id,name FROM category WHERE active=1 ORDER BY name')),lambda r:r['name']);_combo(self.cost,list(self.connection.execute('SELECT id,name FROM cost_center WHERE active=1 ORDER BY name')),lambda r:r['name']);_combo(self.bank,list(self.connection.execute('SELECT id,institution,name FROM bank_account WHERE active=1 ORDER BY institution,name')),lambda r:f"{r['institution']} - {r['name']}");_combo(self.card,list(self.connection.execute('SELECT id,issuer,holder,name FROM credit_card WHERE active=1 ORDER BY issuer,holder')),lambda r:f"{r['issuer']} - {r['name'] or r['holder']}")
    def _filters(self):return ReportFilters(_d(self.start),_d(self.end),person_id=self.person.currentData(),category_id=self.category.currentData(),cost_center_id=self.cost.currentData(),bank_account_id=self.bank.currentData(),card_id=self.card.currentData(),status=self.status.currentData())
    def generate(self):
        try:
            name=self.kind.currentData();method=getattr(self.service,name)
            if name in {'assets','investments'}:self.current=method()
            elif name=='net_worth':self.current=method(_d(self.end))
            else:self.current=method(self._filters())
            _fill(self.table,list(self.current.columns),self.current.rows);self.total.setText('Total: '+('—' if self.current.total_cents is None else f'R$ {self.current.total_cents/100:,.2f}')+'   |   '+self.current.filters_text)
        except Exception as e:QMessageBox.warning(self,'Relatórios',str(e))
    def show_detail(self):
        if not self.current or not self.current.detail_entry_ids:QMessageBox.information(self,'Detalhamento','Este relatório não possui lançamentos para detalhar.');return
        marks=','.join('?'*len(self.current.detail_entry_ids));rows=self.connection.execute(f'SELECT id,competence_date,description,entry_type,status,amount_cents FROM financial_entry WHERE id IN ({marks}) ORDER BY competence_date,id',self.current.detail_entry_ids).fetchall();dlg=QDialog(self);dlg.setWindowTitle('Lançamentos do relatório');dlg.resize(900,500);lay=QVBoxLayout(dlg);table=QTableWidget();_fill(table,['ID','Data','Descrição','Tipo','Status','Valor'],[(r['id'],r['competence_date'],r['description'],r['entry_type'],r['status'],r['amount_cents']/100) for r in rows]);lay.addWidget(table);dlg.exec()
    def xlsx(self):
        if not self.current:return
        p,_=QFileDialog.getSaveFileName(self,'Exportar Excel','relatorio.xlsx','Excel (*.xlsx)')
        if p:export_xlsx(self.current,Path(p))
    def pdf(self):
        if not self.current:return
        p,_=QFileDialog.getSaveFileName(self,'Exportar PDF','relatorio.pdf','PDF (*.pdf)')
        if p:export_pdf(self.current,Path(p))
