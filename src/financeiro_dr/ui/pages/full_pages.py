from __future__ import annotations
from datetime import date
from pathlib import Path
import sqlite3
from PySide6.QtCore import QDate
from PySide6.QtWidgets import (QCheckBox,QComboBox,QDateEdit,QFileDialog,QFormLayout,QHBoxLayout,QHeaderView,QLabel,QLineEdit,QMessageBox,QPushButton,QSpinBox,QTableWidget,QTableWidgetItem,QVBoxLayout,QWidget)
from financeiro_dr.ui.widgets.money_edit import MoneyEdit
from financeiro_dr.people import PeopleService
from financeiro_dr.classification import ClassificationService
from financeiro_dr.budgets import BudgetService
from financeiro_dr.banking import BankService
from financeiro_dr.cards import CardService
from financeiro_dr.reconciliation import ImportService,ReconciliationService
from financeiro_dr.assets import AssetService
from financeiro_dr.investments import InvestmentService
from financeiro_dr.documents import DocumentService,DocumentFilters
from financeiro_dr.income_sources import IncomeSourceService
from financeiro_dr.reports import ReportFilters,ReportQueryService,export_pdf,export_xlsx
from financeiro_dr.backup import BackupService,RestoreService
from financeiro_dr.settings import SettingsService,AppSettings
from financeiro_dr.audit.query_service import AuditQueryService
from financeiro_dr.security.auth_service import AuthService

def _title(layout,text):
    x=QLabel(text);x.setStyleSheet('font-size:24px;font-weight:700;');layout.addWidget(x)
def _fill(table,headers,rows):
    table.clear();table.setColumnCount(len(headers));table.setHorizontalHeaderLabels(headers);table.setRowCount(len(rows))
    for i,row in enumerate(rows):
        for j,val in enumerate(row):table.setItem(i,j,QTableWidgetItem('' if val is None else str(val)))
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents);table.horizontalHeader().setStretchLastSection(True)
def _d(widget):
    q=widget.date();return date(q.year(),q.month(),q.day())
def _combo(combo,rows,label,optional=True):
    combo.clear()
    if optional:combo.addItem('Todos / Não informado',None)
    for r in rows:combo.addItem(label(r),r['id'])

class PeoplePage(QWidget):
    def __init__(self,service:PeopleService,parent=None):
        super().__init__(parent);self.service=service;l=QVBoxLayout(self);_title(l,'Pessoas / Beneficiários');f=QFormLayout();self.name=QLineEdit();self.rel=QLineEdit();self.nick=QLineEdit();f.addRow('Nome:',self.name);f.addRow('Parentesco:',self.rel);f.addRow('Identificação:',self.nick);l.addLayout(f);b=QPushButton('Adicionar pessoa');b.clicked.connect(self.add);l.addWidget(b);self.table=QTableWidget();l.addWidget(self.table,1);self.refresh()
    def add(self):
        try:self.service.create(self.name.text(),self.rel.text() or None,self.nick.text() or None,None);self.name.clear();self.refresh()
        except Exception as e:QMessageBox.warning(self,'Pessoas',str(e))
    def refresh(self):_fill(self.table,['ID','Nome','Parentesco','Identificação','Ativo'],[(p.id,p.name,p.relationship,p.nickname,'Sim' if p.active else 'Não') for p in self.service.list_all()])

