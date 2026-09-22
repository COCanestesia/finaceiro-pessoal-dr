from datetime import date
import pytest
pytest.importorskip("PySide6")
from PySide6.QtCore import QDate,Qt
from financeiro_dr.audit.audit_service import AuditService
from financeiro_dr.core.financeiro.repository import FinancialRepository
from financeiro_dr.core.financeiro.scheduling import SchedulingService
from financeiro_dr.core.financeiro.service import FinancialService
from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.ui.pages.entries_page import EntriesPage

@pytest.fixture
def page_services(tmp_path):
    con=Database(tmp_path/"entries-ui.db").connect(); MigrationRunner().apply_all(con); repo=FinancialRepository(con); finance=FinancialService(con,repo,AuditService(con)); scheduling=SchedulingService(con,finance,repo)
    try: yield con,repo,finance,scheduling
    finally: con.close()

def fill_basic_entry(page):
    page.description_input.setText("Condomínio"); page.money_input.setText("1.234,56"); page.type_combo.setCurrentIndex(page.type_combo.findData("DESPESA")); page.status_combo.setCurrentIndex(page.status_combo.findData("PENDENTE")); page.competence_date.setDate(QDate(2026,9,22)); page.due_date.setDate(QDate(2026,9,22)); page.payment_method_input.setText("PIX")

def test_entry_form_saves_financial_entry(qtbot,page_services):
    con,repo,finance,scheduling=page_services; page=EntriesPage(finance,scheduling,repo); qtbot.addWidget(page); fill_basic_entry(page); qtbot.mouseClick(page.save_button,Qt.LeftButton); row=con.execute("select description, amount_cents, entry_type, status from financial_entry").fetchone(); assert tuple(row)==("Condomínio",123456,"DESPESA","PENDENTE"); assert "salvo" in page.feedback_label.text().lower()

def test_installment_form_creates_all_installments(qtbot,page_services):
    con,repo,finance,scheduling=page_services; page=EntriesPage(finance,scheduling,repo); qtbot.addWidget(page); fill_basic_entry(page); page.installments_spin.setValue(3); qtbot.mouseClick(page.save_button,Qt.LeftButton); rows=con.execute("select installment_number, installment_total, installment_group_id from financial_entry order by id").fetchall(); assert [tuple(row[:2]) for row in rows]==[(1,3),(2,3),(3,3)]; assert len({row[2] for row in rows})==1; assert rows[0][2] is not None

def test_future_classification_fields_are_disabled(qtbot,page_services):
    _,repo,finance,scheduling=page_services; page=EntriesPage(finance,scheduling,repo); qtbot.addWidget(page); assert page.person_combo.isEnabled() is False; assert page.category_combo.isEnabled() is False; assert page.bank_combo.isEnabled() is False; assert page.card_combo.isEnabled() is False
