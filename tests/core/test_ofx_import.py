from financeiro_dr.database.connection import Database
from financeiro_dr.database.migrations import MigrationRunner
from financeiro_dr.core.financeiro.ofx_import import import_ofx


def test_ofx_import_duplicate_fitid(tmp_path):
    con = Database(tmp_path / "data.db").connect()
    MigrationRunner().apply_all(con)
    account = con.execute("INSERT INTO bank_account(name) VALUES('Principal')").lastrowid
    text = """OFXHEADER:100
DATA:OFXSGML
<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><BANKTRANLIST>
<STMTTRN><TRNTYPE>DEBIT<DTPOSTED>20261009000000<TRNAMT>-12.34<FITID>abc123<NAME>Compra</STMTTRN>
<STMTTRN><TRNTYPE>DEBIT<DTPOSTED>20261009000000<TRNAMT>-12.34<FITID>abc123<NAME>Compra</STMTTRN>
</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>"""
    file = tmp_path / "bank.ofx"
    file.write_text(text, encoding="utf-8")
    try:
        assert import_ofx(con, account, file) == {"imported": 1, "duplicates": 1}
        assert import_ofx(con, account, file) == {"imported": 0, "duplicates": 2}
        assert con.execute("SELECT amount_cents FROM bank_statement_line").fetchone()[0] == -1234
        assert con.execute("SELECT count(*) FROM financial_entry").fetchone()[0] == 0
    finally:
        con.close()