class ClassificationPage(QWidget):
    def __init__(self,connection,service:ClassificationService,parent=None):
        super().__init__(parent);self.connection=connection;self.service=service;self.sources=IncomeSourceService(connection);l=QVBoxLayout(self);_title(l,'Categorias, Centros de Custo e Origens');f=QFormLayout();self.cat=QLineEdit();self.cat_combo=QComboBox();self.sub=QLineEdit();self.cost=QLineEdit();self.source=QLineEdit();f.addRow('Nova categoria:',self.cat);bc=QPushButton('Criar categoria');bc.clicked.connect(self.add_cat);f.addRow('',bc);f.addRow('Categoria da subcategoria:',self.cat_combo);f.addRow('Nova subcategoria:',self.sub);bs=QPushButton('Criar subcategoria');bs.clicked.connect(self.add_sub);f.addRow('',bs);f.addRow('Novo centro de custo:',self.cost);bco=QPushButton('Criar centro de custo');bco.clicked.connect(self.add_cost);f.addRow('',bco);f.addRow('Nova origem de receita:',self.source);bo=QPushButton('Criar origem');bo.clicked.connect(self.add_source);f.addRow('',bo);l.addLayout(f);self.table=QTableWidget();l.addWidget(self.table,1);self.refresh()
    def add_cat(self):
        try:self.service.create_category(self.cat.text());self.cat.clear();self.refresh()
        except Exception as e:QMessageBox.warning(self,'Classificação',str(e))
    def add_sub(self):
        try:self.service.create_subcategory(self.cat_combo.currentData(),self.sub.text());self.sub.clear();self.refresh()
        except Exception as e:QMessageBox.warning(self,'Classificação',str(e))
    def add_cost(self):
        try:self.service.create_cost_center(self.cost.text());self.cost.clear();self.refresh()
        except Exception as e:QMessageBox.warning(self,'Classificação',str(e))
    def add_source(self):
        try:self.sources.create(self.source.text());self.source.clear();self.refresh()
        except Exception as e:QMessageBox.warning(self,'Classificação',str(e))
    def refresh(self):
        cats=self.service.list_categories(False);_combo(self.cat_combo,[r for r in cats if r['active']],lambda r:r['name'],False);rows=[]
        for r in cats:rows.append(('Categoria','',r['name'],'Sim' if r['active'] else 'Não'))
        for r in self.connection.execute('SELECT s.*,c.name category_name FROM subcategory s JOIN category c ON c.id=s.category_id ORDER BY c.name,s.name'):rows.append(('Subcategoria',r['category_name'],r['name'],'Sim' if r['active'] else 'Não'))
        for r in self.service.list_cost_centers(False):rows.append(('Centro de Custo','',r['name'],'Sim' if r['active'] else 'Não'))
        for r in self.sources.list_all():rows.append(('Origem de Receita','',r.name,'Sim' if r.active else 'Não'))
        _fill(self.table,['Tipo','Grupo','Nome','Ativo'],rows)

class BudgetsPage(QWidget):
    def __init__(self,connection,parent=None):
        super().__init__(parent);self.connection=connection;self.service=BudgetService(connection);l=QVBoxLayout(self);_title(l,'Orçamentos');f=QFormLayout();self.month=QLineEdit(date.today().strftime('%Y-%m'));self.amount=MoneyEdit();self.person=QComboBox();self.category=QComboBox();self.cost=QComboBox();f.addRow('Mês (AAAA-MM):',self.month);f.addRow('Valor previsto:',self.amount);f.addRow('Pessoa:',self.person);f.addRow('Categoria:',self.category);f.addRow('Centro de Custo:',self.cost);l.addLayout(f);b=QPushButton('Criar orçamento');b.clicked.connect(self.add);l.addWidget(b);self.table=QTableWidget();l.addWidget(self.table,1);self.refresh()
    def add(self):
        try:self.service.create(self.month.text(),self.amount.cents(),self.person.currentData(),self.category.currentData(),self.cost.currentData());self.refresh()
        except Exception as e:QMessageBox.warning(self,'Orçamento',str(e))
    def refresh(self):
        _combo(self.person,list(self.connection.execute('SELECT id,name FROM person WHERE active=1 ORDER BY name')),lambda r:r['name']);_combo(self.category,list(self.connection.execute('SELECT id,name FROM category WHERE active=1 ORDER BY name')),lambda r:r['name']);_combo(self.cost,list(self.connection.execute('SELECT id,name FROM cost_center WHERE active=1 ORDER BY name')),lambda r:r['name'])
        try:y,m=map(int,self.month.text().split('-'))
        except Exception:y,m=date.today().year,date.today().month
        snaps=self.service.month_summary(y,m);rows=[]
        for s in snaps:
            level='ACIMA' if s.percent_used>100 else 'LIMITE' if s.percent_used>=100 else 'ATENÇÃO' if s.percent_used>=80 else 'OK';rows.append((s.id,f'{s.month:02d}/{s.year}',s.amount_cents/100,s.spent_cents/100,s.remaining_cents/100,f'{s.percent_used:.1f}%',level))
        _fill(self.table,['ID','Mês','Previsto','Realizado','Saldo','Uso','Alerta'],rows)

