from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.core.financeiro.reports import monthly_summary, export_excel, export_pdf


def test_monthly_financial_reports(tmp_path):
    con=Database(tmp_path/"financeiro.db").connect()
    MigrationRunner().apply_all(con)
    try:
        con.execute("INSERT INTO financial_entry(competence_date,description,amount_cents,entry_type,status) VALUES ('2026-10-09','Receita',10000,'RECEITA','RECEBIDO')")
        con.execute("INSERT INTO financial_entry(competence_date,description,amount_cents,entry_type,status) VALUES ('2026-10-09','Despesa',2550,'DESPESA','PAGO')")
        con.execute("INSERT INTO financial_entry(competence_date,description,amount_cents,entry_type,status) VALUES ('2026-10-09','Cancelada',500,'DESPESA','CANCELADO')")
        s=monthly_summary(con,2026,10)
        assert (s["income_cents"],s["expense_cents"],s["result_cents"]) == (10000,2550,7450)
        xlsx=export_excel(con,tmp_path/"report.xlsx",2026,10)
        pdf=export_pdf(con,tmp_path/"report.pdf",2026,10)
        assert xlsx.exists() and xlsx.stat().st_size>1000
        assert pdf.read_bytes()[:4]==b"%PDF"
    finally: con.close()
