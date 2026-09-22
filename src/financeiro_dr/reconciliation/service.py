from __future__ import annotations
import sqlite3
from financeiro_dr.core.financeiro.repository import FinancialRepository
from .matcher import rank_matches

class ReconciliationService:
    def __init__(self,connection:sqlite3.Connection,repository:FinancialRepository|None=None): self.connection=connection; self.repository=repository or FinancialRepository(connection)
    def suggest(self,statement_row_id:int):
        row=self.connection.execute("SELECT * FROM statement_row WHERE id=?",(statement_row_id,)).fetchone()
        if row is None: raise ValueError("Movimento do extrato não encontrado.")
        entries=self.repository.candidates_by_amount(abs(int(row['amount_cents'])))
        return rank_matches(row,entries)
    def confirm(self,statement_row_id:int,entry_id:int)->None:
        result=self.suggest(statement_row_id); score=next((x.score for x in result.candidates if x.entry_id==entry_id),0)
        self.connection.execute("INSERT INTO reconciliation_link(statement_row_id,entry_id,status,score,confirmed_at) VALUES (?,?,'CONCILIADO',?,strftime('%Y-%m-%dT%H:%M:%fZ','now'))",(statement_row_id,entry_id,score)); self.connection.commit()
    def mark_divergent(self,statement_row_id:int,note:str)->None:
        self.connection.execute("INSERT INTO reconciliation_link(statement_row_id,status,note,confirmed_at) VALUES (?,'DIVERGENTE',?,strftime('%Y-%m-%dT%H:%M:%fZ','now'))",(statement_row_id,note)); self.connection.commit()
    def pending_count(self)->int:
        return int(self.connection.execute("SELECT COUNT(*) FROM statement_row sr WHERE sr.ignored=0 AND NOT EXISTS(SELECT 1 FROM reconciliation_link rl WHERE rl.statement_row_id=sr.id AND rl.status IN ('CONCILIADO','DIVERGENTE'))").fetchone()[0])