class BanksPage(QWidget):
    def __init__(self,connection,parent=None):
        super().__init__(parent);self.connection=connection;self.service=BankService(connection);l=QVBoxLayout(self);_title(l,'Bancos e Contas');f=QFormLayout();self.inst=QLineEdit();self.name=QLineEdit();self.opening=MoneyEdit();f.addRow('Instituição:',self.inst);f.addRow('Conta:',self.name);f.addRow('Saldo inicial:',self.opening);b=QPushButton('Cadastrar conta');b.clicked.connect(self.add);f.addRow('',b);self.src=QComboBox();self.dst=QComboBox();self.transfer=MoneyEdit();self.tdesc=QLineEdit('Transferência');f.addRow('Transferir de:',self.src);f.addRow('Para:',self.dst);f.addRow('Valor:',self.transfer);f.addRow('Descrição:',self.tdesc);bt=QPushButton('Fazer transferência');bt.clicked.connect(self.do_transfer);f.addRow('',bt);l.addLayout(f);self.table=QTableWidget();l.addWidget(self.table,1);self.refresh()
    def add(self):
        try:self.service.create_account(self.inst.text(),self.name.text(),self.opening.cents());self.refresh()
        except Exception as e:QMessageBox.warning(self,'Bancos',str(e))
    def do_transfer(self):
        try:self.service.transfer(self.src.currentData(),self.dst.currentData(),self.transfer.cents(),date.today(),self.tdesc.text() or 'Transferência');self.refresh()
        except Exception as e:QMessageBox.warning(self,'Transferência',str(e))
    def refresh(self):
        rows=self.service.list_accounts(False);active=[r for r in rows if r['active']];_combo(self.src,active,lambda r:f"{r['institution']} - {r['name']}",False);_combo(self.dst,active,lambda r:f"{r['institution']} - {r['name']}",False);_fill(self.table,['ID','Instituição','Conta','Saldo Atual','Ativa'],[(r['id'],r['institution'],r['name'],self.service.balance(r['id'])/100,'Sim' if r['active'] else 'Não') for r in rows])

class CardsPage(QWidget):
    def __init__(self,connection,parent=None):
        super().__init__(parent);self.connection=connection;self.service=CardService(connection);l=QVBoxLayout(self);_title(l,'Cartões de Crédito');f=QFormLayout();self.issuer=QLineEdit();self.holder=QLineEdit();self.cname=QLineEdit();self.limit=MoneyEdit();self.close=QSpinBox();self.close.setRange(1,31);self.close.setValue(10);self.due=QSpinBox();self.due.setRange(1,31);self.due.setValue(20);f.addRow('Banco/Emissor:',self.issuer);f.addRow('Titular:',self.holder);f.addRow('Nome do cartão:',self.cname);f.addRow('Limite:',self.limit);f.addRow('Fechamento:',self.close);f.addRow('Vencimento:',self.due);bc=QPushButton('Cadastrar cartão');bc.clicked.connect(self.add_card);f.addRow('',bc);self.card=QComboBox();self.pdesc=QLineEdit();self.pamount=MoneyEdit();self.pinstall=QSpinBox();self.pinstall.setRange(1,60);self.pdate=QDateEdit(QDate.currentDate());self.pdate.setCalendarPopup(True);f.addRow('Cartão da compra:',self.card);f.addRow('Descrição da compra:',self.pdesc);f.addRow('Valor total:',self.pamount);f.addRow('Parcelas:',self.pinstall);f.addRow('Data da compra:',self.pdate);bp=QPushButton('Adicionar compra');bp.clicked.connect(self.add_purchase);f.addRow('',bp);l.addLayout(f);self.table=QTableWidget();l.addWidget(self.table,1);self.refresh()
    def add_card(self):
        try:self.service.create_card(self.issuer.text(),self.holder.text(),self.limit.cents(),self.close.value(),self.due.value(),self.cname.text() or None);self.refresh()
        except Exception as e:QMessageBox.warning(self,'Cartões',str(e))
    def add_purchase(self):
        try:self.service.add_purchase(self.card.currentData(),_d(self.pdate),self.pdesc.text(),self.pamount.cents(),self.pinstall.value());self.refresh()
        except Exception as e:QMessageBox.warning(self,'Compra',str(e))
    def refresh(self):
        rows=list(self.connection.execute('SELECT * FROM credit_card ORDER BY active DESC,issuer,holder'));_combo(self.card,[r for r in rows if r['active']],lambda r:f"{r['issuer']} - {r['name'] or r['holder']}",False);out=[]
        for r in rows:
            used=self.service.used_limit_cents(r['id']);out.append((r['id'],r['issuer'],r['name'] or r['holder'],r['limit_cents']/100,used/100,(r['limit_cents']-used)/100,r['closing_day'],r['due_day']))
        _fill(self.table,['ID','Emissor','Cartão','Limite','Usado','Disponível','Fecha','Vence'],out)

class ReconciliationPage(QWidget):
    def __init__(self,connection,parent=None):
        super().__init__(parent);self.connection=connection;self.importer=ImportService(connection);self.service=ReconciliationService(connection);self.banks=BankService(connection);l=QVBoxLayout(self);_title(l,'Conciliação Financeira');top=QHBoxLayout();self.account=QComboBox();top.addWidget(QLabel('Conta:'));top.addWidget(self.account);bi=QPushButton('Importar OFX / CSV / Excel');bi.clicked.connect(self.import_file);top.addWidget(bi);bc=QPushButton('Confirmar melhor candidato');bc.clicked.connect(self.confirm);top.addWidget(bc);bd=QPushButton('Marcar divergente');bd.clicked.connect(self.divergent);top.addWidget(bd);l.addLayout(top);self.table=QTableWidget();l.addWidget(self.table,1);self.refresh()
    def import_file(self):
        path,_=QFileDialog.getOpenFileName(self,'Importar extrato','','Extratos (*.ofx *.qfx *.csv *.xlsx *.xlsm)')
        if not path:return
        try:r=self.importer.import_file(self.account.currentData(),Path(path));QMessageBox.information(self,'Importação',f'{r.created} novos; {r.duplicates} duplicados.');self.refresh()
        except Exception as e:QMessageBox.warning(self,'Importação',str(e))
    def _selected_id(self):
        row=self.table.currentRow();return int(self.table.item(row,0).text()) if row>=0 else None
    def confirm(self):
        sid=self._selected_id()
        if sid is None:return
        try:
            result=self.service.suggest(sid)
            if not result.candidates:raise ValueError('Nenhum lançamento candidato encontrado.')
            self.service.confirm(sid,result.candidates[0].entry_id);self.refresh()
        except Exception as e:QMessageBox.warning(self,'Conciliação',str(e))
    def divergent(self):
        sid=self._selected_id()
        if sid is None:return
        try:self.service.mark_divergent(sid,'Marcado manualmente');self.refresh()
        except Exception as e:QMessageBox.warning(self,'Conciliação',str(e))
    def refresh(self):
        accounts=self.banks.list_accounts();_combo(self.account,accounts,lambda r:f"{r['institution']} - {r['name']}",False);rows=[]
        for r in self.connection.execute("SELECT sr.*,COALESCE((SELECT status FROM reconciliation_link rl WHERE rl.statement_row_id=sr.id ORDER BY rl.id DESC LIMIT 1),'PENDENTE') status FROM statement_row sr ORDER BY sr.posted_date DESC,sr.id DESC"):
            try:sg=self.service.suggest(r['id']);best=sg.candidates[0] if sg.candidates else None;candidate=f"#{best.entry_id} / {best.score}" if best else ''
            except Exception:candidate=''
            rows.append((r['id'],r['posted_date'],r['description'],r['amount_cents']/100,candidate,r['status']))
        _fill(self.table,['ID','Data','Extrato','Valor','Melhor candidato / score','Status'],rows)

class AssetsPage(QWidget):
    def __init__(self,connection,parent=None):
        super().__init__(parent);self.connection=connection;self.service=AssetService(connection);l=QVBoxLayout(self);_title(l,'Patrimônio');f=QFormLayout();self.kind=QComboBox();[(self.kind.addItem(a,b)) for a,b in [('Imóvel','IMOVEL'),('Veículo','VEICULO'),('Terreno','TERRENO'),('Outro','OUTRO')]];self.desc=QLineEdit();self.acq=MoneyEdit();self.est=MoneyEdit();f.addRow('Tipo:',self.kind);f.addRow('Descrição:',self.desc);f.addRow('Valor de aquisição:',self.acq);f.addRow('Valor estimado atual:',self.est);b=QPushButton('Cadastrar patrimônio');b.clicked.connect(self.add);f.addRow('',b);l.addLayout(f);self.table=QTableWidget();l.addWidget(self.table,1);self.refresh()
    def add(self):
        try:self.service.create(self.kind.currentData(),self.desc.text(),None,self.acq.cents(),self.est.cents(),None);self.refresh()
        except Exception as e:QMessageBox.warning(self,'Patrimônio',str(e))
    def refresh(self):_fill(self.table,['ID','Tipo','Descrição','Aquisição','Valor Atual'],[(r['id'],r['asset_type'],r['description'],r['acquisition_value_cents']/100,r['estimated_value_cents']/100) for r in self.service.list_active()])

class InvestmentsPage(QWidget):
    def __init__(self,connection,parent=None):
        super().__init__(parent);self.connection=connection;self.service=InvestmentService(connection);l=QVBoxLayout(self);_title(l,'Investimentos');f=QFormLayout();self.inst=QLineEdit();self.name=QLineEdit();self.kind=QLineEdit();f.addRow('Instituição:',self.inst);f.addRow('Aplicação:',self.name);f.addRow('Tipo:',self.kind);ba=QPushButton('Cadastrar investimento');ba.clicked.connect(self.add_account);f.addRow('',ba);self.account=QComboBox();self.movetype=QComboBox();[(self.movetype.addItem(a,a)) for a in ['APORTE','RESGATE','RENDIMENTO','AJUSTE']];self.amount=MoneyEdit();self.mdate=QDateEdit(QDate.currentDate());f.addRow('Investimento:',self.account);f.addRow('Movimento:',self.movetype);f.addRow('Valor:',self.amount);f.addRow('Data:',self.mdate);bm=QPushButton('Registrar movimento');bm.clicked.connect(self.add_move);f.addRow('',bm);l.addLayout(f);self.table=QTableWidget();l.addWidget(self.table,1);self.refresh()
    def add_account(self):
        try:self.service.create(self.inst.text(),self.name.text(),self.kind.text());self.refresh()
        except Exception as e:QMessageBox.warning(self,'Investimentos',str(e))
    def add_move(self):
        try:self.service.add_movement(self.account.currentData(),self.movetype.currentData(),self.amount.cents(),_d(self.mdate));self.refresh()
        except Exception as e:QMessageBox.warning(self,'Investimentos',str(e))
    def refresh(self):
        rows=self.service.list_accounts();_combo(self.account,rows,lambda r:f"{r['institution']} - {r['account_name']}",False);_fill(self.table,['ID','Instituição','Aplicação','Tipo','Saldo'],[(r['id'],r['institution'],r['account_name'],r['investment_type'],self.service.balance(r['id'])/100) for r in rows])

class DocumentsPage(QWidget):
    def __init__(self,connection,service:DocumentService,parent=None):
        super().__init__(parent);self.connection=connection;self.service=service;l=QVBoxLayout(self);_title(l,'Documentos e Comprovantes');top=QHBoxLayout();self.dtype=QLineEdit('COMPROVANTE');self.entry=QSpinBox();self.entry.setRange(0,999999999);b=QPushButton('Anexar arquivo');b.clicked.connect(self.attach);top.addWidget(QLabel('Tipo:'));top.addWidget(self.dtype);top.addWidget(QLabel('Lançamento ID (0 = nenhum):'));top.addWidget(self.entry);top.addWidget(b);l.addLayout(top);self.table=QTableWidget();l.addWidget(self.table,1);self.refresh()
    def attach(self):
        path,_=QFileDialog.getOpenFileName(self,'Selecionar documento')
        if not path:return
        try:self.service.attach(Path(path),self.dtype.text() or 'DOCUMENTO',entry_id=self.entry.value() or None);self.refresh()
        except Exception as e:QMessageBox.warning(self,'Documentos',str(e))
    def refresh(self):_fill(self.table,['ID','Arquivo','Tipo','Status','Data'],[(r.id,r.original_name,r.document_type,'Arquivo ausente' if r.missing else 'OK',r.created_at) for r in self.service.search(DocumentFilters())])

class ReportsPage(QWidget):
    def __init__(self,connection,parent=None):
        super().__init__(parent);self.connection=connection;self.service=ReportQueryService(connection);self.current=None;l=QVBoxLayout(self);_title(l,'Relatórios');top=QHBoxLayout();self.kind=QComboBox();[(self.kind.addItem(a,b)) for a,b in [('Despesas','expenses'),('Receitas','income'),('Fluxo de Caixa','cash_flow'),('Fixas x Variáveis','fixed_vs_variable'),('Receitas por Origem','income_by_source'),('Contas a Pagar','payables'),('Contas a Receber','receivables'),('Patrimônio','assets'),('Investimentos','investments')]];self.start=QDateEdit(QDate(date.today().year,date.today().month,1));self.start.setCalendarPopup(True);self.end=QDateEdit(QDate.currentDate());self.end.setCalendarPopup(True);bg=QPushButton('Gerar');bg.clicked.connect(self.generate);bx=QPushButton('Exportar Excel');bx.clicked.connect(self.xlsx);bp=QPushButton('Exportar PDF');bp.clicked.connect(self.pdf);top.addWidget(self.kind);top.addWidget(self.start);top.addWidget(self.end);top.addWidget(bg);top.addWidget(bx);top.addWidget(bp);l.addLayout(top);self.total=QLabel('');l.addWidget(self.total);self.table=QTableWidget();l.addWidget(self.table,1);self.generate()
    def generate(self):
        try:
            name=self.kind.currentData();filters=ReportFilters(_d(self.start),_d(self.end));self.current=getattr(self.service,name)() if name in {'assets','investments'} else getattr(self.service,name)(filters);_fill(self.table,list(self.current.columns),self.current.rows);self.total.setText('Total: '+('—' if self.current.total_cents is None else f'R$ {self.current.total_cents/100:,.2f}'))
        except Exception as e:QMessageBox.warning(self,'Relatórios',str(e))
    def xlsx(self):
        if not self.current:return
        path,_=QFileDialog.getSaveFileName(self,'Exportar Excel','relatorio.xlsx','Excel (*.xlsx)')
        if path:export_xlsx(self.current,Path(path))
    def pdf(self):
        if not self.current:return
        path,_=QFileDialog.getSaveFileName(self,'Exportar PDF','relatorio.pdf','PDF (*.pdf)')
        if path:export_pdf(self.current,Path(path))

class AuditHistoryPage(QWidget):
    def __init__(self,connection,parent=None):
        super().__init__(parent);self.service=AuditQueryService(connection);l=QVBoxLayout(self);_title(l,'Histórico de Alterações');self.table=QTableWidget();l.addWidget(self.table,1);self.refresh()
    def refresh(self):_fill(self.table,['Data/Hora','Ação','Módulo','Registro','Campo','Antes','Depois'],[(e.occurred_at,e.action,e.entity,e.entity_id,e.field_name,e.old_value,e.new_value) for e in self.service.search()[:1000]])

class BackupPage(QWidget):
    def __init__(self,backup:BackupService,restore:RestoreService,settings:SettingsService,parent=None):
        super().__init__(parent);self.backup=backup;self.restore_service=restore;self.settings=settings;l=QVBoxLayout(self);_title(l,'Backup e Restauração');f=QFormLayout();self.dir=QLineEdit(self.settings.load().backup_dir);choose=QPushButton('Escolher pasta');choose.clicked.connect(self.choose);f.addRow('Pasta sincronizada pelo Google Drive:',self.dir);f.addRow('',choose);l.addLayout(f);b=QPushButton('Fazer backup agora');b.clicked.connect(self.make);r=QPushButton('Restaurar backup');r.clicked.connect(self.restore);l.addWidget(b);l.addWidget(r);self.info=QLabel('');self.info.setWordWrap(True);l.addWidget(self.info);l.addStretch(1);self.refresh()
    def choose(self):
        p=QFileDialog.getExistingDirectory(self,'Pasta de backup')
        if p:self.dir.setText(p)
    def make(self):
        try:
            if not self.dir.text():raise ValueError('Escolha a pasta de backup.')
            s=self.settings.load();self.settings.save(AppSettings(self.dir.text(),s.auto_backup_enabled,s.card_alert_percent,s.budget_warning_percent,s.budget_limit_percent));res=self.backup.create(Path(self.dir.text()),'MANUAL');self.info.setText(f'Backup concluído: {res.path}');self.refresh()
        except Exception as e:QMessageBox.warning(self,'Backup',str(e))
    def restore(self):
        p,_=QFileDialog.getOpenFileName(self,'Restaurar backup','','Backup (*.zip)')
        if not p:return
        try:
            val=self.restore_service.validate(Path(p));ans=QMessageBox.question(self,'Confirmar restauração',f'Backup válido de {val.created_at}. Restaurar agora?')
            if ans==QMessageBox.Yes:self.restore_service.restore(Path(p));self.info.setText('Backup restaurado. Reinicie o aplicativo após concluir o trabalho atual.')
        except Exception as e:QMessageBox.warning(self,'Restauração',str(e))
    def refresh(self):
        row=self.backup.last_success()
        if row:self.info.setText(f"Último backup: {row['created_at']} — {row['file_name']}")

class SettingsPage(QWidget):
    def __init__(self,settings:SettingsService,auth:AuthService,parent=None):
        super().__init__(parent);self.settings=settings;self.auth=auth;l=QVBoxLayout(self);_title(l,'Configurações');f=QFormLayout();s=settings.load();self.backup_dir=QLineEdit(s.backup_dir);self.auto=QCheckBox();self.auto.setChecked(s.auto_backup_enabled);self.card=QSpinBox();self.card.setRange(1,100);self.card.setValue(s.card_alert_percent);self.warn=QSpinBox();self.warn.setRange(1,100);self.warn.setValue(s.budget_warning_percent);f.addRow('Pasta de backup:',self.backup_dir);f.addRow('Backup automático:',self.auto);f.addRow('Alerta de cartão (%):',self.card);f.addRow('Alerta orçamento (%):',self.warn);save=QPushButton('Salvar configurações');save.clicked.connect(self.save);f.addRow('',save);self.current=QLineEdit();self.current.setEchoMode(QLineEdit.Password);self.new=QLineEdit();self.new.setEchoMode(QLineEdit.Password);f.addRow('Senha atual:',self.current);f.addRow('Nova senha:',self.new);change=QPushButton('Trocar senha');change.clicked.connect(self.change);f.addRow('',change);l.addLayout(f);l.addStretch(1)
    def save(self):
        old=self.settings.load();self.settings.save(AppSettings(self.backup_dir.text(),self.auto.isChecked(),self.card.value(),self.warn.value(),old.budget_limit_percent));QMessageBox.information(self,'Configurações','Configurações salvas.')
    def change(self):
        try:self.auth.change_password(self.current.text(),self.new.text());QMessageBox.information(self,'Senha','Senha alterada.');self.current.clear();self.new.clear()
        except Exception as e:QMessageBox.warning(self,'Senha',str(e))
